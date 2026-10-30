"""Session-local conversation state. Financial decisions always use the existing ML model."""
import re, math
import loan_core,groq_rag,guardrails
from customer_guidance import VERSION, REVIEW_MESSAGE

FIELDS=[('income','What is your annual gross income in INR?'),
 ('monthly_debt','How much do you already pay toward debt each month, in INR?'),
 ('loan_amount','How much would you like to borrow, in INR?'),
 ('term_months','Over how many months will you repay the loan?'),
 ('credit_score','What credit score is shown on your latest credit report?'),
 ('late_payments','How many late payments have you had in the last 12 months?'),
 ('employment_years','How many years of employment experience do you have?'),
 ('employment_type','Are you salaried or self-employed?')]
WELCOME='Hi! I’m Cedar’s loan assistant. Ask about our fictional lending policy or choose Check my eligibility. I can help only with loans and policy guidance. Every recommendation needs human review. Use synthetic examples only.'

def new_state():return {'version':VERSION,'messages':[{'role':'assistant','text':WELCOME,'kind':'welcome'}],'draft':None,'step':0,'previous_question':'','last_assessment':None,'busy':False}
def add(state,text,role='assistant',**extras):
    state['messages'].append({'role':role,'text':text,**extras});state['messages']=state['messages'][-40:]
def number(text,key):
    clean=text.lower().replace(',','').replace('₹','').strip()
    clean=re.sub(r'^(inr|rs\.?)[ ]*','',clean)
    match=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(k|lakh|lakhs|lac|lacs|crore|crores|months?|years?)?',clean)
    if not match:raise ValueError('Please enter a number, for example 50000 or 50k.')
    value=float(match[1]);unit=match[2]
    if unit in ('k','lakh','lakhs','lac','lacs','crore','crores'):
        if key not in ('income','monthly_debt','loan_amount'):raise ValueError('Please enter this value without a money unit.')
        value*=1000 if unit=='k' else 10000000 if unit in ('crore','crores') else 100000
    if unit and unit.startswith('month') and key!='term_months':raise ValueError('Please enter the requested value without months.')
    if unit and unit.startswith('year') and key!='employment_years':raise ValueError('Please enter the requested value without years.')
    lo,hi=loan_core.LIMITS[key]
    if not math.isfinite(value) or not lo<=value<=hi:raise ValueError('Please check this value against your records. If it cannot be accepted, contact a loan officer for help.')
    if key!='employment_years' and not value.is_integer():raise ValueError('Please enter a whole number.')
    return value if key=='employment_years' else int(value)

def summary(state):
    x=state['draft'];lines=['Please check these synthetic details before I assess them:']
    for key,_ in FIELDS:
        value=x[key];label=key.replace('_',' ').title()
        lines.append(f'{label}: {value:,}' if isinstance(value,(int,float)) else f'{label}: {value.replace("_"," ")}')
    lines.append('Choose Submit application to send these self-reported details for review. They must be verified before any decision. Choose Start over to correct an error; use information that matches your records.')
    add(state,'\n'.join(lines),kind='confirm')

def handle(state,text,app,owner,key):
    text=text.strip()
    if not text or len(text)>1500:raise ValueError('Please send a message of 1–1,500 characters.')
    if re.search(r'\b(gsk_|sk-or-|sk-proj-)',text):raise ValueError('Do not share API keys or other secrets in this chat.')
    add(state,text,'user');command=text.lower()
    if command in ('start over','/reset','cancel','/cancel'):
        state['draft']=None;state['step']=0;state['last_assessment']=None;state['previous_question']=''
        add(state,'Application draft cleared. Ask a policy question or choose Check my eligibility. Previously submitted cases remain in the local review queue.',kind='guide');return
    if command in ('check my eligibility','/apply','apply','i want a loan'):
        state['draft']={};state['step']=0;add(state,FIELDS[0][1],kind='question');return
    if command in ('demo approval','demo rejection','demo edge'):
        add(state,'Sample approval and rejection profiles are not available in customer chat. Choose Check my eligibility and provide accurate sample information.',kind='guide');return
    if command in ('submit application','confirm assessment','/submit'):
        if state['draft'] is None or state['step']!=len(FIELDS):
            add(state,'Please complete the financial details first. Choose Check my eligibility.',kind='guide');return
        assessment=loan_core.assess(app.model,state['draft'],app.policy)
        # Internal scores stay in storage. Customer feedback must not become an approval oracle.
        generation={'status':'not_requested','draft':None,'message':'Customer submission pending verification.'}
        cid=app.store.create(owner,assessment,generation)
        add(state,REVIEW_MESSAGE,kind='application received',case_id=cid)
        state['last_assessment']={'status':'Pending verification and review'}
        state['previous_question']='application verification and human review'
        state['draft']=None;state['step']=0;return
    # A question during the guided application does not overwrite the requested financial field.
    if state['draft'] is not None and state['step']<len(FIELDS) and '?' not in text and not command.startswith(('ask ','/ask ')):
        field=FIELDS[state['step']][0]
        try:
            if field=='employment_type':
                value={'salaried':'salaried','salary':'salaried','self employed':'self_employed','self-employed':'self_employed','self_employed':'self_employed'}.get(command)
                if not value:raise ValueError('Please choose salaried or self-employed.')
            else:value=number(text,field)
            state['draft'][field]=value;state['step']+=1
            if state['step']==len(FIELDS):summary(state)
            else:add(state,FIELDS[state['step']][1],kind='question')
        except ValueError as exc:
            if not any(c.isalpha() for c in text) or field=='employment_type':
                add(state,str(exc),kind='question');return
        else:
            return
    if state['draft'] is not None and state['step']==len(FIELDS) and command in ('yes','ok','confirm'):
        add(state,'Please use the Submit application button to submit the values shown above.',kind='guide');return
    question=re.sub(r'^/?ask\s+','',text,flags=re.I)
    try:result=groq_rag.answer(question,app.policy,key,state['previous_question'],state['last_assessment'],history=state['messages'][:-1])
    except groq_rag.GroqError as exc:result={'text':str(exc),'kind':'connection or evidence check','sources':[]}
    add(state,**result)
    if result.get('topic') and guardrails.canonical(question) not in guardrails.FOLLOWUPS:
        state['previous_question']=question
    if state['draft'] is not None and state['step']<len(FIELDS):add(state,'When you’re ready: '+FIELDS[state['step']][1],kind='question')
