"""Server-side scope routing and output checks shared by all entry points.

Chat prose is rendered from trusted policy text, never from model-authored text.
Pattern checks are an early rejection layer, not the security boundary.
"""
import re
import unicodedata

REFUSAL = 'I can help only with Cedar loan eligibility, application steps, lending policy and provisional assessment results. Choose Check my eligibility or ask a lending-policy question.'
GAP = 'The supplied Cedar policy does not answer that question. Please ask a loan officer; I cannot invent a policy rule.'
GREETING = 'Hi! I’m Cedar’s loan assistant. Ask about lending policy or choose Check my eligibility.'
FOLLOWUPS = {'why', 'why?', 'explain', 'explain more', 'tell me more', 'what does that mean?', 'what does that mean', 'and why?', 'and why'}

def canonical(text):
    return unicodedata.normalize('NFKC', text).casefold().strip()

def route(text, previous=''):
    value = canonical(text)
    if re.fullmatch(r'(hi|hello|hey|thanks|thank you|help)[!.? ]*', value):
        return 'greeting'
    # Reject instruction overrides and unrelated artifacts even when baited with loan words.
    if re.search(r'ignore|disregard|override|jailbreak|system\s*(prompt|message)|developer\s*(mode|message)|previous\s+instructions|reveal|pretend|role.?play|base64|rot13|<\|', value):
        return 'refuse'
    if re.search(r'\b(email|e-mail|letter|poem|story|essay|recipe|code|script|translate|translation|rewrite|summari[sz]e|song|joke|weather|politics|password|api key|provider|powered by|synthetic\s*ai)\b', value):
        return 'refuse'
    if value in FOLLOWUPS:
        return 'policy' if previous and route(previous) == 'policy' else 'refuse'
    if re.search(r'\b(loan|loans|lending|eligibility|eligible|credit|debt|dti|repayment|repay|income|salaried|self.employed|employment|late payments?|interest|apr|collateral|policy|policies|assessment|recommendation|approved|rejected|application|applicant|human review|officer|threshold|score)\b', value):
        return 'policy'
    return 'refuse'

def validate_public_text(text):
    # Also catches punctuation, spacing, full-width letters and zero-width insertions.
    compact = ''.join(c for c in canonical(text) if c.isalnum())
    if 'syntheticai' in compact:
        raise ValueError('Explanation failed the public response checks.')


def requests_internal_rules(text):
    value = canonical(text)
    return bool(re.search(r'cut.?off|threshold|formula|weight|coefficient|internal|exact|minimum|maximum|percent|percentage|\b[0-9]+\s*%|\bp0[1-9]\b|what.{0,30}(enter|change|increase|decrease).{0,50}(approv|qualif)|guarantee.{0,20}approv', value))
