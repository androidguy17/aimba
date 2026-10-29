"""Python-standard-library demo server with session ownership and officer sign-off."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import parse_qs,urlsplit
import hmac,os,secrets,time,threading
import loan_core,rag,ui
from policy import Policy
from storage import Store

ROOT=Path(__file__).parent

class App:
    def __init__(self,db_path=None,password=None):
        self.model=loan_core.load_model();self.policy=Policy()
        self.store=Store(db_path or os.environ.get('LOAN_DB_PATH',str(ROOT/'data'/'demo.sqlite3')))
        # Classroom demo: reviewer access is selected without a password.
        self.sessions={};self.lock=threading.Lock()
    def session(self,cookie):
        jar=SimpleCookie()
        try:jar.load(cookie or '')
        except Exception:pass
        token=jar['loan_session'].value if 'loan_session' in jar else ''
        with self.lock:
            # Demo sessions expire after 12 hours. SQLite case ownership remains private.
            self.sessions={k:v for k,v in self.sessions.items() if time.time()-v['created']<43200}
            if token not in self.sessions:
                token=secrets.token_urlsafe(32);self.sessions[token]={'csrf':secrets.token_urlsafe(32),'reviewer':False,'created':time.time(),'login_attempts':[]}
            return token,self.sessions[token]

def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,fmt,*args):
            # Do not log URLs, credentials, application bodies or reviewer notes.
            pass
        def context(self):
            self.token,self.session=app.session(self.headers.get('Cookie'))
            return {**self.session,'llm':bool(os.environ.get('OPENROUTER_API_KEY')),'page':urlsplit(self.path).path}
        def reply(self,body,status=200,content_type='text/html; charset=utf-8',location=None):
            data=body.encode() if isinstance(body,str) else body
            self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            secure='; Secure' if os.environ.get('COOKIE_SECURE')=='1' else ''
            if hasattr(self,'token'):self.send_header('Set-Cookie',f'loan_session={self.token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200{secure}')
            if location:self.send_header('Location',location)
            self.end_headers();self.wfile.write(data)
        def redirect(self,location):self.reply('',303,location=location)
        def do_GET(self):
            ctx=self.context();path=urlsplit(self.path).path;q=parse_qs(urlsplit(self.path).query)
            if path=='/style.css':return self.reply((ROOT/'style.css').read_bytes(),content_type='text/css')
            if path=='/health':return self.reply('ok',content_type='text/plain')
            if path=='/':return self.reply(ui.home(ctx,loan_core.DEMO_CASES.get(q.get('case',[''])[0]),app.store.list_cases(self.token)))
            if path=='/policy':return self.reply(ui.policy_page(ctx,app.policy))
            if path=='/evaluation':return self.reply(ui.evaluation(ctx,app.model))
            if path=='/about':return self.reply(ui.about(ctx))
            if path in ('/review','/login'):return self.reply(ui.review_page(ctx,app.store.list_cases() if ctx['reviewer'] else []))
            if path=='/case':
                case=app.store.get(q.get('id',[''])[0])
                if case and (case['owner']==self.token or ctx['reviewer']):return self.reply(ui.case_page(ctx,case))
            self.reply(ui.layout('Page not found',ui.notice('This page or application is not available in your session.'),ctx),404)
        def do_POST(self):
            ctx=self.context();path=urlsplit(self.path).path
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=16384:raise ValueError('Invalid or oversized form.')
                form={k:v[0] for k,v in parse_qs(self.rfile.read(size).decode('utf-8'),keep_blank_values=True).items()}
                if not hmac.compare_digest(form.get('csrf','').encode(),self.session['csrf'].encode()):
                    return self.reply(ui.layout('Form expired',ui.notice('Reload the page and try again.'),ctx),403)
                if path=='/apply':
                    assessment=loan_core.assess(app.model,form,app.policy)
                    generation=rag.generate(assessment) if form.get('use_llm')=='yes' else {'status':'not_requested','message':'LLM generation was not requested. Submit a new case with the OpenRouter checkbox to request it.','draft':None,'requested_model':None,'resolved_model':None,'usage':None}
                    cid=app.store.create(self.token,assessment,generation)
                    return self.redirect('/case?id='+cid)
                if path=='/login':
                    self.session['reviewer']=True;self.session['csrf']=secrets.token_urlsafe(32)
                    return self.redirect('/review')
                if path=='/logout':
                    self.session['reviewer']=False;self.session['csrf']=secrets.token_urlsafe(32);return self.redirect('/')
                if path=='/signoff':
                    if not self.session['reviewer']:return self.reply(ui.layout('Officer access required',ui.notice('Sign in as the demo officer first.'),ctx),403)
                    if form.get('reviewed')!='yes':raise ValueError('Confirm that you reviewed the case and source evidence.')
                    app.store.review(form.get('case_id',''),form.get('decision',''),form.get('note',''),form.get('exception')=='yes',Policy().fingerprint)
                    return self.redirect('/case?id='+form['case_id'])
                self.reply(ui.layout('Page not found','',ctx),404)
            except (ValueError,KeyError,UnicodeDecodeError) as exc:
                self.reply(ui.layout('Please check this request',ui.notice(str(exc))+'<p><a href="/">New application</a> · <a href="/review">Review queue</a></p>',ctx),400)
    return Handler

def main():
    app=App();host=os.environ.get('HOST','127.0.0.1');port=int(os.environ.get('PORT','8000'))
    server=ThreadingHTTPServer((host,port),make_handler(app))
    print(f'Open http://localhost:{port}',flush=True)
    print('Demo reviewer access: no password required',flush=True)
    print('LLM:',os.environ.get('OPENROUTER_MODEL','openrouter/free') if os.environ.get('OPENROUTER_API_KEY') else 'not connected; no LLM prose will be generated',flush=True)
    print('Use synthetic applications only. Stop with Ctrl+C.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
