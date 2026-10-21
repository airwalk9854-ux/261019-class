import os
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from auth import hash_password, verify_password
from assessment import evaluate
from feedback_content import SOURCE_FILE, SOURCE_VERSION
from storage import Store
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]

def button(app, label):
    return next(b for b in app.button if b.label == label)

class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'assessment.db'
        self.old_path = os.environ.get('ASSESSMENT_DB_PATH')
        os.environ['ASSESSMENT_DB_PATH'] = str(self.path)

    def tearDown(self):
        if self.old_path is None:
            os.environ.pop('ASSESSMENT_DB_PATH', None)
        else:
            os.environ['ASSESSMENT_DB_PATH'] = self.old_path
        self.temp.cleanup()

    def app(self):
        app = AppTest.from_file(str(ROOT / 'streamlit_app.py'), default_timeout=30)
        app.secrets['students'] = {'s1': {'name': '검증학생', 'password_hash': hash_password('student-password')}}
        app.secrets['teacher'] = {'password_hash': hash_password('teacher-password')}
        app.run()
        self.assertFalse(app.exception)
        return app

    def test_password_and_negation(self):
        hashed = hash_password('secret')
        self.assertTrue(verify_password('secret', hashed))
        self.assertFalse(verify_password('wrong', hashed))
        self.assertFalse(verify_password('secret', 'invalid'))
        self.assertEqual(evaluate('industry', {'event': '산업 혁명'})['event']['status'], '정답')
        self.assertNotEqual(evaluate('industry', {'event': '산업혁명이 아니다'})['event']['status'], '정답')
        self.assertIn('문맥 확인', evaluate('industry', {'production': '기계 공장 면직물 생산량이 증가하지 않았다'})['production']['status'])

    def test_simultaneous_submissions(self):
        store = Store(self.path)
        def submit(_):
            try:
                store.submit('industry', 's1', '학생', {}, {})
                return True
            except sqlite3.IntegrityError:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(submit, range(4))), 1)
        self.assertIsNone(store.get('industry', 's2'))

    def test_feedback_source_and_answer_specific_guidance(self):
        for exam in ['industry', 'imperialism']:
            result = evaluate(exam, {})
            for item in result.values():
                self.assertEqual(item['source']['file'], SOURCE_FILE)
                self.assertEqual(item['source']['version'], SOURCE_VERSION)
                self.assertTrue(all(1 <= p <= 5 for p in item['source']['pages']))
                self.assertNotIn('공장법', item['feedback'])
                self.assertNotIn('모범 답안:', item['feedback'])
            self.assertNotIn('산업혁명', result['event']['feedback'])
        rail = evaluate('industry', {'positive': '철도가 발달했다'})['positive']
        self.assertIn('시간표', rail['feedback'])
        self.assertNotIn('박람회', rail['feedback'])
        self.assertIn('보완할 부분', rail['feedback'])
        exhibition = evaluate('industry', {'positive': '박람회에서 기술을 전시했다'})['positive']
        self.assertNotIn('보완할 부분', exhibition['feedback'])
        self.assertNotIn('철도', exhibition['feedback'])
        labour = evaluate('industry', {'negative': '아동 노동 시간이 길었다'})['negative']
        self.assertNotIn('콜레라', labour['feedback'])
        france = evaluate('imperialism', {})['france']
        self.assertNotIn('파쇼다', france['feedback'])
        self.assertNotIn('횡단', france['feedback'])
        self.assertIn('사건명', france['feedback'])
        self.assertEqual(france['source']['pages'], [4, 5])

    def test_previous_submission_gets_new_guidance_without_rewriting_record(self):
        store = Store(self.path)
        store.submit('industry', 's1', '검증학생', {'event': '산업혁명'}, {'event': {'feedback': '이전 피드백'}})
        store.review('industry', 's1', {'event': {'status': '정답', 'score': 0, 'feedback': '교사 확인'}})
        before = store.get('industry', 's1')
        app = self.app()
        app.text_input[0].set_value('s1')
        app.text_input[1].set_value('student-password')
        button(app, '로그인').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('피드백 내용.pdf' in c.value for c in app.caption))
        self.assertFalse(any('이전 피드백' in i.value for i in app.info))
        self.assertTrue(any('교사 확인' in i.value for i in app.info))
        self.assertEqual(before, store.get('industry', 's1'))

    def test_results_render_with_missing_or_partial_source_metadata(self):
        store = Store(self.path)
        store.submit('industry', 's1', '검증학생', {'event': '산업혁명'}, {})
        before = store.get('industry', 's1')
        app = self.app()
        app.session_state['identity'] = {'id': 's1', 'name': '검증학생', 'role': '학생'}
        def legacy_evaluate(exam, answers):
            result = evaluate(exam, answers)
            for item in result.values():
                item.pop('source', None)
                item.pop('rubric_source', None)
            result['production']['source'] = None
            result['positive']['source'] = {'pages': None}
            result['negative']['source'] = {'file': '', 'pages': []}
            return result
        with patch('assessment.evaluate', side_effect=legacy_evaluate):
            app.run()
        self.assertFalse(app.exception)
        captions = [item.value for item in app.caption]
        self.assertEqual(sum('피드백 근거: 피드백 내용.pdf' in value for value in captions), 5)
        self.assertEqual(sum('채점 근거: 논술형 문항1 답안.pdf' in value for value in captions), 4)
        self.assertGreaterEqual(len(app.info), 5)
        self.assertEqual(before, store.get('industry', 's1'))

    def test_student_submit_teacher_review_and_relogin(self):
        app = self.app()
        app.text_input[0].set_value('s1')
        app.text_input[1].set_value('student-password')
        button(app, '로그인').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('image')), 2)
        # Each question must be graded twice before the next opens.
        button(app, '이 문제 제출하고 피드백 보기').click().run()
        self.assertTrue(app.error)
        for number in range(1, 8):
            if number == 1:
                app.text_input[0].set_value('산업혁명')
            for text in app.text_area:
                text.set_value('공장과 기계의 발전, 면직물 생산 증가에 관한 자료 근거입니다.')
            button(app, '이 문제 제출하고 피드백 보기').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any('1차 채점' in item.value for item in app.subheader))
            app.text_area[0].set_value('공장제 기계공업으로 면직물 생산량이 증가했다.')
            button(app, '수정 답안 제출하고 2차 채점').click().run()
            self.assertFalse(app.exception)
            if number < 7:
                button(app, '다음 문제 →').click().run()
        self.assertTrue(app.success)
        self.assertEqual(len(Store(self.path).all()), 2)
        self.assertEqual(len(Store(self.path).attempts('s1')), 14)
        self.assertTrue(any(m.label == '최종 학습 점수 · 2차' for m in app.metric))
        button(app, '로그아웃').click().run()
        app.radio[0].set_value('교사')
        app.text_input[1].set_value('teacher-password')
        button(app, '로그인').click().run()
        self.assertFalse(app.exception)
        submission = next(s for s in app.selectbox if s.label == '검토할 제출')
        submission.select(next(i for i, row in enumerate(Store(self.path).all()) if row['exam'] == 'industry')).run()
        scores = [s for s in app.selectbox if s.key and s.key.startswith('score-')]
        self.assertEqual(len(scores), 4)
        for select in scores:
            if select.value is None:
                select.select(1)
        button(app, '교사 판정 저장').click().run()
        self.assertFalse(app.exception)
        self.assertIsNotNone(Store(self.path).get('industry', 's1')['review'])
        button(app, '로그아웃').click().run()
        app.radio[0].set_value('학생')
        app.text_input[0].set_value('s1')
        app.text_input[1].set_value('student-password')
        button(app, '로그인').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.text_area)
        self.assertTrue(any('교사 확정 점수' in m.label for m in app.metric))

    def test_sequential_demo_revision_and_reset(self):
        app = self.app()
        button(app, '체험 시작').click().run()
        self.assertEqual(len(app.sidebar.radio[0].options), 1)
        for number in range(1, 8):
            if number == 1:
                app.text_input[0].set_value('산업혁명')
            original = f'{number}번 자료를 바탕으로 작성한 체험 답안입니다.'
            app.text_area[0].set_value(original)
            button(app, '이 문제 제출하고 피드백 보기').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_area[0].value, original)
            revised = '공장제 기계공업으로 면직물 생산량이 증가했다.'
            app.text_area[0].set_value(revised)
            button(app, '수정 답안 제출하고 2차 채점').click().run()
            self.assertFalse(app.exception)
            if number < 7:
                button(app, '다음 문제 →').click().run()
        self.assertTrue(app.success)
        self.assertEqual(Store(self.path).all(), [])
        attempts = app.session_state['demo-attempts']
        self.assertEqual(attempts[1, 1]['answers']['production'], '1번 자료를 바탕으로 작성한 체험 답안입니다.')
        self.assertEqual(attempts[1, 2]['answers']['production'], revised)
        industry = json.loads(app.session_state['demo-industry']['answers'])
        imperialism = json.loads(app.session_state['demo-imperialism']['answers'])
        self.assertEqual(industry['production'], imperialism['production'])
        self.assertEqual(industry['event'], imperialism['event'])
        self.assertTrue(any('vega' in str(e.type) for e in app))
        button(app, '체험 다시 시작').click().run()
        self.assertEqual(app.text_input[0].value, '')
        self.assertEqual(app.text_area[0].value, '')

    def test_question_attempts_resume_and_enforce_round_order(self):
        store = Store(self.path)
        answer = {'event': '산업혁명', 'production': '공장제 기계공업으로 면직물 생산량 증가'}
        with self.assertRaises(ValueError):
            store.submit_question('s1', '학생', 1, 2, answer)
        with self.assertRaises(ValueError):
            store.submit_question('s1', '학생', 2, 1, {'positive': '철도'})
        store.submit_question('s1', '학생', 1, 1, answer)
        resumed = Store(self.path)
        before = resumed.attempts('s1')[1, 1]
        self.assertEqual(before['answers'], answer)
        self.assertEqual(resumed.attempts('s2'), {})
        with self.assertRaises(sqlite3.IntegrityError):
            resumed.submit_question('s1', '학생', 1, 1, answer)
        resumed.submit_question('s1', '학생', 1, 2, {**answer, 'production': '기계로 훨씬 많이 생산'})
        self.assertEqual(resumed.attempts('s1')[1, 1], before)
        app = self.app()
        app.session_state['identity'] = {'id': 's1', 'name': '학생', 'role': '학생'}
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('2번.' in h.value for h in app.header))

    def test_comparison_does_not_replace_pending_scores_with_zero(self):
        from learning import grade_question, comparison
        first = grade_question(1, {'event': '산업혁명', 'production': '모르겠습니다'})
        second = grade_question(1, {'event': '산업혁명', 'production': '기계와 공장으로 면직물 생산량이 증가하지 않았다'})
        records = comparison({(1, 1): first, (1, 2): second})
        self.assertIsNone(records[0]['2차 점수'])
        self.assertIsNone(records[0]['변화'])

    def test_complete_score_comparison_counts_common_question_once(self):
        from learning import grade_question, comparison
        from question_content import QUESTIONS
        best = [
            {'event': '산업혁명', 'production': '가내 수공업에서 공장제 기계공업으로 변하여 면직물 생산량이 증가하였다.'},
            {'positive': '철도로 생활 범위와 여가 활동이 확대되고 시간표를 통해 시간 개념이 생겼다.'},
            {'negative': '인터뷰에 따르면 아동에 대한 노동 착취가 심각하였다.'},
            {'critique': '박람회는 산업과 국력의 발전을 보여주지만 식민지 전시장은 식민지 주민의 착취를 보여 준다.'},
            {'rhodes': '실업 문제 해결과 시장 확보를 위해 제국주의를 추진했고 많은 식민지를 확보하였다.'},
            {'france': '우리 프랑스의 횡단정책이 영국과 파쇼다 사건에서 충돌하여 위협을 느꼈다.'},
            {'africa': '영국의 종단정책으로 우리 땅을 빼앗겨 침략에 분노한다.'},
        ]
        store = Store(self.path)
        for number, (_, _, keys, _) in enumerate(QUESTIONS, 1):
            store.submit_question('s1', '학생', number, 1, {key: '모르겠습니다' for key in keys})
            store.submit_question('s1', '학생', number, 2, best[number - 1])
        records = comparison(store.attempts('s1'))
        self.assertEqual(sum(r['1차 점수'] for r in records), 7)
        self.assertEqual(sum(r['2차 점수'] for r in records), 36)
        self.assertEqual(sum(r['변화'] for r in records), 29)
        self.assertEqual(sum(r['만점'] for r in records), 36)
        self.assertEqual(len(store.all()), 2)
        reversed_records = comparison({(n, 3 - r): a for (n, r), a in store.attempts('s1').items()})
        self.assertEqual(sum(r['변화'] for r in reversed_records), -29)

    def test_legacy_submission_is_preserved_when_remaining_exam_completed(self):
        store = Store(self.path)
        common = {'event': '산업혁명', 'production': '가내 수공업에서 공장제 기계공업으로 면직물 생산량 증가'}
        store.submit('industry', 's1', '학생', common, evaluate('industry', common))
        before = store.get('industry', 's1')
        for number, key in [(5, 'rhodes'), (6, 'france'), (7, 'africa')]:
            for round_number in (1, 2):
                store.submit_question('s1', '학생', number, round_number, {key: '모르겠습니다'})
        self.assertEqual(store.get('industry', 's1'), before)
        final = json.loads(store.get('imperialism', 's1')['answers'])
        self.assertEqual(final['production'], common['production'])

    def test_unified_submission_rolls_back_on_duplicate(self):
        store = Store(self.path)
        store.submit('imperialism', 's1', '학생', {}, {})
        with self.assertRaises(sqlite3.IntegrityError):
            store.submit_many('s1', '학생', {'industry': {}, 'imperialism': {}})
        self.assertIsNone(store.get('industry', 's1'))


if __name__ == '__main__':
    unittest.main()
