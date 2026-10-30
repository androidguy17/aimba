"""Readable assessment copy preserves outcomes without exposing service errors."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chatbot
from loan_core import assess, load_model, DEMO_CASES
from policy import Policy

class AssessmentCopyTests(unittest.TestCase):
    def test_offline_results_keep_outcome_and_review_requirement(self):
        expected = {'approval': 'recommends approval, subject to review',
                    'rejection': 'does not recommend approval',
                    'edge': 'needs a specialist review'}
        for name, title in expected.items():
            assessment = assess(load_model(), DEMO_CASES[name], Policy())
            for status in ('not_configured', 'validation_failed', 'provider_error'):
                with self.subTest(name=name, status=status):
                    message = chatbot.assessment_message(assessment, {
                        'status': status, 'message': 'Internal provider error with model details'})
                    self.assertIn(title, message)
                    self.assertIn('not a final loan decision', message)
                    self.assertIn('Start over', message)
                    for technical in ('provider', 'repayment score', 'Policy flags', '[P04]', 'threshold'):
                        self.assertNotIn(technical, message)
        self.assertIn('estimated payment', chatbot.assessment_message(
            assess(load_model(), DEMO_CASES['rejection'], Policy()), {'status': 'not_configured'}))

    def test_generated_summary_is_not_duplicated_with_internal_reasons(self):
        assessment = assess(load_model(), DEMO_CASES['rejection'], Policy())
        summary = 'Your existing payments would leave too little room for this loan.'
        message = chatbot.assessment_message(assessment, {'status': 'generated', 'draft': {
            'summary': summary, 'reasons': [{'explanation': 'Internal technical evidence'}]}})
        self.assertEqual(message.count(summary), 1)
        self.assertNotIn('Internal technical evidence', message)
        self.assertIn('does not recommend approval', message)
        self.assertIn('loan officer must review', message)

if __name__ == '__main__':
    unittest.main()
