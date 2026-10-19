import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from auth import hash_password, verify_password
from assessment import evaluate
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

    def test_student_submit_teacher_review_and_relogin(self):
        app = self.app()
        app.text_input[0].set_value('s1')
        app.text_input[1].set_value('student-password')
        button(app, '로그인').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('image')), 1)
        # Empty submission is refused, then all answers are supplied.
        button(app, '최종 제출하고 피드백 보기').click().run()
        self.assertTrue(app.error)
        app.text_input[0].set_value('산업혁명')
        for text in app.text_area:
            text.set_value('공장과 기계의 발전, 면직물 생산 증가에 관한 자료 근거입니다.')
        app.checkbox[0].check()
        button(app, '최종 제출하고 피드백 보기').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.success)
        self.assertEqual(len(Store(self.path).all()), 1)
        button(app, '로그아웃').click().run()
        app.radio[0].set_value('교사')
        app.text_input[1].set_value('teacher-password')
        button(app, '로그인').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.number_input), 4)
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

    def test_demo_second_exam_does_not_persist(self):
        app = self.app()
        button(app, '체험 시작').click().run()
        app.selectbox[0].select('imperialism').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('image')), 2)
        app.text_input[0].set_value('산업혁명')
        for text in app.text_area:
            text.set_value('당시 자료를 바탕으로 작성한 체험 답안입니다.')
        app.checkbox[0].check()
        button(app, '최종 제출하고 피드백 보기').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.success)
        self.assertEqual(Store(self.path).all(), [])
        button(app, '체험 다시 시작').click().run()
        self.assertEqual(len(app.text_area), 4)

if __name__ == '__main__':
    unittest.main()
