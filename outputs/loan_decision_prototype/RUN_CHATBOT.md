# Cedar Loan Chat · local demo

1. Create a free Groq account at https://console.groq.com/ and open **API Keys**. Create a key. Check **Limits** for the exact free allowance on your account.
2. Open `.env` in this folder. Put the key after `GROQ_API_KEY=`. Do not add spaces, quotes or the key to chat messages. `.env` is excluded by `.gitignore`; `.env.example` is safe to share.
3. From a terminal opened in this folder run `python3 chat_server.py`. If your Mac blocks scripts inside Documents, copy this whole folder to a location Terminal can access, then run the same command there.
4. Open http://localhost:8765. Ask a policy question or click **Check my eligibility**. The bot asks for eight fields. Review the summary and click **Confirm assessment**. Try **Demo approval**, **Demo rejection**, and **Policy gap**.

The saved supervised model makes the provisional recommendation. BM25 searches the fictional policy; Policy chat displays only validated source clauses; the model can select clause IDs but cannot supply arbitrary chat prose. Assessment explanations are checked against exact quotations and citation IDs. Human review remains required. Use synthetic details only; connecting Groq sends submitted questions and financial fields to Groq. Without a key, policy guidance and local assessments work, but generated assessment explanations are unavailable.

The default `openai/gpt-oss-20b` is listed in Groq's free-plan limits. A rate limit or model availability error will be shown in the chat. The app uses only Python's standard library, so no package install is needed. Stop the server with Ctrl+C.

The older form interface remains in `app.py` and can be run separately on a different port. The chatbot is the demo entry point in `chat_server.py`. Click the case link after an assessment to record a human decision.
