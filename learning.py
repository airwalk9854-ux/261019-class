"""Question-level attempts and score comparisons; shared by storage and UI."""
from assessment import EXAMS, evaluate
from question_content import QUESTIONS


def grade_question(number, answers):
    _, exam, keys, _ = QUESTIONS[number - 1]
    if any(not isinstance(answers.get(key), str) or not answers[key].strip() for key in keys):
        raise ValueError('이 문제의 답안을 모두 작성해 주세요.')
    clean = {key: answers[key].strip() for key in keys}
    result = evaluate(exam, clean)
    return {'answers': clean, 'result': {key: result[key] for key in keys}}


def score(attempt):
    values = [item['score'] for key, item in attempt['result'].items() if key != 'event']
    return None if any(value is None for value in values) else sum(values)


def comparison(attempts):
    rows = []
    for number, (title, exam, keys, _) in enumerate(QUESTIONS, 1):
        if (number, 1) not in attempts or (number, 2) not in attempts:
            continue
        first, second = score(attempts[number, 1]), score(attempts[number, 2])
        maximum = sum(points for key, _, _, points, _ in EXAMS[exam]['questions'] if key in keys)
        rows.append({'문제': f'{number}번', '제목': title, '1차 점수': first, '2차 점수': second,
                     '변화': second - first if first is not None and second is not None else None, '만점': maximum})
    return rows
