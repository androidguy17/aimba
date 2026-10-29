"""Versioned fictional policy, exact numeric checks and BM25 text retrieval."""
from collections import Counter
from pathlib import Path
import hashlib, json, math, operator, re

PATH=Path(__file__).with_name('policy.json')
STOP=set('a an the and or to of in on for is are be this that with from by it as at its not must may'.split())
OPS={'lt':operator.lt,'le':operator.le,'gt':operator.gt,'ge':operator.ge,'eq':operator.eq,'ne':operator.ne}

def tokens(text):
    return [w for w in re.findall(r'[a-z0-9]+',text.lower()) if w not in STOP]

class Policy:
    def __init__(self,path=PATH):
        self.data=json.loads(Path(path).read_text()); self.clauses=self.data['clauses']
        self.version=self.data['version']; self.fingerprint=hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
        self.by_id={c['id']:c for c in self.clauses}
        if len(self.by_id)!=len(self.clauses): raise ValueError('Policy IDs must be unique')
        self.docs=[Counter(tokens(c['title']+' '+c['text'])) for c in self.clauses]
        self.lengths=[sum(d.values()) for d in self.docs]; self.avg=sum(self.lengths)/len(self.lengths)
        self.df=Counter(t for d in self.docs for t in d)

    def checks(self,values):
        flags=[]
        for c in self.clauses:
            for r in c['rules']:
                if OPS[r['op']](values[r['field']],r['value']):
                    flags.append({'clause':c['id'],'message':r['message'],'severity':r['severity']})
        return flags

    def search(self,query,k=3,required=()):
        """Search every clause by BM25, then add exact-rule evidence and review obligations.

        Numeric rule evidence is included even when lexical similarity would miss it.
        Scores are text relevance scores, never probabilities or confidence values.
        """
        q=set(tokens(query)); scored=[]; n=len(self.docs)
        for c,tf,length in zip(self.clauses,self.docs,self.lengths):
            score=0.0
            for t in q:
                f=tf[t]
                if f:
                    idf=math.log(1+(n-self.df[t]+.5)/(self.df[t]+.5))
                    score+=idf*f*2.5/(f+1.5*(1-.75+.75*length/self.avg))
            scored.append((score,c))
        scored.sort(key=lambda v:(-v[0],v[1]['id']))
        required=set(required)
        if not required<=self.by_id.keys():raise ValueError('Unknown required policy ID')
        selected={c['id'] for s,c in scored[:k] if s>0}|required
        return [{'id':c['id'],'title':c['title'],'text':c['text'],'score':round(s,3),
                 'reason':'Required policy evidence' if c['id'] in required else 'BM25 text match'}
                for s,c in scored if c['id'] in selected]

    def markdown(self):
        head=f"# {self.data['name']}\n\nVersion {self.version} | Fictional classroom policy\n\nNot a real bank policy or financial advice. Canonical source: policy.json.\n\n"
        return head+'\n\n'.join(f"## {c['id']} {c['title']}\n\n{c['text']}" for c in self.clauses)+'\n'

if __name__=='__main__':
    Path(__file__).with_name('lending_policy.md').write_text(Policy().markdown())
    print('Updated lending_policy.md from policy.json')
