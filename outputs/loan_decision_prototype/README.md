# Streamlit version

Run `streamlit run streamlit_app.py`. See [DEPLOY_STREAMLIT.md](DEPLOY_STREAMLIT.md) for free Community Cloud deployment. The original custom interface remains available below.

# Team 12 Loan Decision Chatbot

**Start here:** [RUN_CHATBOT.md](RUN_CHATBOT.md). The local chatbot is `chat_server.py`; open `http://localhost:8765` after starting it.

Add your Groq API key in the `.env` file in this folder: `GROQ_API_KEY=your_key_here`. The default model is `openai/gpt-oss-20b`, listed in Groq's free-plan limits. The app reads `.env` when it starts; restart it after changing the key. Keep `.env` private; `.env.example` is a shareable template.

The chatbot reuses the trained logistic regression model and fictional Cedar Demo Bank policy. It handles only loan-policy questions with trusted source clauses, asks for the applicant's details conversationally, and shows a provisional recommendation. Groq writes a cited explanation only when connected. Open a submitted case to record the human reviewer decision. Use synthetic applicants only.

---

# Section C Team 12 Loan Decision and Explanation System

This version replaces the earlier minimal prototype. It includes an authored fictional policy, BM25 document retrieval, an OpenRouter explanation component, an authenticated demo officer queue, audit records and reproducible model evaluation. Use synthetic applications only.

## Run on your Mac

Python 3.10 or newer. No extra packages are needed.

```bash
python3 run.py
```

Paste your OpenRouter API key into the hidden terminal prompt, or press Enter to inspect the app without LLM generation. The key stays in process memory. Open http://localhost:8000. The terminal prints a randomly generated **officer review passcode**; use it on the Officer review page. Stop with Ctrl+C.

If Terminal cannot read the Documents folder, use the refreshed copy in `/private/tmp/team12_loan_prototype`. This is a temporary working copy and may be removed by macOS; keep the ZIP or original folder.

With an environment key already configured, `python3 app.py` also works. Default model: `openrouter/free`. Set `OPENROUTER_MODEL` to a specific model ID for consistent evaluation. No paid fallback is automatic. Every generated case records the model returned by OpenRouter.

## Demonstrate the complete flow

1. Choose **01 / Approval**, check the OpenRouter box and assess. Inspect the recommendation, cited explanation and evidence.
2. Open **Officer review**, enter the passcode, open the case, review it and record a decision with a reason.
3. Repeat **02 / Rejection**. Inspect each triggered policy clause.
4. Repeat **03 / Policy gap**. Its finances resemble the approval example, but self-employed income is outside policy scope. The app blocks approval even for an authenticated officer.
5. Show **Lending policy**, **Model evaluation** and **How it works**.

If the LLM key is absent or the provider/output fails, the app explicitly says no LLM explanation was generated. It never disguises a template as an AI explanation.

## Files

| File | Purpose |
|---|---|
| `BUILD_PLAN.md` | Architecture, approach, owners, acceptance criteria and remaining work |
| `policy.json` | Canonical fictional clauses and exact rules |
| `lending_policy.md` | Human-readable policy |
| `policy.py` | BM25 retrieval and generic structured-rule evaluation |
| `loan_core.py` | Data generation, model training, metrics and inference |
| `model_artifact.json` | Trained weights, threshold and measured metrics |
| `dataset/synthetic_loans.csv` | Synthetic records and fixed split membership |
| `rag.py` | Grounded OpenRouter prompt and response validation |
| `app.py`, `ui.py`, `style.css` | HTTP server, user interface, sessions and review routes |
| `storage.py` | Synthetic case records and review audit events |
| `evaluate_llm.py` | Real explanation collection for human evaluation |
| `tests/test_system.py` | Prediction, retrieval, grounding, access and workflow tests |

## Reproduce checks

```bash
python3 -m unittest discover -s tests -v
python3 loan_core.py
python3 policy.py
```

