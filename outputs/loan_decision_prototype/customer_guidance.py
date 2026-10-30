"""Approved customer wording. Internal underwriting policy is never public content."""
VERSION = 2
REVIEW_MESSAGE = ('Your application has been received and is pending verification and human review. '
    'The details you entered are self-reported and have not been verified. '
    'A reviewer must check supporting income, employment and credit information before a decision. '
    'This chat cannot approve a loan or guarantee an offer. Do not upload identity or financial documents here.')
PRIVATE_RULES_MESSAGE = ('Eligibility depends on a review of your financial circumstances and verified records. '
    'I cannot share internal decision cutoffs, scoring formulas or values to enter to obtain approval. '
    'Please provide accurate information that matches your records. You can ask about the application process '
    'or the factors considered in a review.')
GUIDANCE = {
    'P01': ('Application suitability', 'We review whether the requested loan and your employment circumstances are supported. A loan officer can discuss alternatives if specialist review is needed.'),
    'P06': ('Loan request', 'Tell us the amount you need and your preferred repayment period. Available terms depend on a full review; entering a particular amount does not guarantee approval.'),
    'P03': ('Credit history', 'Credit history is considered alongside income, existing commitments and other application details. A credit score alone does not determine approval. Please use accurate credit information and raise any errors with the credit bureau.'),
    'P04': ('Affordability', 'We consider whether repayments are manageable alongside your income and existing financial commitments. Please report your income and debts accurately. Any rate, repayment amount or loan terms must be confirmed in an offer after review.'),
    'P05': ('Repayment history', 'A reviewer considers your repayment history and any missed payments. Provide accurate details and explain any disputed records to the reviewing officer.'),
    'P02': ('Income and employment information', 'Employment and income information form part of the application review. A reviewer may need supporting records to confirm that information.'),
    'P07': ('Application assessment', 'Applications are reviewed using several financial factors. An automated assessment is not an approval, and changing self-reported figures does not replace verification.'),
    'P08': ('Verification and review', REVIEW_MESSAGE),
    'P09': ('Corrections and explanations', 'You can correct a mistake before submitting your details. After submission, contact the reviewing officer to correct a record or request a plain-language explanation. Do not change accurate information to try to obtain a different result.'),
    'P10': ('Privacy', 'This is an educational demonstration. Use sample details only. Do not send names, identity numbers, bank statements or other private documents in this chat. No funds are released through this service.'),
}

def public_clause(clause):
    title, text = GUIDANCE.get(clause['id'], ('', ''))
    return {'id':clause['id'], 'title':title, 'text':text} if text else None

def public_case(case):
    # Deliberate allowlist: never forward assessment, generation, flags or officer notes.
    return {'id':case['id'], 'status':'Pending verification and review', 'message':REVIEW_MESSAGE}
