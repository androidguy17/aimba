# OpenRouter connection

Create an API key in your OpenRouter dashboard at https://openrouter.ai/settings/keys. Copy it once. Do not paste the key into chat or commit it to code.

The simplest launch is `python3 run.py`: paste the key into its hidden prompt, then open http://localhost:8000 and check the explanation box when submitting a synthetic case. The default `openrouter/free` router uses available free models. It can vary the actual model; each case records the returned model ID. For repeatable evaluation, select a specific currently available model in the account and set OPENROUTER_MODEL.

To use a key in the same macOS zsh terminal for the app and evaluation script:

```bash
read -s "OPENROUTER_API_KEY?Paste OpenRouter key: "
echo
export OPENROUTER_API_KEY
python3 app.py
```

Stop with Ctrl+C, then run `python3 evaluate_llm.py` in the same terminal. No paid model is selected automatically. If you choose a paid model via OPENROUTER_MODEL, requests use your OpenRouter credits.

Free endpoints can rate limit or fail. Provider errors are shown explicitly. A generated explanation must also pass checks for unchanged recommendation, required review language, cited clauses and exact source quotations. Human interpretation checks remain necessary. Use synthetic data only.

Official references: https://openrouter.ai/openrouter/free and https://openrouter.ai/docs/api/reference/overview
