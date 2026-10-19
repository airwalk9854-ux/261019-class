"""Server-side assessment definitions; never sent as a downloadable answer key."""
import re

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

FACTS = {
    'event': '18세기 후반 영국에서는 동력과 기계의 활용이 확대되면서 생산과 생활 전반에 큰 변화가 일어났습니다.',
    'production': '생산량을 설명할 때에는 생산 도구, 작업 장소, 동력의 변화가 작업 속도와 규모에 미친 영향을 연결해 살펴볼 수 있습니다.',
    'positive': '19세기 영국에서는 산업 성과를 보여 주는 전시와 철도망 확장이 나타났습니다. 자료 속 이동 시간·생활 범위·전시 내용은 변화의 근거가 됩니다.',
    'negative': '공장 노동자의 생활과 도시의 위생은 산업화 과정에서 중요한 사회 문제였습니다. 당시 영국의 공장법은 아동의 노동 시간과 근로 조건을 규제하려 했습니다.',
    'critique': '19세기의 산업 성장과 해외 식민지 확대는 서로 연결되어 있었습니다. 발전의 혜택과 비용이 어떤 집단에 돌아갔는지 구분하여 자료를 읽어 보세요.',
    'rhodes': '19세기 말 제국주의를 옹호한 정치인들은 국내 사회 문제와 해외 시장을 연결했습니다. 발언에 담긴 주장과 지도에서 확인되는 결과를 구분할 필요가 있습니다.',
    'france': '19세기 말 아프리카에서 유럽 열강의 세력 확대는 외교적 긴장을 일으켰습니다. 지도의 방향과 두 세력이 만나는 지역을 함께 살펴보세요.',
    'africa': '아프리카의 식민지화는 현지 주민의 토지, 자원, 노동과 정치적 자율성에 영향을 주었습니다. 제국의 관점과 현지 주민의 관점은 다를 수 있습니다.',
}

def evaluate(exam_id, answers):
    """Conservative rules: free writing is always provisional and teacher-reviewed.

    No automatic essay score: keyword coverage cannot establish historical reasoning.
    """
    result = {}
    for key, _, kind, points, _ in EXAMS[exam_id]['questions']:
        text = answers.get(key, '').strip()
        if key == 'event':
            correct = normalized(text) in {'산업혁명', '영국산업혁명', '산업혁명(industrialrevolution)', 'industrialrevolution'}
            result[key] = {'status': '정답' if correct else '오답 · 교사 확인 가능', 'feedback': FACTS[key], 'score': None}
            continue
        checks = {
            'production': [contains(text, '면직물', '옷감', '직물'), contains(text, '증가', '늘', '많', '대량'), contains(text, '기계', '공장')],
            'positive': [contains(text, '박람회', '철도', '기차'), contains(text, '전시', '국력', '시간', '여가', '여행', '생활범위')],
            'negative': [contains(text, '아동', '어린이', '환경', '위생'), contains(text, '착취', '시간', '노동', '콜레라', '전염병', '오염')],
            'critique': [contains(text, '박람회', '철도', '생산', '발전'), contains(text, '제국주의', '식민지'), contains(text, '착취', '수탈', '불평등', '지배')],
            'rhodes': [contains(text, '실업', '인구', '계층', '시장'), contains(text, '식민지', '지배', '점령'), contains(text, '(가)', '(나)', '자료', '지도', '발언')],
            'france': [contains(text, '횡단'), contains(text, '파쇼다'), contains(text, '우리', '프랑스', '나는')],
            'africa': [contains(text, '종단'), contains(text, '우리', '나는', '아프리카인'), contains(text, '착취', '수탈', '빼앗', '침략', '자유', '저항', '반대')],
        }[key]
        status = '관련 개념 확인 · 교사 검토 대기' if all(checks) else '보완 필요 · 교사 검토 대기'
        if not text:
            status = '미작성 · 교사 검토 대기'
        feedback = FACTS[key] + ' ' + ('관련 표현이 확인되었습니다. 근거와 인과관계의 타당성은 선생님이 최종 확인합니다.' if all(checks) else '자료의 구체적인 근거와 주장 사이의 연결을 다시 살펴보세요.')
        # Negation and contradictions require human reading, regardless of keywords.
        if contains(text, '않', '아니', '감소', '줄어'):
            status = '문맥 확인 필요 · 교사 검토 대기'
        result[key] = {'status': status, 'feedback': feedback, 'score': None}
    return result
