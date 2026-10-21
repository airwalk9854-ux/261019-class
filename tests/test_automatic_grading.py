import copy
import unittest

from assessment import EXAMS, evaluate
from learning import grade_question, comparison, refresh_attempts
from rubrics import bands, score_answer
from spelling import check_spelling


class AutomaticGradingTests(unittest.TestCase):
    def test_scores_are_always_in_rubric_including_negations_and_partial_answers(self):
        samples = ['', '모르겠습니다', '면직물 생산량이 증가했다.',
                   '산업혁명 때 수공업에서 공장제로 변했지만 생산량이 감소했다.',
                   '우리 프랑스는 횡단정책과 파쇼다 사건을 설명한다.',
                   '횡단정책과 파쇼다 사건', '박람회의 산업 발전과 식민지 착취',
                   '영국의 횡단정책 때문에 우리는 분노한다.',
                   '아동 노동 착취가 없었다.', '철도가 발전하지 않았다.']
        for exam, definition in EXAMS.items():
            for key, *_ in definition['questions']:
                for text in samples:
                    with self.subTest(exam=exam, key=key, text=text):
                        item = evaluate(exam, {key: text})[key]
                        self.assertNotIn('대기', item['status'])
                        if key != 'event':
                            self.assertIn(item['score'], bands(exam, key))
                            self.assertFalse(item['needs_review'])
                            self.assertTrue(item['decision_reason'])

    def test_typo_corrections_preserve_answers_and_do_not_penalize_content(self):
        answers = {'event': '산업혁멍', 'production': '가내수공엽에서 공장재 기계공엽으로 변하여 면직믈 생산랑이 증가햇다.'}
        original = copy.deepcopy(answers)
        result = evaluate('industry', answers)
        self.assertEqual(result['event']['status'], '정답')
        self.assertEqual(result['production']['score'], 4)
        self.assertTrue(result['event']['spelling'])
        self.assertEqual(len(result['production']['spelling']), 6)
        self.assertEqual(answers, original)
        attempt = grade_question(1, answers)
        self.assertEqual(attempt['answers'], original)
        self.assertEqual(attempt['result']['production']['score'], 4)

    def test_wrong_policy_is_factual_error_not_spelling(self):
        answer = '영국의 횡단정책으로 우리는 침략에 분노한다.'
        corrected, notices = check_spelling(answer)
        self.assertEqual(corrected, answer)
        self.assertEqual(notices, [])
        self.assertEqual(score_answer('imperialism', 'africa', {'africa': answer})['score'], 4)
        typo = '영국의 종단정첵으로 우리는 침략에 분노한다.'
        self.assertEqual(score_answer('imperialism', 'africa', {'africa': typo})['score'], 6)

    def test_negations_and_reversed_transition_cannot_receive_full_credit(self):
        cases = [
            ('industry', 'production', 2, '산업혁명 때 수공업에서 공장제로 바뀌었지만 면직물 생산량이 증가하지 않았다.'),
            ('industry', 'production', 1, '산업혁명 때 공장제에서 가내수공업으로 바뀌고 면직물 생산량이 증가했다.'),
            ('industry', 'negative', 1, '아동 노동 착취는 없었다.'),
            ('imperialism', 'rhodes', 4, '실업과 시장 문제로 식민지를 확보하지 않았다.'),
            ('imperialism', 'france', 3, '우리 프랑스의 횡단정책은 파쇼다 사건과 관련이 없었다.'),
        ]
        for exam, key, expected, text in cases:
            with self.subTest(key=key, text=text):
                self.assertEqual(score_answer(exam, key, {key: text})['score'], expected)

    def test_negating_one_fact_preserves_other_affirmed_facts(self):
        text = '아동 노동은 없었지만 환경오염으로 위생이 열악한 도시에서 콜레라가 유행했다.'
        self.assertEqual(score_answer('industry', 'negative', {'negative': text})['score'], 4)
        text = '산업혁명 때 수공업에서 공장제로 바뀌었고 면직물 생산량은 감소하지 않고 증가했다.'
        self.assertEqual(score_answer('industry', 'production', {'production': text})['score'], 4)

    def test_legacy_pending_attempts_are_rescored_without_mutating_history(self):
        attempt = grade_question(1, {'event': '산업혁명', 'production': '면직물 생산량이 증가하지 않았다.'})
        attempt['result']['production']['score'] = None
        attempt['result']['production'].pop('decision_reason')
        old = copy.deepcopy(attempt)
        attempts = {(1, 1): attempt, (1, 2): copy.deepcopy(attempt)}
        refreshed = refresh_attempts(attempts)
        self.assertEqual(refreshed[1, 1]['result']['production']['score'], 1)
        self.assertEqual(comparison(attempts)[0]['변화'], 0)
        self.assertEqual(attempt, old)
