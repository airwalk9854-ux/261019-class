import unittest
from assessment import evaluate
from rubrics import score_answer


class ParaphraseTests(unittest.TestCase):
    def test_short_answer_sentences_and_punctuation(self):
        for text in ['산업 혁명입니다.', '영국에서 일어난 산업혁명이다.', '산업혁명!', 'Industrial Revolution.', '18세기 후반 영국의 산업혁명']:
            with self.subTest(text=text):
                self.assertEqual(evaluate('industry', {'event': text})['event']['status'], '정답')
        for text in ['산업혁명이 아니다.', '프랑스혁명이다.', '산업혁명이나 프랑스혁명 중 하나']:
            with self.subTest(text=text):
                self.assertNotEqual(evaluate('industry', {'event': text})['event']['status'], '정답')

    def test_paraphrases_use_same_rubric_and_feedback_checks(self):
        cases = [
            ('industry', 'production', 4, '산업혁명 때 집에서 손으로 짜던 옷감을 공장에서 기계로 만들게 되었고 훨씬 많이 생산했다.'),
            ('industry', 'positive', 4, '기찻길이 놓여 먼 곳까지 갈 수 있었고 관광을 즐겼다. 출발 시각이 정해져 생활도 규칙적으로 바뀌었다.'),
            ('industry', 'positive', 4, '만국 박람회에서 기계들을 전시해 발전한 나라의 힘을 과시하였다.'),
            ('industry', 'negative', 4, '신문의 증언에서 아이들이 하루 열다섯 시간씩 일했다고 한다.'),
            ('industry', 'negative', 4, '도시 빈민촌의 위생이 불결하고 물이 오염되어 감염병이 퍼졌다.'),
            ('industry', 'critique', 8, '박람회에서 산업의 성장을 자랑했지만 식민지관은 식민지 주민의 자원을 약탈한 현실을 드러낸다.'),
            ('imperialism', 'rhodes', 6, '일자리를 잃은 사람들의 불만과 물건을 팔 곳이 필요해 제국주의를 추진했다. 여러 지역을 식민지로 삼았다.'),
            ('imperialism', 'france', 4, '저희 프랑스는 아프리카 횡단을 추진했고 파쇼다에서 영국과 맞섰다.'),
            ('imperialism', 'africa', 6, '저희는 영국의 아프리카 종단 구상 때문에 토지를 빼앗겼고 억지로 일해야 해 억울하다.'),
        ]
        for exam, key, expected, text in cases:
            with self.subTest(key=key, text=text):
                scored = score_answer(exam, key, {key: text})
                self.assertEqual(scored['score'], expected)
                item = evaluate(exam, {key: text})[key]
                self.assertEqual(item['score'], expected)
                self.assertNotIn('보완할 부분:', item['feedback'])

    def test_criticism_negation_is_distinct_from_negated_fact(self):
        criticism = '박람회는 산업 발전을 과시했지만 식민지 전시장은 식민지 주민의 착취를 보여주므로 정당화할 수 없다.'
        self.assertEqual(score_answer('industry', 'critique', {'critique': criticism})['score'], 8)
        negative_fact = '인터뷰에서 아동 노동 착취는 없었다고 했다.'
        self.assertEqual(score_answer('industry', 'negative', {'negative': negative_fact})['score'], 1)
        wrong_growth = '산업혁명으로 수공업에서 공장제 생산으로 바뀌었지만 면직물 생산량이 늘지 않았다.'
        self.assertEqual(score_answer('industry', 'production', {'production': wrong_growth})['score'], 2)
        wrong_attribution = '우리 프랑스의 종단정책과 파쇼다 사건은 연결된다.'
        self.assertEqual(score_answer('imperialism', 'france', {'france': wrong_attribution})['score'], 3)
