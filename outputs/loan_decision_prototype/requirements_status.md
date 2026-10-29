# Assignment requirement status

This checklist separates working code from work that still needs a live test or external setup.

| Requirement | Where it is | Status |
|---|---|---|
| Applicant input and interactive UI | `app.py` form and three example links | Built; synthetic cases only |
| Predictive model | `loan_core.py`: `synthetic_data`, `train`, `probability`, `assess` | Built; trained only on synthetic data |
| Baseline, precision, recall and error counts | `loan_core.py`: `metrics`; run `python3 loan_core.py` | Measured on 400 held-out synthetic cases |
| Team-written lending policy | `lending_policy.md` | Built; fictional classroom rules |
| Retrieval part of RAG | `loan_core.py`: `policy_sections` and `retrieve` | Built as rule-based retrieval of policy sections; no embeddings or vector store |
| Generation part of RAG | `loan_core.py`: `llm_explanation` | Wired to OpenRouter; requires a key, checkbox and successful provider response |
| No-key explanation | `loan_core.py`: `fallback_explanation` | Built; deterministic Python template, not an LLM |
| Human checkpoint | `app.py` result remains pending officer review | Demonstrated as a hold; authenticated review and audit trail are not built |
| Prompt injection and output checks | `loan_core.py` system prompt, source IDs and fallback checks | Basic safeguards built; adversarial testing remains |
| LLM error/hallucination evaluation | `evaluate_llm.py` creates 30 drafts and review CSV | Harness built; human ratings and measured rate remain |
| Bias and privacy | UI educational notice; no real records stored | Risks documented; representative fairness audit remains |
| Public demo link | `Procfile` and deployment instructions | Not deployed; team hosting account needed |
| Final presentation and business case | `final_demo_plan.md` | Demo outline and illustrative cost assumptions drafted; live slides and reviewed quotes remain |
| Prompt log | `prompt_log.md` | Started; add real LLM prompts, failures and fixes during testing |

The assignment also requires an approval, rejection and edge case in the demo. All three are available in the app. Do not present the synthetic-data model performance as evidence of real lending accuracy.
