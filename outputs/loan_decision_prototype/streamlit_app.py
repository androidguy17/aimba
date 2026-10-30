"""Streamlit entry point. Run: streamlit run streamlit_app.py."""
import os
import secrets
from pathlib import Path
from types import SimpleNamespace
import streamlit as st
import chatbot
import groq_rag
import loan_core
from policy import Policy
from storage import Store
from customer_guidance import VERSION, public_case
from chat_server import load_env

st.set_page_config(page_title='Cedar · Loan Chat', page_icon='🌿', layout='centered')
load_env()
ROOT = Path(__file__).parent

def setting(name, default=''):
    try:
        return str(st.secrets.get(name, os.environ.get(name, default)))
    except FileNotFoundError:
        return os.environ.get(name, default)

key = setting('GROQ_API_KEY')
os.environ['GROQ_MODEL'] = setting('GROQ_MODEL', groq_rag.DEFAULT_MODEL)

@st.cache_resource
def resources():
    return SimpleNamespace(model=loan_core.load_model(), policy=Policy(),
        store=Store(os.environ.get('CHAT_DB_PATH', str(ROOT/'data'/'streamlit_demo.sqlite3'))))

app = resources()
if ('conversation' not in st.session_state
        or st.session_state.conversation.get('version') != VERSION):
    st.session_state.conversation = chatbot.new_state()
    st.session_state.owner = secrets.token_urlsafe(24)
state = st.session_state.conversation

st.markdown('''<style>
.block-container{max-width:900px;padding-top:2rem}
[data-testid="stChatMessage"]{border:1px solid #e2ebe5;border-radius:16px;animation:arrive .22s ease-out}
@keyframes arrive{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){*{animation:none!important}}
</style>''', unsafe_allow_html=True)

def process(text):
    try:
        with st.spinner('Processing your message…'):
            chatbot.handle(state, text, app, st.session_state.owner, key)
    except ValueError as exc:
        st.session_state.notice = str(exc)

with st.sidebar:
    st.title('🌿 Cedar')
    st.caption('Team 12 · Educational loan assistant')
    if st.button('＋ New conversation', use_container_width=True):
        st.session_state.conversation = chatbot.new_state()
        st.session_state.pop('notice', None)
        st.rerun()
    st.caption('Clears chat and the application draft. Submitted cases remain below for this session.')
    st.divider()
    for label, command in [('Start an application','Check my eligibility')]:
        if st.button(label, use_container_width=True):
            process(command)
            st.rerun()
    if state['draft'] is not None:
        if state['step'] == len(chatbot.FIELDS):
            if st.button('Submit application', type='primary', use_container_width=True):
                process('Submit application')
                st.rerun()
        if st.button('Clear application draft', use_container_width=True):
            process('Start over')
            st.rerun()
    st.divider()
    st.caption('Use synthetic details only. Loan questions may be sent to an external AI service for guidance. Application details are stored for demonstration review; no records are verified here. Cases are temporary on cloud hosting.')

st.title('Chat with Cedar')
st.caption('Ask about loan eligibility, fictional lending policy, or an assessment.')
st.info('Cedar supports lending questions only. Provide accurate details. Applications require verification and human review; this chat cannot approve a loan.')
chat_tab, cases_tab = st.tabs(['Conversation', 'My applications'])
with chat_tab:
    for message in state['messages']:
        user = message['role'] == 'user'
        kind = message.get('kind', 'guide')
        generated = kind == 'assessment explanation'
        with st.chat_message('user' if user else 'assistant', avatar=None if user else '🌿'):
            if not user:
                label = ('Assessment · provisional explanation' if message.get('case_id') and generated
                         else 'Cedar · '+kind)
                st.caption(label)
            st.text(message['text'])
            if message.get('case_id'):
                st.caption('Case '+message['case_id'][:8]+' · open My applications for status')
    if st.session_state.get('notice'):
        st.error(st.session_state.notice)
with cases_tab:
    cases = app.store.list_cases(st.session_state.owner)
    if not cases:
        st.info('Submit a demo assessment to see it here.')
    for record in cases:
        case = public_case(record)
        with st.expander('Application '+case['id'][:8]):
            st.write(case['status'])
            st.text(case['message'])

if prompt := st.chat_input('Type a message to Cedar…', max_chars=1500):
    st.session_state.pop('notice', None)
    with chat_tab:
        with st.chat_message('user'):
            st.text(prompt)
        process(prompt)
    st.rerun()
