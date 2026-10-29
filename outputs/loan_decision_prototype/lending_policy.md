# Cedar Demo Bank Personal Loan Policy

Version 1.0 | Fictional classroom policy

Not a real bank policy or financial advice. Canonical source: policy.json.

## P01 Product scope

This fictional policy covers unsecured personal loans to salaried applicants. Self-employed income, business loans, collateral and joint applicants are outside this prototype. Refer out-of-scope applications to a human specialist; do not infer eligibility from missing rules.

## P02 Income and document checks

Annual gross income must be at least INR 240,000 for standard processing. Lower income requires an exception review. Before any final decision, the loan officer checks income evidence, existing liabilities and applicant identity. The prototype collects financial values only and does not collect identity documents.

## P03 Credit history

A credit score below 650 requires manual exception review. A score at or above 650 is not a promise of approval. The model may recommend rejection even where this threshold is met, because it combines several financial features.

## P04 Affordability and debt service

Total debt service is existing monthly debt payments plus the estimated monthly payment for the requested loan. Divide this total by gross monthly income to obtain the total debt-service ratio. A ratio above 40% requires manual exception review. An illustrative fixed annual rate of 12% is used solely to calculate the proposed monthly payment; it is not an offered interest rate.

## P05 Recent repayment history

Two or more late payments during the last twelve months require manual exception review. Zero or one late payment does not guarantee approval. A reviewer should allow the applicant to correct an inaccurate payment record.

## P06 Loan amount and term

Standard requested amounts range from INR 50,000 to INR 1,000,000 and standard terms range from 12 to 60 months. An amount greater than annual income also requires review. Values outside those product limits require a documented exception; unsupported or invalid inputs must not silently receive a standard approval.

## P07 Model uncertainty and explanation

The model estimates the probability of full repayment under a synthetic-data simulation. Its recommendation is Approve or Reject at the selected decision threshold. A score within 0.05 of that threshold is borderline and requires explicit discussion in the review note. Feature contributions describe associations in the model, not proven causes or real-world creditworthiness. Inputs outside the model training ranges require explicit review because the score extrapolates beyond the simulated examples.

## P08 Human decision and accountability

Every model recommendation remains Pending review until a loan officer signs off. The officer may approve, reject or request more information. An approval with a policy review flag requires a written exception reason. Out-of-scope cases must be referred or rejected, not approved under this policy. LLM text is a draft and has no authority to change the model recommendation or release a loan.

## P09 Customer explanation and correction

Explain the model recommendation using the supplied applicant values and cited clauses. Distinguish model factors from policy review triggers. State that a human review is required. Do not invent a rule, guarantee approval, invent documents, or provide legal advice. When the policy does not cover a situation, state the gap and request specialist review. Applicants may correct data and request human reconsideration.

## P10 Privacy and fairness

Use synthetic applicants for this classroom system. Do not collect names, government identifiers, gender, caste, religion, address or health information. Their exclusion does not establish fairness because financial fields may act as proxies. Synthetic cases and reviewer notes are stored locally for the demonstration. The LLM receives financial values and relevant policy clauses only when a key is configured and the applicant opts in. Production deployment requires representative evaluation, access controls, retention rules and qualified policy review.
