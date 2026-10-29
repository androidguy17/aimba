# Final demonstration and evaluation plan

## Ten to twelve minute demo

1. Explain the business problem and show the educational-prototype notice (1 minute).
2. Show the held-out synthetic model result against the all-reject baseline (2 minutes): accuracy 80.0% versus 61.0%; approval precision 76.4%; approval recall 70.5%; 34 false approvals and 46 missed approvals in 400 test records.
3. Run the built-in approval case (1 minute): the model recommends approval, retrieves policy sections, and leaves the case pending officer review.
4. Run the rejection case (1 minute): multiple policy triggers are visible and the relevant P1, P2 and P3 sections are retrieved.
5. Run the edge case (1 minute): a credit score below 650 triggers review even when the model's numeric score alone is being shown.
6. With a server-side API key and synthetic values only, request an LLM explanation and show its cited sections (1 minute). If no key is available, clearly state that the app is using its policy template fallback.
7. Discuss cost of errors, human checkpoint, privacy and bias limits, and next steps (3 to 4 minutes).

## LLM evaluation before claiming reliability

Create at least 30 synthetic cases, including borderline values, conflicting policy triggers, a missing rule, and an injection inserted into a copy of the policy. Have two reviewers label each draft for factual correctness, policy citation correctness, unsupported claims, and whether it preserves the model recommendation and officer review. Report the number wrong or hallucinated out of the evaluated total, with three exact failure examples and fixes. The current package has no measured LLM error rate because no live LLM key was used during packaging.

## Business case and build versus rent decision

A three-year cost comparison should use the bank's actual volumes, reviewed vendor quotes, hosting rates, security controls and human-review workload. A defensible classroom illustration is:

| Cost assumption | Classroom estimate |
|---|---:|
| Initial build, 2 engineer-months at ₹150,000/month | ₹300,000 |
| Hosting and monitoring, ₹4,000/month for 36 months | ₹144,000 |
| LLM use, 30,000 drafts/month at assumed ₹0.25/draft for 36 months | ₹270,000 |
| Policy maintenance and review, 4 hours/month at ₹1,000/hour for 36 months | ₹144,000 |
| Illustrative three-year total | ₹858,000 |

These are assumptions, not quotes. A bank should rent an established lending workflow for production compliance and build only the explainable prototype or differentiating layer after policy, security and data validation. This prototype's total does not include procurement, independent validation, legal review, audit, incident response or loan officers' decision time; those could dominate the real cost.

## Peer challenge cases

- Enter unsupported extreme values; confirm the app rejects them.
- Insert instruction-like text into a test policy copy; confirm the LLM does not follow it.
- Check a borderline model score against policy flags; the officer must resolve the conflict.
- Ask why a protected attribute is absent but proxy bias can remain.
- Disconnect the LLM or give an invalid key; the app must label the template fallback.
