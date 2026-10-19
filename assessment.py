"""Server-side assessment definitions; never sent as a downloadable answer key."""
import re
from feedback_content import FACTS, CRITERIA, source_for

EXAMS = {
    'industry': {
        'title': '산업혁명, 빛과 그림자', 'file_number': '1',
        'description': '생산 방식의 변화부터 산업 사회의 명암까지, 자료를 근거로 설명해 보세요.',
        'questions': [
            ('event', '1-①', '단답형', 0, '(가)에서 (나)로 변화하게 된 역사적 사건의 명칭을 쓰세요.'),
            ('production', '1-②', '서술형', 4, '앞에서 쓴 사건과 연결하여 면직물 생산량이 어떻게 변했는지 서술하세요. (1-①과 합산 4점)'),
            ('positive', '2-1 ①', '서술형', 4, '(가)~(라) 기사 중 긍정적인 영향 한 가지를 골라, 자료의 구체적 근거와 함께 서술하세요.'),
            ('negative', '2-1 ②', '서술형', 4, '(가)~(라) 기사 중 부정적인 영향 한 가지를 골라, 자료의 구체적 근거와 함께 서술하세요.'),
            ('critique', '2-2', '논술형', 8, '산업혁명의 긍정적인 영향을 먼저 작성하고, 제시된 자료를 근거로 제국주의와 연결하여 비판하세요.'),
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

def normalized(text):
    return re.sub(r'\s+', '', text).lower()

def contains(text, *words):
    return any(normalized(w) in normalized(text) for w in words)

def evaluate(exam_id, answers):
    """Conservative rules: free writing is always provisional and teacher-reviewed.

    No automatic essay score: keyword coverage cannot establish historical reasoning.
    """
    result = {}
    for key, _, kind, points, _ in EXAMS[exam_id]['questions']:
        text = answers.get(key, '').strip()
        if key == 'event':
            correct = normalized(text) in {'산업혁명', '영국산업혁명', '산업혁명(industrialrevolution)', 'industrialrevolution'}
            result[key] = {'status': '정답' if correct else '오답 · 교사 확인 가능', 'feedback': FACTS[key], 'source': source_for(exam_id, key), 'score': None}
            continue
        checks = {
            'production': [contains(text, '면직물', '옷감', '직물'), contains(text, '증가', '늘', '많', '대량'), contains(text, '기계', '공장')],
            'positive': [contains(text, '박람회', '철도', '기차'), contains(text, '전시', '국력', '시간', '여가', '여행', '생활범위')],
            'negative': [contains(text, '아동', '어린이', '환경', '위생'), contains(text, '착취', '시간', '노동', '콜레라', '전염병', '오염')],
            'critique': [contains(text, '박람회', '철도', '생산', '발전'), contains(text, '제국주의', '식민지'), contains(text, '착취', '수탈', '불평등', '희생', '침략'), contains(text, '(가)', '자료', '박람회', '전시장', '전시관')],
            'rhodes': [contains(text, '실업', '인구', '계층', '시장', '원료', '빈부'), contains(text, '식민지', '지배', '점령'), contains(text, '종단', '남북', '케이프타운', '카이로')],
            'france': [contains(text, '횡단'), contains(text, '파쇼다'), contains(text, '우리', '프랑스', '나는')],
            'africa': [contains(text, '종단'), contains(text, '우리', '나는', '아프리카인'), contains(text, '착취', '수탈', '빼앗', '침략', '자유', '저항', '반대', '토지', '강제', '광산', '주권', '분노', '고통')],
        }[key]
        status = '관련 개념 확인 · 교사 검토 대기' if all(checks) else '보완 필요 · 교사 검토 대기'
        if not text:
            status = '미작성 · 교사 검토 대기'
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
        guidance = ('관련 표현이 확인되었습니다. 자료 해석과 인과관계의 타당성은 선생님이 최종 확인합니다.'
                    if not missing else '보완할 부분: ' + ', '.join(missing) + '. 자료의 근거와 연결하여 살펴보세요.')
        feedback = FACTS[fact_key] + ' ' + guidance
        # Negation and contradictions require human reading, regardless of keywords.
        if contains(text, '않', '아니', '감소', '줄어'):
            status = '문맥 확인 필요 · 교사 검토 대기'
            feedback += ' 부정 표현이나 변화 방향은 문맥에 따라 의미가 달라지므로 선생님의 확인이 필요합니다.'
        result[key] = {'status': status, 'feedback': feedback, 'source': source_for(exam_id, key), 'score': None}
    return result
