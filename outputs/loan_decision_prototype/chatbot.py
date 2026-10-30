"""Session-local conversation state. Financial decisions always use the existing ML model."""
import re, math
import loan_core,groq_rag,guardrails

FIELDS=[('income','What is your annual gross income in INR? Example: 1440000.'),
 ('monthly_debt','How much do you already pay toward debt each month, in INR? Example: 5000.'),
 ('loan_amount','How much would you like to borrow, in INR? Example: 200000.'),
 ('term_months','Over how many months will you repay the loan? Example: 36.'),
 ('credit_score','What is your credit score? Enter a number from 300 to 900.'),
 ('late_payments','How many late payments have you had in the last 12 months? Example: 0.'),
 ('employment_years','How many years of employment experience do you have? Example: 10.'),
 ('employment_type','Are you salaried or self-employed?')]
WELCOME='Hi! I’m Cedar’s loan assistant. Ask about our fictional lending policy or choose Check my eligibility. I can help only with loans and policy guidance. Every recommendation needs human review. Use synthetic examples only.'

def new_state():return {'messages':[{'role':'assistant','text':WELCOME,'kind':'welcome'}],'draft':None,'step':0,'previous_question':'','last_assessment':None,'busy':False}
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
    if not math.isfinite(value) or not lo<=value<=hi:raise ValueError(f'Please enter a value between {lo:,} and {hi:,}.')
    if key!='employment_years' and not value.is_integer():raise ValueError('Please enter a whole number.')
    return value if key=='employment_years' else int(value)

def summary(state):
    x=state['draft'];lines=['Please check these synthetic details before I assess them:']
    for key,_ in FIELDS:
        value=x[key];label=key.replace('_',' ').title()
        lines.append(f'{label}: {value:,}' if isinstance(value,(int,float)) else f'{label}: {value.replace("_"," ")}')
    lines.append('Choose Confirm assessment to run the local model. If explanations are enabled, these values and policy evidence will also be sent to an external AI service. Choose Start over to change them.')
    add(state,'\n'.join(lines),kind='confirm')

def handle(state,text,app,owner,key):
    text=text.strip()
    if not text or len(text)>1500:raise ValueError('Please send a message of 1–1,500 characters.')
    if re.search(r'\b(gsk_|sk-or-|sk-proj-)',text):raise ValueError('Keep your API key in the .env file, never the chat box.')
    add(state,text,'user');command=text.lower()
    if command in ('start over','/reset','cancel','/cancel'):
        state['draft']=None;state['step']=0;state['last_assessment']=None;state['previous_question']=''
        add(state,'Application draft cleared. Ask a policy question or choose Check my eligibility. Previously submitted cases remain in the local review queue.',kind='guide');return
    if command in ('check my eligibility','/apply','apply','i want a loan'):
        state['draft']={};state['step']=0;add(state,FIELDS[0][1],kind='question');return
    if command in ('demo approval','demo rejection','demo edge'):
        state['draft']=dict(loan_core.DEMO_CASES[command.split()[-1]]);state['step']=len(FIELDS);summary(state);return
    if command in ('confirm assessment','/submit'):
        if state['draft'] is None or state['step']!=len(FIELDS):
            add(state,'Please complete the financial details first. Choose Check my eligibility.',kind='guide');return
        assessment=loan_core.assess(app.model,state['draft'],app.policy)
        generation=groq_rag.explain(assessment,key)
        cid=app.store.create(owner,assessment,generation)
        title='Human specialist review required' if not assessment['scope_supported'] else 'Provisional recommendation: '+assessment['recommendation']
        message=f'{title}\nLocal model: {assessment["recommendation"]} · Synthetic repayment score: {assessment["probability"]:.1%}\nThis is not a final loan decision.'
        if assessment['flags']:message+='\n\nPolicy flags:\n'+'\n'.join(f'[{f["clause"]}] {f["message"]}' for f in assessment['flags'])
        if generation['status']=='generated':
            message+='\n\n'+generation['draft']['summary']+'\n\n'+'\n'.join(f'[{r["clause_id"]}] {r["explanation"]}' for r in generation['draft']['reasons'])
        else:message+='\n\n'+generation['message']
        add(state,message,kind='assessment explanation' if generation['status']=='generated' else 'local assessment',sources=assessment['evidence'],case_id=cid)
        state['last_assessment']={'recommendation':assessment['recommendation'],'input':assessment['input'],'flags':assessment['flags'],'scope_supported':assessment['scope_supported']}
        state['previous_question']='loan assessment recommendation '+assessment['recommendation']+' '+ ' '.join(f['message'] for f in assessment['flags'])
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
        add(state,'Please use the Confirm assessment button to submit the values shown above.',kind='guide');return
    question=re.sub(r'^/?ask\s+','',text,flags=re.I)
    try:result=groq_rag.answer(question,app.policy,key,state['previous_question'],state['last_assessment'],history=state['messages'][:-1])
    except groq_rag.GroqError as exc:result={'text':str(exc),'kind':'connection or evidence check','sources':[]}
    add(state,**result)
    if result.get('sources') and guardrails.canonical(question) not in guardrails.FOLLOWUPS:
        state['previous_question']=question
    if state['draft'] is not None and state['step']<len(FIELDS):add(state,'When you’re ready: '+FIELDS[state['step']][1],kind='question')
