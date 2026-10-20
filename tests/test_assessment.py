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
        # Empty submission is refused, then all answers are supplied.
        button(app, '최종 제출하고 피드백 보기').click().run()
        self.assertTrue(app.error)
        app.text_input[0].set_value('산업혁명')
        for text in app.text_area:
            text.set_value('공장과 기계의 발전, 면직물 생산 증가에 관한 자료 근거입니다.')
        app.run()
        for number in range(2, 8):
            app.sidebar.radio[0].set_value(number).run()
            app.text_area[0].set_value('공장과 기계의 발전, 면직물 생산 증가에 관한 자료 근거입니다.').run()
        app.checkbox[0].check()
        button(app, '최종 제출하고 피드백 보기').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.success)
        self.assertEqual(len(Store(self.path).all()), 2)
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

    def test_navigation_preserves_answers_and_demo_does_not_persist(self):
        app = self.app()
        button(app, '체험 시작').click().run()
        self.assertFalse(app.selectbox)  # All questions share one continuous menu.
        self.assertEqual(len(app.sidebar.radio[0].options), 7)
        app.text_input[0].set_value('산업혁명')
        app.text_area[0].set_value('기계와 공장으로 생산 방식이 변하고 면직물 생산량이 증가했다.').run()
        for number in range(2, 8):
            app.sidebar.radio[0].set_value(number).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.text_area), 1)
            app.text_area[0].set_value(f'{number}번 자료를 바탕으로 작성한 체험 답안입니다.').run()
        button(app, '← 이전 문제').click().run()
        self.assertEqual(app.text_area[0].value, '6번 자료를 바탕으로 작성한 체험 답안입니다.')
        app.sidebar.radio[0].set_value(1).run()
        self.assertEqual(app.text_input[0].value, '산업혁명')
        self.assertIn('면직물', app.text_area[0].value)
        app.checkbox[0].check()
        button(app, '최종 제출하고 피드백 보기').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.success)
        self.assertEqual(Store(self.path).all(), [])
        industry = json.loads(app.session_state['demo-industry']['answers'])
        imperialism = json.loads(app.session_state['demo-imperialism']['answers'])
        self.assertEqual(industry['production'], imperialism['production'])
        self.assertEqual(industry['event'], imperialism['event'])
        button(app, '체험 다시 시작').click().run()
        self.assertEqual(app.text_input[0].value, '')
        self.assertEqual(app.text_area[0].value, '')

    def test_unified_submission_rolls_back_on_duplicate(self):
        store = Store(self.path)
        store.submit('imperialism', 's1', '학생', {}, {})
        with self.assertRaises(sqlite3.IntegrityError):
            store.submit_many('s1', '학생', {'industry': {}, 'imperialism': {}})
        self.assertIsNone(store.get('industry', 's1'))


if __name__ == '__main__':
    unittest.main()
