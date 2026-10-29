# Deploy Cedar on Streamlit Community Cloud

1. Put this prototype folder in a GitHub repository. Exclude `.env`, `data/`, virtual environments and `.streamlit/secrets.toml`. Keep all Python modules, `policy.json`, `model_artifact.json` and `requirements.txt`.
2. Sign in to https://share.streamlit.io with GitHub and choose Create app.
3. Select the repository and branch. If uploading this whole workspace, main file path is `outputs/loan_decision_prototype/streamlit_app.py`. If this prototype folder is the repository root, use `streamlit_app.py`.
4. In Advanced settings choose Python 3.13 and add these secrets, replacing the placeholder privately:

```toml
GROQ_API_KEY = "your_actual_key"
GROQ_MODEL = "openai/gpt-oss-20b"
```

5. Deploy. Test a greeting, a follow-up, Demo approval → Confirm assessment, My demo cases, and New conversation.

The key stays on the server. Never commit it or paste it into chat. Groq account quotas still apply. Chat state is per browser session; a disconnected or reloaded session may reset it. SQLite case storage is temporary on Community Cloud; export any demo evidence you need before restarting. Only the current session's cases appear in My demo cases. Reviewer controls are classroom role-play.

## Local run from workspace root

```sh
python3 -m venv .venv-streamlit
.venv-streamlit/bin/python -m pip install -r outputs/loan_decision_prototype/requirements.txt
.venv-streamlit/bin/streamlit run outputs/loan_decision_prototype/streamlit_app.py
```

Locally the app reads the existing prototype `.env`. In Community Cloud use app Secrets instead.
