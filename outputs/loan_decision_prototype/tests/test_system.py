import copy, http.cookiejar, io, json, os, re, sys, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import build_opener,HTTPCookieProcessor,Request
from urllib.error import HTTPError
from urllib.parse import urlencode
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from loan_core import load_model,assess,validate,DEMO_CASES
from policy import Policy
from rag import validate_draft,generate
from storage import Store
from app import App,make_handler

class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model=load_model();cls.policy=Policy()
    def assessment(self,name='approval'):return assess(self.model,DEMO_CASES[name],self.policy)
    def draft(self,a):
        ids={'P08'}|{f['clause'] for f in a['flags']}
        sources={c['id']:c for c in a['evidence']}
        return {'recommendation':a['recommendation'],'summary':'This is an explicitly mocked explanation used only in software tests.',
                'human_review_required':True,'reasons':[{'clause_id':cid,'policy_quote':sources[cid]['text'][:100],
                'explanation':'A human must review this applicable policy clause.'} for cid in sorted(ids)]}
    def test_demo_outcomes(self):
        self.assertEqual(self.assessment()['recommendation'],'Approve')
        self.assertEqual(self.assessment('rejection')['recommendation'],'Reject')
        edge=self.assessment('edge');self.assertFalse(edge['scope_supported']);self.assertIn('P01',[f['clause'] for f in edge['flags']])
    def test_input_rejects_nonfinite_and_fractional(self):
        for key,value in [('income','nan'),('income','inf'),('income',0),('term_months',12.5),('credit_score','<script>')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):validate({**DEMO_CASES['approval'],key:value})
    def test_bm25_searches_clause_text(self):
        for query,cid in [('credit score below 650','P03'),('late payments inaccurate record','P05'),('self employed collateral joint applicants','P01'),('debt service monthly payment ratio','P04'),('loan officer final decision human sign off','P08')]:
            self.assertEqual(self.policy.search(query,k=1)[0]['id'],cid)
    def test_every_trigger_is_retrieved(self):
        a=self.assessment('rejection');retrieved={c['id'] for c in a['evidence']}
        self.assertTrue({f['clause'] for f in a['flags']}<=retrieved)
        self.assertTrue({'P08','P09'}<=retrieved)
    def test_policy_boundaries(self):
        a=self.assessment();v={**a['input'],**a['derived'],'threshold_distance':.2}
        exact={**v,'credit_score':650,'total_dti':.4,'late_payments':1}
        self.assertFalse({'P03','P04','P05'}&{f['clause'] for f in self.policy.checks(exact)})
        over={**v,'credit_score':649,'total_dti':.40001,'late_payments':2}
        self.assertTrue({'P03','P04','P05'}<={f['clause'] for f in self.policy.checks(over)})
    def test_valid_mock_explanation(self):
        a=self.assessment('rejection');self.assertEqual(validate_draft(self.draft(a),a)['recommendation'],'Reject')
    def test_bad_quotes_decisions_citations_and_missing_reasons(self):
        a=self.assessment('rejection');base=self.draft(a)
        changes=[lambda d:d.update(recommendation='Approve'),lambda d:d.update(human_review_required=False),
                 lambda d:d['reasons'][0].update(clause_id='P99'),lambda d:d['reasons'][0].update(policy_quote='A fabricated policy that never existed.'),lambda d:d.update(reasons=[])]
        for change in changes:
            d=copy.deepcopy(base);change(d)
            with self.assertRaises(ValueError):validate_draft(d,a)
    def test_no_key_has_no_generation_or_network(self):
        with patch('urllib.request.urlopen') as request:
            result=generate(self.assessment(),key='')
            self.assertEqual(result['status'],'not_configured');self.assertIsNone(result['draft']);request.assert_not_called()
    def test_real_request_shape_with_mock_response(self):
        a=self.assessment();reply={'model':'mock-model','choices':[{'finish_reason':'stop','message':{'content':json.dumps(self.draft(a))}}],'usage':{'total_tokens':100}}
        with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(reply).encode())) as request:
            result=generate(a,key='dummy-for-mock',model='openrouter/free')
            self.assertEqual(result['status'],'generated')
            payload=json.loads(request.call_args.args[0].data)
            self.assertEqual(payload['model'],'openrouter/free')
            self.assertIn('retrieved_policy',json.loads(payload['messages'][1]['content']))
    def test_metric_counts_cover_test_set(self):
        m=self.model['test_metrics'];self.assertEqual(sum(m[k] for k in ('tp','fp','tn','fn')),480)
        self.assertEqual(self.model['training_n']+self.model['validation_n']+self.model['test_n'],2400)

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name)/'test.sqlite');self.policy=Policy();self.model=load_model()
    def tearDown(self):self.temp.cleanup()
    def make_case(self,name):return self.store.create('test-owner',assess(self.model,DEMO_CASES[name],self.policy),{'status':'not_requested'})
    def test_review_records_audit_and_cannot_finalize_twice(self):
        cid=self.make_case('approval');self.assertEqual(self.store.get(cid)['status'],'Pending review')
        self.store.review(cid,'Approved','Reviewed synthetic inputs and policy evidence.',False,self.policy.fingerprint)
        self.assertEqual(len(self.store.get(cid)['reviews']),1)
        with self.assertRaises(ValueError):self.store.review(cid,'Rejected','Second decision is not permitted for this case.',False,self.policy.fingerprint)
    def test_out_of_scope_approval_blocked(self):
        cid=self.make_case('edge')
        with self.assertRaises(ValueError):self.store.review(cid,'Approved','Trying to approve unsupported income by exception.',True,self.policy.fingerprint)
        self.assertEqual(self.store.get(cid)['status'],'Pending review')
    def test_policy_exception_and_changed_policy_blocked(self):
        cid=self.make_case('rejection')
        with self.assertRaises(ValueError):self.store.review(cid,'Approved','Trying to approve without exception acknowledgement.',False,self.policy.fingerprint)
        with self.assertRaises(ValueError):self.store.review(cid,'Rejected','This policy changed after the assessment was created.',False,'wrong-fingerprint')

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.app=App(Path(cls.temp.name)/'web.sqlite',password='test-officer-password')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.app));cls.url=f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
    def setUp(self):self.client=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def get(self,path,client=None):return (client or self.client).open(self.url+path)
    def token(self,path='/'):
        page=self.get(path).read().decode();return re.search('name="csrf" value="([^"]+)"',page).group(1)
    def post(self,path,data):return self.client.open(Request(self.url+path,data=urlencode(data).encode()))
    def test_pages_and_style(self):
        for path in ['/','/policy','/evaluation','/about','/review','/style.css']:
            with self.subTest(path=path):self.assertEqual(self.get(path).status,200)
    def test_real_form_submission_and_private_case(self):
        response=self.post('/apply',{**DEMO_CASES['approval'],'csrf':self.token()});page=response.read().decode();case_url=response.url
        self.assertIn('Pending review',page);self.assertIn('No LLM explanation',page);self.assertIn('RAG evidence trail',page)
        stranger=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
        with self.assertRaises(HTTPError) as err:stranger.open(case_url)
        self.assertEqual(err.exception.code,404)
    def test_csrf_and_unauthorized_review(self):
        with self.assertRaises(HTTPError) as err:self.post('/apply',{**DEMO_CASES['approval'],'csrf':'wrong'})
        self.assertEqual(err.exception.code,403)
        with self.assertRaises(HTTPError) as err:self.post('/signoff',{'csrf':self.token(),'case_id':'missing','reviewed':'yes'})
        self.assertEqual(err.exception.code,403)
    def test_officer_signoff_end_to_end(self):
        response=self.post('/apply',{**DEMO_CASES['approval'],'csrf':self.token()});cid=response.url.split('id=')[1]
        self.post('/login',{'csrf':self.token('/review'),'password':'test-officer-password'})
        page=self.get('/case?id='+cid).read().decode();csrf=re.search('name="csrf" value="([^"]+)"',page).group(1)
        response=self.post('/signoff',{'csrf':csrf,'case_id':cid,'reviewed':'yes','decision':'Approved','note':'Reviewed the synthetic evidence and confirmed policy coverage.'})
        self.assertIn('Recorded officer decision',response.read().decode());self.assertEqual(self.app.store.get(cid)['status'],'Approved')

if __name__=='__main__':unittest.main()
