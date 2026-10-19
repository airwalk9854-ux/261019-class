from pathlib import Path
import csv
import io
import json
import os
import sqlite3
import time
import unicodedata

import pymupdf
import streamlit as st

from assessment import EXAMS, evaluate
from auth import verify_password
from storage import Store

ROOT = Path(__file__).parent
st.set_page_config(page_title='역사의 시선 | 서논술형 평가', page_icon='📜', layout='wide')
st.markdown('''<style>
.stApp {background:#f6f5f0;color:#233b36} .block-container {max-width:1120px;padding-top:2.5rem}
h1,h2,h3 {color:#254f46} [data-testid="stSidebar"] {background:#e8eee8}
div.stButton>button[kind="primary"],div.stFormSubmitButton>button {background:#2e6354;color:white;border:0;border-radius:10px}
[data-testid="stMetric"] {background:white;padding:18px;border-radius:14px}
</style>''', unsafe_allow_html=True)

try:
    config = st.secrets.to_dict()
except FileNotFoundError:
    config = {}
accounts = config.get('students', {})
teacher_hash = config.get('teacher', {}).get('password_hash', '')

@st.cache_resource
def get_store(path):
    return Store(path)

store = get_store(os.environ.get('ASSESSMENT_DB_PATH', str(ROOT / 'runtime' / 'assessment.sqlite3')))

@st.cache_data
def pdf_pages(number):
    files = [p for p in (ROOT / 'data').glob('*.pdf')
             if unicodedata.normalize('NFC', p.name) == f'논술형 문항{number}.pdf']
    if not files:
        return []
    with pymupdf.open(files[0]) as doc:
        return [page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes('png') for page in doc]

def show_results(exam_id, row, preview=False):
    st.success('체험이 끝났습니다. 실제 응시 기록에는 저장되지 않았습니다.' if preview else '제출이 완료되었습니다. 이 평가에는 다시 응시할 수 없습니다.')
    st.caption('단답형은 정오를 판정합니다. 서술·논술형은 규칙 기반 예비 피드백이며, 선생님 검토 후 최종 정오와 점수가 표시됩니다. 모범 답안은 제공하지 않습니다.')
    answers, results = json.loads(row['answers']), json.loads(row['result'])
    review = json.loads(row['review']) if row.get('review') else {}
    if review:
        st.metric('교사 확정 점수', f"{sum(v['score'] for v in review.values())} / 20")
    for key, number, kind, points, prompt in EXAMS[exam_id]['questions']:
        with st.container(border=True):
            st.markdown(f'#### {number} · {kind}')
            st.write(prompt)
            st.text(answers.get(key, ''))
            if key in review:
                item = review[key]
                st.markdown(f"**교사 판정: {item['status']}** · {item['score']}점")
                if item.get('feedback'):
                    st.info(item['feedback'])
            else:
                st.markdown(f"**{results[key]['status']}**")
            st.info(results[key]['feedback'])

st.caption('HISTORY CLASSROOM / 생각을 쓰고, 역사로 돌아보다')
st.title('역사의 시선')
st.write('산업혁명과 제국주의 · 자료를 읽고 나의 언어로 설명하는 역사 평가')

with st.sidebar:
    st.markdown('### 📜 역사 탐구실')
    st.caption('서논술형 평가 & 피드백')
    if st.session_state.get('identity'):
        st.write(st.session_state['identity']['name'])
        if st.button('로그아웃', width='stretch'):
            st.session_state.clear()
            st.rerun()
    st.divider()
    st.markdown('**응시 안내**\n\n① 자료를 살펴보세요.\n\n② 모든 답안을 작성하세요.\n\n③ 최종 제출 후 피드백을 확인하세요.')
    st.caption('평가별 학생 계정당 1회 제출 · 총 20점')

