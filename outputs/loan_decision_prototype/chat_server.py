"""Local classroom chatbot backed by the saved classifier, policy and Groq."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
import json,os,secrets,threading,time,hmac,html
from urllib.parse import urlsplit,parse_qs
import loan_core,chatbot,groq_rag
from policy import Policy
from storage import Store
ROOT=Path(__file__).parent

def load_env():
    path=ROOT/'.env'
    if not path.exists():return
    for raw in path.read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line:continue
        k,v=line.split('=',1)
        if k.strip() in ('GROQ_API_KEY','GROQ_MODEL','PORT') and k.strip() not in os.environ:
            os.environ[k.strip()]=v.strip().strip('"\'')

class Application:
    def __init__(self):
        self.model=loan_core.load_model();self.policy=Policy()
        self.store=Store(os.environ.get('CHAT_DB_PATH',str(ROOT/'data'/'chat_demo.sqlite3')))
        self.sessions={};self.lock=threading.Lock()
    def session(self,cookie):
        jar=SimpleCookie()
        try:jar.load(cookie or '')
        except Exception:pass
        token=jar['cedar_chat'].value if 'cedar_chat' in jar else ''
        with self.lock:
            self.sessions={k:v for k,v in self.sessions.items() if time.time()-v['created']<43200}
            if token not in self.sessions:
                token=secrets.token_urlsafe(24)
                self.sessions[token]={'csrf':secrets.token_urlsafe(24),'created':time.time(),'chat':chatbot.new_state(),'lock':threading.Lock()}
            return token,self.sessions[token]

def handler(app):
 class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,body,status=200,ctype='application/json; charset=utf-8'):
        data=body.encode();self.send_response(status)
        self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header('Set-Cookie',f'cedar_chat={self.token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200')
        self.end_headers();self.wfile.write(data)
    def setup_session(self):self.token,self.session=app.session(self.headers.get('Cookie'))
    def state(self):
        s=self.session['chat']
        return {'csrf':self.session['csrf'],'connected':bool(os.environ.get('GROQ_API_KEY')),
            'messages':chatbot.grouped_messages(s['messages']),'draft_active':s['draft'] is not None,'ready':s['draft'] is not None and s['step']==len(chatbot.FIELDS)}
    def do_GET(self):
        self.setup_session()
        if urlsplit(self.path).path=='/case':
            cid=parse_qs(urlsplit(self.path).query).get('id',[''])[0]
            case=app.store.get(cid)
            if not case or case['owner']!=self.token:return self.reply('Case unavailable',404,'text/plain')
            a=case['assessment'];g=case['generation']
            source=''.join('<li><b>'+html.escape(c['id']+' '+c['title'])+'</b>: '+html.escape(c['text'])+'</li>' for c in a['evidence'])
            body=f'<h1>Case {html.escape(cid[:8])}</h1><p>Provisional recommendation: {html.escape(a["recommendation"])} · score {a["probability"]:.1%}</p><p>LLM: {html.escape(g["status"])}</p><h2>Retrieved policy</h2><ul>{source}</ul>'
            if case['reviews']:
                r=case['reviews'][-1];body+='<h2>Human decision</h2><p>'+html.escape(r['decision']+' — '+r['note'])+'</p>'
            else:
                body+=f'''<h2>Human review</h2><form method="post" action="/review-case"><input type="hidden" name="csrf" value="{self.session['csrf']}"><input type="hidden" name="case_id" value="{html.escape(cid)}"><select name="decision"><option>More information required</option><option>Rejected</option><option>Approved</option></select><p><textarea name="note" minlength="20" required placeholder="Officer reason, at least 20 characters"></textarea></p><p><label><input type="checkbox" name="reviewed" value="yes" required> I reviewed the facts and policy</label></p><p><label><input type="checkbox" name="exception" value="yes"> I acknowledge a policy exception, if needed</label></p><button>Record decision</button></form>'''
            return self.reply('<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Case review</title><style>body{font:16px Arial;max-width:800px;margin:2em auto;padding:1em;line-height:1.5}textarea{width:100%;min-height:90px}li{margin:1em 0}</style></head><body><p><a href="/">← Back to chat</a></p>'+body+'</body></html>',ctype='text/html; charset=utf-8')
        if self.path in ('/','/chat'):return self.reply((ROOT/'chat.html').read_text(),ctype='text/html; charset=utf-8')
        if self.path=='/chat.js':return self.reply((ROOT/'chat.js').read_text(),ctype='application/javascript; charset=utf-8')
        if self.path=='/chat.css':return self.reply((ROOT/'chat.css').read_text(),ctype='text/css; charset=utf-8')
        if self.path=='/api/state':return self.reply(json.dumps(self.state()))
        if self.path=='/health':return self.reply('ok',ctype='text/plain')
        self.reply(json.dumps({'error':'Not found'}),404)
    def do_POST(self):
        self.setup_session()
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=4096:raise ValueError('Invalid message length.')
            if self.path=='/review-case':
                form={k:v[0] for k,v in parse_qs(self.rfile.read(size).decode()).items()}
                if not hmac.compare_digest(form.get('csrf',''),self.session['csrf']):raise ValueError('Session expired.')
                case=app.store.get(form.get('case_id',''))
                if not case or case['owner']!=self.token:raise ValueError('Case unavailable.')
                if form.get('reviewed')!='yes':raise ValueError('Review the case first.')
                app.store.review(form['case_id'],form.get('decision',''),form.get('note',''),form.get('exception')=='yes',app.policy.fingerprint)
                self.send_response(303);self.send_header('Location','/case?id='+form['case_id']);self.send_header('Set-Cookie',f'cedar_chat={self.token}; HttpOnly; SameSite=Strict; Path=/');self.end_headers();return
            obj=json.loads(self.rfile.read(size))
            if not isinstance(obj,dict) or not hmac.compare_digest(str(obj.get('csrf','')),self.session['csrf']):raise ValueError('Session expired. Reload the page.')
            if self.path=='/api/reset':
                with self.session['lock']:
                    self.session['chat']=chatbot.new_state()
                return self.reply(json.dumps(self.state()))
            if self.path!='/api/send':raise ValueError('Unknown action.')
            with self.session['lock']:
                chatbot.handle(self.session['chat'],str(obj.get('text','')),app,self.token,os.environ.get('GROQ_API_KEY',''))
            self.reply(json.dumps(self.state()))
        except (ValueError,TypeError,json.JSONDecodeError) as exc:self.reply(json.dumps({'error':str(exc)}),400)
 return Handler

def main():
    load_env();app=Application();port=int(os.environ.get('PORT','8765'))
    server=ThreadingHTTPServer(('127.0.0.1',port),handler(app))
    print(f'Open http://localhost:{port} — Groq {"connected" if os.environ.get("GROQ_API_KEY") else "not connected"}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
