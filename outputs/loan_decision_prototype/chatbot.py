"""Session-local conversation state. Financial decisions always use the existing ML model."""
import re, math
import loan_core,groq_rag,guardrails,intake

FIELDS=[('income','How much do you earn? You can say “16 lakh per year” or “50k a month”; I’ll convert it to annual income in rupees.'),
 ('monthly_debt','How much do you pay toward existing debt each month? For example, “my EMIs are 10k” or “no debt”.'),
 ('loan_amount','How much would you like to borrow? You can say “five lakh rupees”, “500k”, or describe the amount naturally.'),
 ('term_months','How long would you like to repay the loan over? You can say “3 years” or “36 months”.'),
 ('credit_score','What credit score is shown on your report? You can write it in digits or words.'),
 ('late_payments','Have you had any late payments in the last year? Tell me how many, or say “none”.'),
 ('employment_years','How long have you been working? For example, “five years” or “18 months”.'),
 ('employment_type','How do you work — are you salaried, self-employed, or a freelancer?')]
WELCOME='Hi! I’m Cedar’s loan assistant. Ask about our fictional lending policy or choose Check my eligibility. I can help only with loans and policy guidance. Every recommendation needs human review. Use synthetic examples only.'

def new_state():return {'messages':[{'role':'assistant','text':WELCOME,'kind':'welcome'}],'draft':None,'step':0,'previous_question':'','last_assessment':None,'busy':False}
def add(state,text,role='assistant',**extras):
    state['messages'].append({'role':role,'text':text,**extras});state['messages']=state['messages'][-40:]
def number(text,key):
    return intake.numeric(text,key)

def understood(name,value):
    if name in ('income','monthly_debt','loan_amount'):
        period=' per year' if name=='income' else ' per month' if name=='monthly_debt' else ''
        return name.replace('_',' ').capitalize()+f': ₹{value:,}'+period
    if name=='employment_type':return 'Employment: '+value.replace('_',' ')
    unit=' months' if name=='term_months' else ' years' if name=='employment_years' else ''
    return name.replace('_',' ').capitalize()+f': {value:g}'+unit

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
    # A natural loan request may start intake and supply facts in the same turn.
    if state['draft'] is None and re.match(r'(?i)^(?:check my eligibility\b|i (?:want|need|would like)(?: to (?:borrow|apply))?(?: a)? loan\b|i want to borrow\b)',text) and re.search(r'(?i)\d|\b(lakh|lac|thousand|income|salary|score)\b',text):
        state['draft']={};state['step']=0
        add(state,'Let’s check your eligibility. I’ll record the details you share and ask for anything missing.',kind='guide')
    # Interpret application facts before policy routing, including complete sentences.
    active=state['draft'] is not None
    policy_question=bool(re.match(r'(?i)^(?:/?ask |what (?:is|are)|how (?:does|do)|why |can (?:i|you)|is (?:there|it))',text))
    if policy_question and re.search(r'(?i)\b(my|i earn|i make|i pay|i have)\b',text) and re.search(r'(?i)\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|lakh|lac)\b',text):
        policy_question=False
    if active and not policy_question:
        field=FIELDS[min(state['step'],len(FIELDS)-1)][0]
        if state['step']==len(FIELDS) and command in ('yes','ok','confirm'):
            add(state,'Please use the Confirm assessment button to submit the values shown above.',kind='guide');return
        try:
            values=intake.extract(text,field,key)
        except intake.Clarify as exc:
            # Clarification stays in the application, never becomes a general chat task.
            add(state,str(exc),kind='question');return
        state['draft'].update(values)
        state['step']=next((i for i,(name,_) in enumerate(FIELDS) if name not in state['draft']),len(FIELDS))
        add(state,'Got it — '+ '; '.join(understood(name,value) for name,value in values.items())+'.',kind='details recorded')
        if state['step']==len(FIELDS):summary(state)
        else:add(state,FIELDS[state['step']][1],kind='question')
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