if not st.session_state.get('identity'):
    login, demo = st.tabs(['학생·교사 로그인', '미리 체험하기'])
    with login:
        if not accounts or not teacher_hash:
            st.info('수업 운영 전 학생 계정과 교사 비밀번호 설정이 필요합니다. 체험 탭에서 앱을 먼저 살펴볼 수 있습니다.')
        with st.form('login'):
            role = st.radio('로그인 유형', ['학생', '교사'], horizontal=True)
            student_id = st.text_input('학생 아이디 (교사는 비워 두세요)', max_chars=60)
            password = st.text_input('비밀번호', type='password')
            submitted = st.form_submit_button('로그인', type='primary')
        if submitted:
            if time.time() < st.session_state.get('retry_at', 0):
                st.error('잠시 후 다시 시도해 주세요.')
            else:
                account = accounts.get(student_id.strip(), {}) if role == '학생' else {'password_hash': teacher_hash, 'name': '선생님'}
                if verify_password(password, account.get('password_hash', '')):
                    st.session_state['identity'] = {'id': student_id.strip() if role == '학생' else '__teacher__', 'name': account.get('name', student_id), 'role': role}
                    st.rerun()
                st.session_state['retry_at'] = time.time() + 3
                st.error('아이디 또는 비밀번호를 확인해 주세요.')
    with demo:
        st.write('로그인 없이 문제와 피드백을 확인할 수 있습니다. 체험 답안은 제출 기록에 저장되지 않습니다.')
        if st.button('체험 시작', type='primary'):
            st.session_state['identity'] = {'id': '__demo__', 'name': '체험 학생', 'role': '체험'}
            st.rerun()
    st.stop()

identity = st.session_state['identity']
if identity['role'] == '교사':
    st.header('교사 검토실')
    st.warning('문항2 채점기준 마지막 항목의 영국 “횡단정책” 표기는 검토가 필요합니다. 영국의 종단정책을 기준으로 예비 피드백을 구성했습니다. 원본 문항2의 세부 문항 번호 3-1~3-3을 유지했습니다.')
    st.caption('부정 표현, 사실 오류, 자료 해석과 논증을 직접 확인하세요. 1-①은 명칭 확인용이며, 1-②와 합산하여 4점입니다.')
    rows = store.all()
    cols = st.columns(3)
    cols[0].metric('전체 제출', len(rows))
    cols[1].metric('검토 대기', sum(not r['review'] for r in rows))
    cols[2].metric('검토 완료', sum(bool(r['review']) for r in rows))
    if not rows:
        st.info('아직 제출한 학생이 없습니다.')
        st.stop()
    export = io.StringIO()
    writer = csv.writer(export)
    writer.writerow(['평가', '학생 아이디', '이름', '제출 시각(UTC)', '답안', '예비 피드백', '교사 판정'])
    for row in rows:
        writer.writerow(["'" + str(row[k]) if str(row[k]).startswith(('=', '+', '-', '@')) else row[k] for k in ['exam', 'student', 'name', 'submitted', 'answers', 'result', 'review']])
    st.download_button('제출 기록 CSV 내려받기', export.getvalue().encode('utf-8-sig'), '평가기록.csv', 'text/csv')
    selected = st.selectbox('검토할 제출', range(len(rows)), format_func=lambda i: f"{rows[i]['name']} ({rows[i]['student']}) · {EXAMS[rows[i]['exam']]['title']} · {'검토 완료' if rows[i]['review'] else '검토 대기'}")
    row = rows[selected]
    answers = json.loads(row['answers'])
    old = json.loads(row['review']) if row['review'] else {}
    with st.form(f"review-{row['exam']}-{row['student']}"):
        review = {}
        for key, number, kind, points, prompt in EXAMS[row['exam']]['questions']:
            st.subheader(f'{number} · {kind}')
            st.write(prompt)
            st.text(answers[key])
            statuses = ['정답', '부분 정답', '오답']
            previous = old.get(key, {})
            status = st.selectbox('최종 판정', statuses, index=statuses.index(previous.get('status', '부분 정답')), key=f'status-{key}-{selected}')
            score = st.number_input('점수 (1-①은 0점, 1-②에 합산)', 0, points, int(previous.get('score', 0)), key=f'score-{key}-{selected}') if points else 0
            feedback = st.text_area('추가 피드백 · 모범 답안 대신 역사적 사실과 보완 방향을 안내하세요.', value=previous.get('feedback', ''), key=f'feedback-{key}-{selected}')
            review[key] = {'status': status, 'score': score, 'feedback': feedback}
        if st.form_submit_button('교사 판정 저장', type='primary'):
            store.review(row['exam'], row['student'], review)
            st.success('저장했습니다. 학생이 결과 화면에서 확인할 수 있습니다.')
    st.stop()

