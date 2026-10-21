import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from rubrics import bands

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS submissions (
                exam TEXT NOT NULL, student TEXT NOT NULL, name TEXT NOT NULL,
                answers TEXT NOT NULL, result TEXT NOT NULL, submitted TEXT NOT NULL,
                review TEXT, PRIMARY KEY(exam, student))''')

            db.execute('''CREATE TABLE IF NOT EXISTS question_attempts (
                student TEXT NOT NULL, question INTEGER NOT NULL, round INTEGER NOT NULL,
                payload TEXT NOT NULL, submitted TEXT NOT NULL,
                PRIMARY KEY(student, question, round), CHECK(round IN (1,2)),
                CHECK(question BETWEEN 1 AND 7))''')

    def attempts(self, student):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM question_attempts WHERE student=?', (student,)).fetchall()
        return {(r['question'], r['round']): json.loads(r['payload']) for r in rows}

    def submit_question(self, student, name, number, round_number, answers):
        from learning import grade_question
        from question_content import QUESTIONS
        from assessment import evaluate
        if not 1 <= number <= len(QUESTIONS) or round_number not in (1, 2):
            raise ValueError('잘못된 제출 단계입니다.')
        payload = grade_question(number, answers)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = {r['exam'] for r in db.execute('SELECT exam FROM submissions WHERE student=?', (student,))}
            needed = [n for n, (_, exam, _, _) in enumerate(QUESTIONS, 1)
                      if exam not in existing and (n != 1 or not existing)]
            attempts = {(r['question'], r['round']): json.loads(r['payload']) for r in
                        db.execute('SELECT * FROM question_attempts WHERE student=?', (student,))}
            next_number = next((n for n in needed if (n, 2) not in attempts), None)
            if number != next_number or (round_number == 2 and (number, 1) not in attempts):
                raise ValueError('현재 문제를 순서대로 제출해 주세요.')
            db.execute('INSERT INTO question_attempts VALUES (?,?,?,?,?)',
                       (student, number, round_number, json.dumps(payload, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
            attempts[number, round_number] = payload
            if all((n, 2) in attempts for n in needed):
                common = attempts.get((1, 2), {}).get('answers', {})
                if existing:
                    old = db.execute('SELECT answers FROM submissions WHERE student=? LIMIT 1', (student,)).fetchone()
                    common = {k: v for k, v in json.loads(old['answers']).items() if k in ('event', 'production')}
                for exam in ('industry', 'imperialism'):
                    if exam in existing:
                        continue
                    final = dict(common)
                    for n, (_, question_exam, _, _) in enumerate(QUESTIONS, 1):
                        if n != 1 and question_exam == exam:
                            final.update(attempts[n, 2]['answers'])
                    db.execute('INSERT INTO submissions(exam,student,name,answers,result,submitted) VALUES (?,?,?,?,?,?)',
                               (exam, student, name, json.dumps(final, ensure_ascii=False),
                                json.dumps(evaluate(exam, final), ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
        return payload

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def get(self, exam, student):
        with self.connect() as db:
            row = db.execute('SELECT * FROM submissions WHERE exam=? AND student=?', (exam, student)).fetchone()
            return dict(row) if row else None

    def submit(self, exam, student, name, answers, result):
        # Unique constraint is authoritative even across tabs and simultaneous requests.
        with self.connect() as db:
            db.execute('INSERT INTO submissions(exam,student,name,answers,result,submitted) VALUES (?,?,?,?,?,?)',
                       (exam, student, name, json.dumps(answers, ensure_ascii=False), json.dumps(result, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))

    def all(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM submissions ORDER BY submitted DESC')]

    def submit_many(self, student, name, submissions):
        """Save the unified screen in one transaction, preserving attempt limits."""
        from assessment import evaluate
        with self.connect() as db:
            for exam, answers in submissions.items():
                db.execute('INSERT INTO submissions(exam,student,name,answers,result,submitted) VALUES (?,?,?,?,?,?)',
                           (exam, student, name, json.dumps(answers, ensure_ascii=False),
                            json.dumps(evaluate(exam, answers), ensure_ascii=False), datetime.now(timezone.utc).isoformat()))

    def review(self, exam, student, review):
        for key, item in review.items():
            allowed = [0] if key == 'event' else bands(exam, key)
            if item.get('score') not in allowed:
                raise ValueError('루브릭에 없는 점수는 저장할 수 없습니다.')
        with self.connect() as db:
            db.execute('UPDATE submissions SET review=? WHERE exam=? AND student=?',
                       (json.dumps(review, ensure_ascii=False), exam, student))
