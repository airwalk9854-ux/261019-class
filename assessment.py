"""Server-side assessment definitions; never sent as a downloadable answer key."""
from answer_matching import contains, event_is_correct
from feedback_content import FACTS, CRITERIA, source_for
from rubrics import score_answer
from spelling import check_spelling

EXAMS = {
    'industry': {
        'title': '산업혁명, 빛과 그림자', 'file_number': '1',
        'description': '생산 방식의 변화부터 산업 사회의 명암까지, 자료를 근거로 설명해 보세요.',
        'questions': [
            ('event', '1-①', '단답형', 0, '(가)에서 (나)로 변화하게 된 역사적 사건의 명칭을 쓰세요.'),
            ('production', '1-②', '서술형', 4, '앞에서 쓴 사건과 연결하여 (가)에서 (나)로 바뀐 생산 방식과 그 결과 면직물 생산량이 어떻게 변했는지 서술하세요. (1-①과 합산 4점)'),
            ('positive', '2-1 ①', '서술형', 4, '(가)~(라) 기사 중 긍정적인 영향 한 가지를 골라, 자료의 구체적 근거와 함께 서술하세요.'),
            ('negative', '2-1 ②', '서술형', 4, '(가)~(라) 기사 중 부정적인 영향 한 가지를 골라, 자료의 구체적 근거와 함께 서술하세요.'),
            ('critique', '2-2', '논술형', 8, '산업혁명을 부정적으로 바라보는 입장에서, 긍정적인 영향을 먼저 작성한 뒤 제시된 자료를 근거로 제국주의와 연결하여 비판하세요.'),
        ],
    },
    'imperialism': {
        'title': '제국주의, 서로 다른 시선', 'file_number': '2',
        'description': '같은 역사적 사건을 영국·프랑스·아프리카의 서로 다른 관점에서 살펴봅니다.',
        'questions': [
            ('event', '1-①', '단답형', 0, '(가)에서 (나)로 변화하게 된 역사적 사건의 명칭을 쓰세요.'),
            ('production', '1-②', '서술형', 4, '역사적 사건의 명칭을 포함하여, 생산 방식과 면직물 생산량의 변화를 서술하세요. (1-①과 합산 4점)'),
            ('rhodes', '3-1', '서술형', 6, '(가), (나)를 참고하여 세실 로즈가 추진한 제국주의 정책을 서술하세요. 배경은 (가), 결과는 (나)를 근거로 작성하세요.'),
            ('france', '3-2', '논술형', 4, '(다)를 참고하여 당시 프랑스인의 입장에서 세실 로즈의 정책에 대한 반응을 서술하세요. 프랑스의 정책 명칭과 두 국가의 정책이 충돌한 사건명을 포함하세요.'),
            ('africa', '3-3', '논술형', 6, '당시 아프리카인의 입장에서 세실 로즈의 정책에 대한 반응을 서술하세요. 영국의 정책 명칭을 넣고, 아프리카인의 입장에서 감정이입하여 작성하세요.'),
        ],
    },
}

def evaluate(exam_id, answers):
    """Provide source-based guidance and automatic discrete rubric scores."""
    corrected = {key: check_spelling(value)[0] for key, value in answers.items()}
    result = {}
    for key, _, kind, points, _ in EXAMS[exam_id]['questions']:
        text = corrected.get(key, '').strip()
        _, spelling = check_spelling(answers.get(key, ''))
        if key == 'event':
            correct = event_is_correct(text)
            result[key] = {'status': '정답' if correct else '오답', 'feedback': FACTS[key], 'source': source_for(exam_id, key), 'score': 0, 'spelling': spelling}
            continue
        graded = score_answer(exam_id, key, corrected)
        checks = graded['criteria_checks']
        status = '루브릭 기준 충족' if graded['score'] == graded['max_score'] else '루브릭 부분 충족 · 보완 필요'
        if not text:
            status = '미작성 · 루브릭 최저 구간 적용'
        fact_key = key
        if key == 'positive':
            rail, exhibition = contains(text, '철도', '기차'), contains(text, '박람회')
            if rail != exhibition:
                fact_key = 'positive_rail' if rail else 'positive_exhibition'
        if key == 'negative':
            labour = contains(text, '아동', '어린이', '노동')
            environment = contains(text, '환경', '위생', '오염', '전염병', '콜레라')
            if labour != environment:
                fact_key = 'negative_labour' if labour else 'negative_environment'
        missing = [label for label, matched in zip(CRITERIA[key], checks) if not matched]
        guidance = ('루브릭에 해당하는 표현이 확인되었습니다. 적용된 기준과 자료의 인과관계를 함께 확인해 보세요.'
                    if not missing else '보완할 부분: ' + ', '.join(missing) + '. 자료의 근거와 연결하여 살펴보세요.')
        feedback = FACTS[fact_key] + ' ' + guidance
        if graded['context_required']:
            feedback += ' 부정된 사실이나 잘못된 정책 연결은 점수 근거에서 제외했습니다. 사실관계와 변화 방향을 확인해 보세요.'
        result[key] = {**graded, 'spelling': spelling, 'status': status, 'feedback': feedback, 'source': source_for(exam_id, key)}
    return result
