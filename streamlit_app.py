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
from rubrics import RUBRICS, bands, band_feedback, rubric_rows
from gradebook import export_workbook
from feedback_content import resolve_source
from question_content import QUESTIONS, NEWS, RHODES, answers_for
from learning import grade_question, comparison

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
def material_image(number, clip):
    files = [p for p in (ROOT / 'data').glob('*.pdf')
             if unicodedata.normalize('NFC', p.name) == f'논술형 문항{number}.pdf']
    if not files:
        return None
    with pymupdf.open(files[0]) as doc:
        return doc[0].get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=pymupdf.Rect(clip)).tobytes('png')


def show_material_image(number, clip, caption):
    picture = material_image(number, clip)
    if picture:
        st.image(picture, caption=caption, width='stretch')
    else:
        st.error('제시 자료를 찾지 못했습니다. 선생님께 문의하세요.')


def show_materials(material):
    st.subheader('제시 자료')
    if material == 'production':
        left, right = st.columns(2)
        with left:
            show_material_image('2', (64, 93, 292, 267), '(가) 가내 수공업')
        with right:
            show_material_image('2', (302, 94, 528, 267), '(나) 공장제 기계공업')
    elif material == 'news':
        st.caption('19세기 영국 사회를 다룬 가상의 신문 기사 · 원본의 기사와 설명을 읽기 쉬운 글로 재구성했습니다.')
        for title, text in NEWS:
            with st.container(border=True):
                st.markdown(f'#### {title}')
                st.markdown(text)
    else:
        with st.container(border=True):
            st.markdown('#### (가) 세실 로즈의 발언')
            st.write(RHODES)
        left, right = st.columns([1, 1.3])
        with left:
            show_material_image('2', (64, 503, 247, 746), '(나) 세실 로즈를 표현한 풍자화')
        with right:
            show_material_image('2', (267, 495, 534, 758), '(다) 아프리카 지도')
    if material == 'news':
        st.caption('출처: 원본 문항1 PDF의 기사 및 환경·위생 설명.')
    else:
        st.caption('출처: 원본 문항 PDF의 그림·기사·지도. 그림은 확대해서 볼 수 있습니다.')


def move_question(number):
    st.session_state['question_number'] = number


def show_results(exam_id, row, preview=False):
    st.success('체험이 끝났습니다. 실제 응시 기록에는 저장되지 않았습니다.' if preview else '제출이 완료되었습니다. 이 평가에는 다시 응시할 수 없습니다.')
    st.caption('점수는 업로드한 루브릭을 적용한 규칙 기반 예비 평가입니다. 문맥이 모호한 항목은 검토 대기로 표시하며, 선생님이 최종 점수를 확정합니다. 모범 답안은 제공하지 않습니다.')
    answers = json.loads(row['answers'])
    # Refresh learning guidance for previous submissions without altering answers,
    # attempt counts, stored assessment history, or teacher-confirmed judgments.
    results = evaluate(exam_id, answers)
    st.caption('학습 피드백은 「피드백 내용.pdf」를 바탕으로 제공합니다. 이전 제출도 현재 자료 기준의 예비 피드백으로 표시합니다.')
    review = json.loads(row['review']) if row.get('review') else {}
    scored_keys = list(RUBRICS[exam_id])
    if all(key in review for key in scored_keys):
        st.metric('교사 확정 점수', f"{sum(v['score'] for v in review.values())} / 20")
    elif all(results[key]['score'] is not None for key in scored_keys):
        st.metric('루브릭 예비 점수 · 교사 미확정', f"{sum(results[key]['score'] for key in scored_keys)} / 20")
    else:
        st.warning('일부 항목은 문맥 검토가 필요하여 예비 총점을 확정하지 않았습니다.')
    st.dataframe([{'문항': '1 (①+② 합산)' if key == 'production' else number,
                   '예비 점수': results[key]['score'], '교사 확정 점수': review.get(key, {}).get('score'), '만점': points}
                  for key, number, _, points, _ in EXAMS[exam_id]['questions'] if points], hide_index=True)
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
            if points:
                item = results[key]
                final_score = review.get(key, {}).get('score')
                if final_score in bands(exam_id, key):
                    st.info(f"확정 {final_score}점 피드백 · " + band_feedback(exam_id, key, final_score))
                elif item['score'] is not None:
                    st.info(f"예비 {item['score']} / {points}점 · " + item['score_feedback'])
                else:
                    st.warning(item['score_feedback'])
                rubric_source = item.get('rubric_source') or {}
                rubric_file = rubric_source.get('file') or f"논술형 문항{EXAMS[exam_id]['file_number']} 답안.pdf"
                st.caption(f"채점 근거: {rubric_file} · PDF 1쪽")
            st.info(results[key]['feedback'])
            source = resolve_source(exam_id, key, results[key].get('source'))
            st.caption(f"피드백 근거: {source['file']} · PDF {', '.join(map(str, source['pages']))}쪽")

