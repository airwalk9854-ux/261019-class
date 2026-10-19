import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS submissions (
                exam TEXT NOT NULL, student TEXT NOT NULL, name TEXT NOT NULL,
                answers TEXT NOT NULL, result TEXT NOT NULL, submitted TEXT NOT NULL,
                review TEXT, PRIMARY KEY(exam, student))''')

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

    def review(self, exam, student, review):
        with self.connect() as db:
            db.execute('UPDATE submissions SET review=? WHERE exam=? AND student=?',
                       (json.dumps(review, ensure_ascii=False), exam, student))