The second command retrains and rewrites the synthetic dataset and model artifact. The third regenerates the Markdown policy from its canonical JSON. If you edit policy.json, restart the server so its retrieval index is rebuilt. Changing the illustrative APR requires reviewing/retraining the model assumptions.

## Evaluate the LLM

With `OPENROUTER_API_KEY` set in the terminal, run:

```bash
python3 evaluate_llm.py
python3 evaluate_llm.py --count 10 --adversarial
```

The script writes `evaluation/llm_review.csv` and full case/prompt/output snapshots in `evaluation/llm_evaluation.json`. Requests are paced, and three consecutive provider failures stop the run. Human graders must label factuality, policy interpretation and hallucination. Automated quote checks are not a factuality score. Separate provider errors, withheld outputs and human-labelled errors in your presentation. All evaluated applicants are synthetic.

## Storage and hosting

The app stores synthetic cases in `data/demo.sqlite3`. This folder, the evaluation results and secrets are excluded from the ZIP and Git. The demo session owns its cases; authenticated officers can view the review queue. Sessions last 12 hours and reset when the server restarts. Reviewer audit events persist in SQLite.

For hosting, configure `HOST=0.0.0.0`, a platform `PORT`, a strong `REVIEWER_PASSWORD`, and `OPENROUTER_API_KEY` as secrets. Set `COOKIE_SECURE=1` only behind HTTPS and set `LOAN_DB_PATH` to a persistent volume. `Dockerfile` and `Procfile` are supplied. A public URL has not been created. This classroom server is not hardened for real applicant traffic.


## Lending-only guardrails

Both the local chatbot and Streamlit use `guardrails.py` and the same server-side response path. General writing, emails, coding, provider questions and common instruction overrides receive a fixed scope reminder. Guided financial fields accept validated numbers or fixed employment choices; those values cannot become model instructions.

For policy chat the model can select up to three retrieved clause IDs. The server validates the complete response schema and renders only the canonical policy text. No model-authored chat prose is displayed. Empty evidence returns a policy-gap notice, malformed selections are withheld, and policy guidance works without a provider key. The model does not receive conversation history. Short follow-ups use only the last accepted lending question.

Assessment explanations are a separate, fixed-purpose task using validated application fields. Existing checks preserve the provisional recommendation, exact citations and human review. Public response checks also withhold the excluded brand name, including common Unicode and punctuation variations. Dashboard labels use Cedar branding; demo-data and external-service disclosures remain accurate.

Run `python3 -m unittest discover -s tests -v` from this folder. Tests cover off-topic requests, loan-keyword bait, instruction overrides, malformed model outputs, history poisoning, brand-name variants and the application flow. These controls limit output capability; keyword matching alone is not a security guarantee. Assessment prose still needs human factual review. Policy files are trusted operator-controlled content. A running or hosted instance must be restarted or redeployed after updating these files; existing browser sessions should start a new conversation.


## Conversational eligibility intake

Eligibility accepts complete sentences, common rupee abbreviations (`10k`, `16 lac`, `16 LPA`), English number words, and explicit monthly/yearly income. Monthly income is annualized; repayment years are converted to months. A short acknowledgement displays the normalized value. The final summary must still be confirmed before assessment.

`intake.py` handles common formats locally without a provider key. For more complex wording, multiple labeled details or corrections, the configured model performs a bounded JSON extraction task. Only known application fields are accepted, source spans must appear in the current message, numeric values must pass server-side bounds, and locally readable sources must agree with the model’s conversions. Model prose is never displayed. Ambiguous alternatives and unsupported currencies request clarification. Multi-field extraction skips details already supplied; it does not change the lending model or automatically submit an assessment.

The extraction request sends the current application answer and requested field to the external service when the local parser cannot handle it. Unrelated instruction requests remain blocked. Include `intake.py` in all deployments. Run `python3 -m unittest discover -s tests -v` for format, conversion, ambiguity, grounding, correction, full-flow and existing guardrail regressions.