st.caption('HISTORY CLASSROOM / 생각을 쓰고, 역사로 돌아보다')
st.title('역사의 시선')
st.write('산업혁명과 제국주의 · 자료를 읽고 나의 언어로 설명하는 역사 평가')

with st.sidebar:
    st.markdown('### 📜 역사 탐구실')
    st.caption('한 문제씩 배우는 서논술형 평가')
    if st.session_state.get('identity'):
        st.write(st.session_state['identity']['name'])
        if st.button('로그아웃', width='stretch'):
            st.session_state.clear()
            st.rerun()
    st.divider()
    st.markdown("""
### 학습 진행 안내

**① 자료 읽고 첫 답안 작성**

현재 문제의 자료를 읽고 나의 생각을 작성하세요.

**② 1차 제출과 피드백 확인**

‘이 문제 제출하고 피드백 보기’를 누르면 바로 채점 결과와 보완할 점을 확인할 수 있습니다.

**③ 답안 수정과 2차 채점**

피드백과 루브릭을 참고해 답안을 보완한 뒤 ‘수정 답안 제출하고 2차 채점’을 누르세요.

**④ 다음 문제로 이동**

2차 결과를 확인하고 ‘다음 문제 →’를 누르세요. 모든 문제를 같은 순서로 진행합니다.

**⑤ 최종 점수와 변화 확인**

모든 문제를 마치면 최종 학습 점수와 1·2차 점수 차이, 문제별 비교 그래프를 볼 수 있습니다.
""")
    with st.expander('답안 저장과 점수 안내'):
        st.markdown("""
- 제출한 1·2차 답안과 피드백은 각각 보관됩니다. 학생 계정은 재접속해도 이어서 진행할 수 있습니다.
- 제출 전 입력은 새로고침이나 창 닫기 시 사라질 수 있습니다. 체험 기록은 현재 세션에서만 유지됩니다.
- 전체 학습 점수는 공통 1번을 한 번만 합산한 **36점 만점**입니다.
- 자동 채점은 루브릭에 따른 예비 결과이며, 교사가 최종 확정합니다. 문맥 검토가 필요한 점수와 관련 총점·향상 폭은 검토 대기로 표시합니다.
""")
    question_menu = st.empty()

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
    st.caption('표현 확인 규칙으로 원본 점수 구간을 추천합니다. 부정 표현, 사실 오류, 자료 해석과 논증은 직접 확인하세요. 1-①과 1-②는 합산 4점이며, 원본 기준의 최저 점수는 항목당 1점입니다.')
    with st.expander('전체 루브릭 · 배점과 점수별 피드백 표'):
        for rubric_exam in RUBRICS:
            st.subheader(EXAMS[rubric_exam]['title'])
            st.dataframe(rubric_rows(rubric_exam), hide_index=True)
    rows = store.all()
    cols = st.columns(3)
    cols[0].metric('전체 제출', len(rows))
    cols[1].metric('검토 대기', sum(not r['review'] for r in rows))
    cols[2].metric('검토 완료', sum(bool(r['review']) for r in rows))
    st.download_button('루브릭·학생별 성적 Excel 내려받기', export_workbook(rows), '루브릭_평가결과.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
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
    history = store.attempts(row['student'])
    if history:
        from learning import comparison
        with st.expander('1·2차 답안과 점수 변화'):
            st.dataframe(comparison(history), hide_index=True)
            for (number, round_number), attempt in sorted(history.items()):
                st.write(f'{number}번 · {round_number}차')
                st.json(attempt['answers'])
    suggested = evaluate(row['exam'], answers)
    st.dataframe([{'항목': suggested[key]['rubric_title'], '예비 점수': suggested[key]['score'], '확정 점수': old.get(key, {}).get('score'), '만점': suggested[key]['max_score'], '적용한 구간': suggested[key]['rubric_descriptor']}
                  for key in RUBRICS[row['exam']]], hide_index=True)
    with st.form(f"review-{row['exam']}-{row['student']}"):
        review = {}
        for key, number, kind, points, prompt in EXAMS[row['exam']]['questions']:
            st.subheader(f'{number} · {kind}')
            st.write(prompt)
            st.text(answers.get(key, ''))
            statuses = ['정답', '부분 정답', '오답']
            previous = old.get(key, {})
            if points:
                item = suggested[key]
                st.caption('추천 근거: ' + (' / '.join(item['evidence']) or '확인된 표현 없음'))
                st.caption('추천 구간: ' + item['rubric_descriptor'])
                options = list(bands(row['exam'], key))
                default_score = previous.get('score', item['score'])
                if previous and default_score not in options:
                    st.warning('이전 점수가 현재 루브릭 구간에 없습니다. 기존 기록은 유지되며, 재확정 시 구간을 선택하세요.')
                score = st.selectbox('루브릭 최종 점수', options, index=options.index(default_score) if default_score in options else None, format_func=lambda value, exam=row['exam'], k=key: f"{value}점 · {bands(exam, k)[value][0]}", key=f'score-{key}-{selected}', placeholder='문맥을 검토하고 점수 구간을 선택하세요')
                status = '정답' if score == points else '부분 정답' if score is not None and score > 1 else '오답'
                if score is not None:
                    st.info(band_feedback(row['exam'], key, score))
            else:
                status = st.selectbox('최종 판정 (1번 합산의 명칭 확인)', statuses, index=statuses.index(previous.get('status', '정답' if suggested[key]['status'] == '정답' else '오답')), key=f'status-{key}-{selected}')
                score = 0
            feedback = st.text_area('추가 피드백 · 모범 답안 대신 역사적 사실과 보완 방향을 안내하세요.', value=previous.get('feedback', ''), key=f'feedback-{key}-{selected}')
            review[key] = {'status': status, 'score': score, 'feedback': feedback}
        if st.form_submit_button('교사 판정 저장', type='primary'):
            if any(item['score'] is None for item in review.values()):
                st.error('검토 대기 항목의 점수 구간을 모두 선택해 주세요.')
            else:
                store.review(row['exam'], row['student'], review)
                st.success('저장했습니다. 학생이 확정 점수와 해당 점수 구간의 피드백을 확인할 수 있습니다.')
    st.stop()

def show_attempt(number, attempt, round_number):
    _, exam, keys, _ = QUESTIONS[number - 1]
    st.subheader(f'{round_number}차 채점과 피드백')
    for key in keys:
        item = attempt['result'][key]
        st.text(attempt['answers'][key])
        st.write(item['status'])
        if key != 'event':
            if item['score'] is None:
                st.warning('점수 보류 · ' + item['score_feedback'])
            else:
                st.info(f"{item['score']} / {item['max_score']}점 · " + item['score_feedback'])
        st.info(item['feedback'])
        source = resolve_source(exam, key, item.get('source'))
        st.caption(f"피드백 근거: {source['file']} · PDF {', '.join(map(str, source['pages']))}쪽")
    st.caption('기존 루브릭에 따른 규칙 기반 예비 채점입니다. 문맥 검토가 필요한 점수는 보류하며 교사가 최종 확정합니다.')


def show_comparison(attempts, complete=False):
    records = comparison(attempts)
    if not records:
        return
    st.subheader('전체 학습 결과' if complete else '문제별 점수 변화')
    first = [r['1차 점수'] for r in records]
    second = [r['2차 점수'] for r in records]
    if complete and len(records) == len(QUESTIONS):
        cols = st.columns(3)
        cols[0].metric('1차 총점', '검토 대기' if None in first else f'{sum(first)} / 36')
        cols[1].metric('최종 학습 점수 · 2차', '검토 대기' if None in second else f'{sum(second)} / 36')
        delta = None if None in first or None in second else sum(second) - sum(first)
        cols[2].metric('1차 대비 변화', '검토 대기' if delta is None else f'{delta:+}점')
    st.caption('공통 1번을 한 번만 합산한 36점 만점입니다. 교사 확정 전에는 예비 점수입니다. 보류 점수는 0점으로 계산하지 않습니다.')
    st.dataframe(records, hide_index=True)
    import pandas as pd
    chart = pd.DataFrame(records).set_index('문제')[['1차 점수', '2차 점수']]
    st.bar_chart(chart, stack=False, y_label='루브릭 점수')
    if any(value is None for value in first + second):
        st.warning('보류된 점수는 그래프에서 생략했습니다. 보류 항목이 있으면 총점과 향상 점수도 확정하지 않습니다.')


preview = identity['role'] == '체험'
if preview:
    st.info('체험 모드 · 실제 응시 횟수에 반영되지 않습니다.')
rows = {exam: (st.session_state.get(f'demo-{exam}') if preview else store.get(exam, identity['id'])) for exam in EXAMS}
attempts = st.session_state.setdefault('demo-attempts', {}) if preview else store.attempts(identity['id'])
pending = [exam for exam, row in rows.items() if not row]
needed = [n for n, (_, exam, _, _) in enumerate(QUESTIONS, 1)
          if exam in pending and (n != 1 or not any(rows.values()))]
current = next((n for n in needed if (n, 2) not in attempts), None)

if not pending:
    st.header('최종 결과')
    st.success('모든 문제의 풀이와 채점이 완료되었습니다.')
    show_comparison(attempts, complete=True)
    if len(comparison(attempts)) < len(QUESTIONS):
        st.info('이전 방식으로 제출한 평가에는 1·2차 기록이 없어 전체 향상 점수를 계산할 수 없습니다.')
    for exam, row in rows.items():
        with st.expander(EXAMS[exam]['title'] + ' · 원본별 20점 결과'):
            show_results(exam, row, preview)
    for n in range(1, len(QUESTIONS) + 1):
        if (n, 2) in attempts:
            with st.expander(f'{n}번 · 처음 답안과 수정 답안 비교'):
                show_attempt(n, attempts[n, 1], 1)
                show_attempt(n, attempts[n, 2], 2)
    if preview and st.button('체험 다시 시작'):
        for key in list(st.session_state):
            if key.startswith(('demo-', 'response-')) or key == 'question_number':
                del st.session_state[key]
        st.rerun()
    st.stop()

available = [n for n in needed if (n, 2) in attempts or n == current]
if st.session_state.get('question_number') not in available:
    st.session_state['question_number'] = current
with question_menu.container():
    st.markdown('### 문제별 학습 현황')
    number = st.radio('문제 번호', available, key='question_number',
                      format_func=lambda n: f"{n}번 · {QUESTIONS[n-1][0]}" + (' · 완료' if (n, 2) in attempts else ' · 진행 중'))
    st.caption('현재 문제의 2차 채점 후 다음 문제가 열립니다. 완료한 문제를 선택하면 처음 답안과 수정 답안, 두 차수의 피드백을 다시 볼 수 있습니다.')

title, exam, keys, material = QUESTIONS[number - 1]
completed = sum((n, 2) in attempts for n in needed)
st.header(f'{number}번. {title}')
st.progress(completed / len(needed), text=f'2차 채점 완료 {completed} / {len(needed)}문제')
show_materials(material)
st.divider()
first = attempts.get((number, 1))
second = attempts.get((number, 2))
if first:
    show_attempt(number, first, 1)
if second:
    show_attempt(number, second, 2)
    show_comparison(attempts)
    st.button('다음 문제 →', on_click=move_question, args=(current,), type='primary')
else:
    round_number = 2 if first else 1
    st.subheader('피드백을 반영한 수정 답안' if first else '나의 첫 답안')
    if first:
        st.caption('처음 답안을 불러왔습니다. 위 피드백과 점수 기준을 참고해 보완한 뒤 다시 제출하세요.')
        with st.expander('이 문제의 루브릭 확인'):
            titles = {RUBRICS[exam][key][0] for key in keys if key in RUBRICS[exam]}
            st.dataframe([row for row in rubric_rows(exam) if row['평가 항목'] in titles], hide_index=True)
    else:
        st.caption('이 문제를 제출하면 바로 피드백을 받습니다. 제출한 1차 답안은 보존되며 수정은 2차 답안에서 합니다.')
    answers = {}
    for key, _, kind, points, prompt in EXAMS[exam]['questions']:
        if key not in keys:
            continue
        if key == 'production':
            prompt = '앞에서 쓴 사건과 연결하여 생산 방식과 면직물 생산량이 어떻게 변했는지 서술하세요.'
        widget = f'response-{number}-{round_number}-{key}'
        default = first['answers'][key] if first else ''
        if kind == '단답형':
            answers[key] = st.text_input(prompt, value=default, max_chars=100, key=widget)
        else:
            answers[key] = st.text_area(prompt, value=default, max_chars=5000, height=220, key=widget)
    label = '수정 답안 제출하고 2차 채점' if first else '이 문제 제출하고 피드백 보기'
    if st.button(label, type='primary', width='stretch'):
        try:
            payload = grade_question(number, answers)
            if preview:
                attempts[number, round_number] = payload
                if all((n, 2) in attempts for n in needed):
                    drafts = {}
                    for n, (_, question_exam, _, _) in enumerate(QUESTIONS, 1):
                        for key, value in attempts[n, 2]['answers'].items():
                            drafts[f'{question_exam}:{key}'] = value
                    for e in EXAMS:
                        final = answers_for(e, drafts)
                        st.session_state[f'demo-{e}'] = {'answers': json.dumps(final, ensure_ascii=False),
                            'result': json.dumps(evaluate(e, final), ensure_ascii=False), 'review': None}
            else:
                store.submit_question(identity['id'], identity['name'], number, round_number, answers)
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except sqlite3.IntegrityError:
            st.rerun()

if any(rows.values()):
    with st.expander('기존에 제출한 평가 결과'):
        for e, row in rows.items():
            if row:
                show_results(e, row, preview)
