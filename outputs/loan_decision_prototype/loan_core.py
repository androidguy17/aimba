"""Synthetic repayment classifier. No provider or LLM is involved in prediction."""
from pathlib import Path
import csv, json, math, random

ROOT=Path(__file__).parent
FEATURE_NAMES=['Credit score','Total debt-service ratio','Loan relative to income','Recent late payments','Employment years']
LIMITS={'income':(120000,5000000),'monthly_debt':(0,200000),'loan_amount':(10000,2000000),
        'term_months':(6,84),'credit_score':(300,900),'late_payments':(0,12),'employment_years':(0,40)}

def validate(raw):
    x={}
    for key,(lo,hi) in LIMITS.items():
        try:v=float(raw[key])
        except (KeyError,ValueError,TypeError):raise ValueError(f'{key.replace("_"," ")} must be a number.')
        if not math.isfinite(v) or not lo<=v<=hi:raise ValueError(f'{key.replace("_"," ")} must be between {lo:,} and {hi:,}.')
        if key!='employment_years' and not v.is_integer():raise ValueError(f'{key.replace("_"," ")} must be a whole number.')
        x[key]=v if key=='employment_years' else int(v)
    x['employment_type']=raw.get('employment_type','salaried')
    if x['employment_type'] not in ('salaried','self_employed'):raise ValueError('Choose a supported employment type.')
    return x

def derived(x,apr=.12):
    r=apr/12; n=x['term_months']
    payment=x['loan_amount']*r/(1-(1+r)**(-n)) if r else x['loan_amount']/n
    return {'proposed_payment':round(payment,2),'total_dti':(x['monthly_debt']+payment)/(x['income']/12),
            'loan_income_ratio':x['loan_amount']/x['income']}

def features(x):
    d=derived(x)
    return [(x['credit_score']-680)/100,d['total_dti'],d['loan_income_ratio'],x['late_payments']/3,x['employment_years']/10]

def sigmoid(z):return 1/(1+math.exp(-max(-35,min(35,z))))

def synthetic_data(n=2400,seed=12):
    rng=random.Random(seed);rows=[]
    for i in range(n):
        income=rng.randint(240000,2400000)
        x={'income':income,'monthly_debt':int(income/12*rng.uniform(0,.6)),
           'loan_amount':rng.randint(50000,1000000),'term_months':rng.choice((12,24,36,48,60)),
           'credit_score':rng.randint(520,830),'late_payments':rng.choices((0,1,2,3,4),(.55,.23,.13,.06,.03))[0],
           'employment_years':round(rng.uniform(0,18),1),'employment_type':'salaried'}
        d=derived(x)
        latent=2.2+.013*(x['credit_score']-680)-3.7*d['total_dti']-.5*d['loan_income_ratio']-.7*x['late_payments']+.05*x['employment_years']
        rows.append((x,int(rng.random()<sigmoid(latent))))
    return rows

def train(rows,steps=500):
    design=[([1]+features(x),y) for x,y in rows];w=[0.0]*6
    for _ in range(steps):
        grad=[0.0]*6
        for f,y in design:
            error=sigmoid(sum(a*b for a,b in zip(w,f)))-y
            for j in range(6):grad[j]+=error*f[j]
        for j in range(6):w[j]-=.2*(grad[j]/len(rows)+(0 if j==0 else .002*w[j]))
    return w

def probability(model,x):return sigmoid(sum(a*b for a,b in zip(model['weights'],[1]+features(x))))

def metrics(rows,model,threshold=None,constant=None):
    threshold=model['threshold'] if threshold is None else threshold
    outcomes=[(y,constant if constant is not None else int(probability(model,x)>=threshold)) for x,y in rows]
    tp=sum(y==1 and p==1 for y,p in outcomes);fp=sum(y==0 and p==1 for y,p in outcomes)
    tn=sum(y==0 and p==0 for y,p in outcomes);fn=sum(y==1 and p==0 for y,p in outcomes)
    precision=tp/(tp+fp) if tp+fp else 0;recall=tp/(tp+fn) if tp+fn else 0
    return {'n':len(rows),'accuracy':(tp+tn)/len(rows),'precision':precision,'recall':recall,
            'f1':2*precision*recall/(precision+recall) if precision+recall else 0,
            'tp':tp,'fp':fp,'tn':tn,'fn':fn,'error_cost_units':5*fp+fn,
            'brier':sum((probability(model,x)-y)**2 for x,y in rows)/len(rows) if constant is None else None}

