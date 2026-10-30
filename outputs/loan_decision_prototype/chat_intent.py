"""Route personal loan conversations separately from explicit policy questions.

Common intent routing is local, so starting eligibility never requires a provider.
This router collects details; it does not promise eligibility or price a loan.
"""
import re
import guardrails
import intake

RATE = re.compile(r'\b(interest|apr|rates?)\b',re.I)
POLICY = re.compile(
    r'\b(policy|policies|rules?|clauses?|criteria|requirements?|documents?|documentation|'
    r'cutoffs?|thresholds?|minimum|maximum|limits?|fees?|collateral|formula|illustrative|calculations?|dti)\b|'
    r'\b(how.{0,25}(?:calculat|debt.service|dti)|'
    r'(?:what|which).{0,35}(?:required|support|allowed)|'
    r'do you (?:support|accept)|(?:rate|interest).{0,30}(?:illustrative|assum|calculat))',re.I)
PERSONAL = re.compile(
    r'\b(?:i|we)\s+(?:want|need|would like|wish|am looking|are looking|would love)\b.{0,100}\b(?:loans?|borrow)\b|'
    r'\b(?:i|we)(?:\s+would|[’\x27]d)\s+like\b.{0,80}\b(?:loans?|borrow|apply)\b|'
    r'\b(?:can|could|may|would|will)\s+(?:i|we)\s+(?:get|take|borrow|apply|qualify|be eligible)\b|'
    r'\b(?:am i|are we)\s+eligible\b|\bdo (?:i|we) qualify\b|'
    r'\b(?:check|assess|calculate|find out|know)\b.{0,30}\b(?:my|our)\s+eligibility\b|'
    r'\b(?:my|our)\s+(?:loan\s+)?eligibility\b|'
    r'\bhow much\s+(?:can|could)\s+(?:i|we)\s+borrow\b|'
    r'\b(?:apply|applying|application)\s+for\s+(?:a\s+)?loan\b|'
    r'\bhelp (?:me|us)\b.{0,40}\b(?:loan|borrow|apply|eligibility)\b|'
    r'\bcheck\s+(?:loan\s+)?eligibility\b|'
    r'\b(?:if|whether)\s+i\s+(?:am\s+)?eligible\b|'
    r'\bi am interested\b.{0,40}\b(?:loan|borrow)\b',re.I)


def has_details(text):
    words=set(re.findall(r'[a-z]+',intake.clean(text)))
    return bool(re.search(r'\d',text) or words & (intake.NUMBER_WORDS-{'and','a','an','point'})
                or re.search(r'salar[i]+ed|self[ _-]?employed|freelanc|\bemployee\b',text,re.I))


def classify(text, active=False, previous=''):
    value=intake.clean(text).replace("i'm",'i am').replace("we're",'we are')
    if intake.BAD.search(value) or re.search(r'\b(e-mail|letter|translate|translation|rewrite|song|joke|weather|politics|provider|powered by)\b',value):
        return 'blocked'
    if re.search(r"\b(?:i|we)\s+(?:don'?t|do not|no longer)\s+(?:want|need)\b.{0,35}\bloan\b",value):
        return 'decline'
    # Specific requests for rules remain RAG, even inside an unfinished application.
    if POLICY.search(value):
        return 'policy'
    if value in guardrails.FOLLOWUPS and previous:
        return 'policy'
    if PERSONAL.search(value) or re.fullmatch(r'(?:please )?(?:loan )?eligibility[?.! ]*',value):
        return 'eligibility'
    # A general rate enquiry starts a discussion of the user's application. The
    # application cannot give a personalized rate; a confirmed offer needs review.
    if RATE.search(value):
        return 'eligibility'
    if re.fullmatch(r'(hi|hello|hey|thanks|thank you)[!.? ]*',value):
        return 'chat'
    if active:
        # A factual answer or correction stays in intake; a question about how a
        # lending concept works can be answered with policy without losing progress.
        if re.search(r'\b(my (?:income|salary|score)|i earn|i make|i pay|i have)\b',value) and has_details(value):
            return 'continue'
        if re.search(r'\b(what|why|how|does|do|can|is|are)\b',value) and ('?' in value or value.startswith(('what ','why ','how ','does ','do ','can ','is ','are '))):
            return 'policy'
        return 'continue'
    return 'chat'