exam_id = st.selectbox('평가 선택', list(EXAMS), format_func=lambda key: EXAMS[key]['title'])
exam = EXAMS[exam_id]
preview = identity['role'] == '체험'
if preview:
    st.info('체험 모드 · 실제 응시 횟수에 반영되지 않습니다.')
row = st.session_state.get(f'demo-{exam_id}') if preview else store.get(exam_id, identity['id'])
if row:
    show_results(exam_id, row, preview)
    if preview and st.button('체험 다시 시작'):
        del st.session_state[f'demo-{exam_id}']
        for key in list(st.session_state):
            if key.startswith(f'answer-{exam_id}-'):
                del st.session_state[key]
        st.rerun()
    st.stop()

st.header(exam['title'])
st.write(exam['description'])
st.caption('원본 문항 20점 유지 · 1번을 단답형과 서술형 입력으로 나누었습니다. 제출 전까지 수정할 수 있습니다.')
source, writing = st.columns([1, 1], gap='large')
with source:
    st.subheader('01 / 제시 자료')
    st.caption('그림과 기사·지도는 이미지의 확대 아이콘으로 자세히 살펴볼 수 있습니다.')
    pages = pdf_pages(exam['file_number'])
    if not pages:
        st.error('문항 PDF를 찾지 못했습니다. 선생님께 문의하세요.')
        st.stop()
    for i, page in enumerate(pages):
        st.image(page, caption=f"원본 문항 {exam['file_number']} · {i+1}쪽", width='stretch')
with writing:
    st.subheader('02 / 나의 답안')
    st.caption('제출 버튼을 눌렀을 때 저장됩니다. 제출 전에는 창을 닫거나 새로고침하지 마세요.')
    with st.form(f'exam-{exam_id}'):
        answers = {}
        for key, number, kind, points, prompt in exam['questions']:
            st.markdown(f'**{number} · {kind}**' + (f' / {points}점' if points else ' / 1번 합산'))
            if kind == '단답형':
                answers[key] = st.text_input(prompt, key=f'answer-{exam_id}-{key}', max_chars=100)
            else:
                answers[key] = st.text_area(prompt, key=f'answer-{exam_id}-{key}', height=150 if kind == '논술형' else 100, max_chars=5000)
        confirmed = st.checkbox('모든 답안을 확인했습니다. 최종 제출 후에는 수정하거나 다시 응시할 수 없음을 이해했습니다.')
        submit = st.form_submit_button('최종 제출하고 피드백 보기', type='primary', width='stretch')
    if submit:
        if not confirmed:
            st.error('제출 안내 확인란을 체크해 주세요.')
        elif any(not value.strip() for value in answers.values()):
            st.error('모든 문항에 답을 입력해 주세요.')
        else:
            result = evaluate(exam_id, answers)
            if preview:
                st.session_state[f'demo-{exam_id}'] = {'answers': json.dumps(answers, ensure_ascii=False), 'result': json.dumps(result, ensure_ascii=False), 'review': None}
                st.rerun()
            try:
                store.submit(exam_id, identity['id'], identity['name'], answers, result)
            except sqlite3.IntegrityError:
                st.warning('이미 제출한 평가입니다. 저장된 결과를 보여 드립니다.')
            st.rerun()
