# Prompt log

| Stage | Key prompt or instruction | Observed issue | Change |
|---|---|---|---|
| Coding assistant | Build a synthetic-data loan model, policy retrieval, explanation UI and human review checkpoint. | The first baseline implementation predicted all approvals while calling itself majority class. | Corrected the baseline to all rejections and reran metrics. |
| LLM draft in app | Explain the supplied recommendation using only retrieved policy snippets; cite section IDs and require loan officer review. | No live LLM key was available during packaging, so hallucination rate is not measured. | Added a labelled deterministic fallback and output checks. A team member must test a labelled set of prompts before the final demo. |

The full LLM system prompt is in `loan_core.py`. Do not claim this log demonstrates tested LLM accuracy.