def build_model():
    rows=synthetic_data();random.Random(44).shuffle(rows)
    training,validation,test=rows[:1440],rows[1440:1920],rows[1920:]
    model={'weights':train(training),'threshold':.5,'version':'2.0','seed':12,'split_seed':44,
           'illustrative_apr':.12,'training_bounds':{'income':[240000,2400000],'monthly_debt':[0,120000],'loan_amount':[50000,1000000],'term_months':[12,60],'credit_score':[520,830],'late_payments':[0,4],'employment_years':[0,18]},
           'target':'simulated full repayment','training_n':len(training),'validation_n':len(validation),'test_n':len(test),
           'feature_names':FEATURE_NAMES,'feature_means':[sum(features(x)[j] for x,y in training)/len(training) for j in range(5)],
           'threshold_selection':'Lowest validation cost, 5 units per false approval and 1 per missed approval; ties favour lower threshold.'}
    candidates=[round(.3+i*.025,3) for i in range(25)]
    model['threshold']=min(candidates,key=lambda t:(metrics(validation,model,t)['error_cost_units'],t))
    majority=int(sum(y for _,y in training)>=len(training)/2)
    model['baseline_class']=majority
    model['test_metrics']=metrics(test,model);model['baseline_metrics']=metrics(test,model,constant=majority)
    model['validation_metrics']=metrics(validation,model)
    model['test_at_050']=metrics(test,model,.5)
    model['limitations']=['All outcomes are simulated; no real bank records were used.','The generator uses the same predictors as the classifier, so the task is favourable to this model.','The cost ratio and decision threshold are classroom assumptions.','Scores are not calibrated or validated for real lending; no demographic fairness claim is made.']
    return model,training,validation,test

def load_model():return json.loads((ROOT/'model_artifact.json').read_text())

def assess(model,raw,policy):
    if policy.data['illustrative_apr']!=model['illustrative_apr']:raise ValueError('Policy APR differs from the model assumptions. Review and retrain before using this policy.')
    x=validate(raw);d=derived(x,policy.data['illustrative_apr'])
    p=probability(model,x);threshold=model['threshold'];decision='Approve' if p>=threshold else 'Reject'
    flags=policy.checks({**x,**d,'threshold_distance':abs(p-threshold)})
    outside=[key.replace('_',' ') for key,(lo,hi) in model['training_bounds'].items() if not lo<=x[key]<=hi]
    if outside:flags.append({'clause':'P07','message':'Outside the synthetic training ranges: '+', '.join(outside)+'.','severity':'review'})
    contributions=[{'feature':name,'contribution':w*(f-mean)} for name,w,f,mean in zip(FEATURE_NAMES,model['weights'][1:],features(x),model['feature_means'])]
    contributions.sort(key=lambda c:-abs(c['contribution']))
    query=f"{decision} recommendation. Credit history score {x['credit_score']}; total debt service affordability; recent late payments {x['late_payments']}; {x['employment_type'].replace('_',' ')} income; loan amount and term. "+' '.join(f['message'] for f in flags)
    required={'P08','P09'}|{f['clause'] for f in flags}
    evidence=policy.search(query,k=3,required=required)
    return {'input':x,'probability':p,'threshold':threshold,'recommendation':decision,'derived':d,'flags':flags,
            'contributions':contributions,'retrieval_query':query,'evidence':evidence,
            'policy_version':policy.version,'policy_fingerprint':policy.fingerprint,
            'scope_supported':not any(f['severity']=='scope' for f in flags)}

DEMO_CASES={
    'approval':{'income':1440000,'monthly_debt':5000,'loan_amount':200000,'term_months':36,'credit_score':810,'late_payments':0,'employment_years':10,'employment_type':'salaried'},
    'rejection':{'income':360000,'monthly_debt':15000,'loan_amount':700000,'term_months':24,'credit_score':560,'late_payments':3,'employment_years':1,'employment_type':'salaried'},
    'edge':{'income':1440000,'monthly_debt':5000,'loan_amount':200000,'term_months':36,'credit_score':810,'late_payments':0,'employment_years':10,'employment_type':'self_employed'}}

if __name__=='__main__':
    model,training,validation,test=build_model()
    (ROOT/'model_artifact.json').write_text(json.dumps(model,indent=2)+'\n')
    folder=ROOT/'dataset';folder.mkdir(exist_ok=True)
    with (folder/'synthetic_loans.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(training[0][0])+['simulated_repaid','split']);writer.writeheader()
        for split,data in [('train',training),('validation',validation),('test',test)]:
            for x,y in data:writer.writerow({**x,'simulated_repaid':y,'split':split})
    print(json.dumps({k:model[k] for k in ('threshold','test_metrics','baseline_metrics')},indent=2))
