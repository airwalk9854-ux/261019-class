"""Scoring bands transcribed/summarized from the two uploaded rubric tables.

Descriptors and matched text are teacher-only. Student feedback does not supply
missing event/policy/incident names or reproduce the model responses.
"""
import re

VERSION = 'rubric-pdf-v1'
COMMON = {
    4: ('사건 명칭·생산 방식 전환·면직물 생산 증가를 모두 설명', '사건과 생산 방식, 생산량의 관계를 함께 설명했습니다. 자료와 인과관계가 자연스럽게 연결되는지 확인하세요.'),
    3: ('생산 방식 전환과 생산 증가를 설명하나 사건 명칭이 없음', '생산 방식과 생산량의 변화를 연결했습니다. 변화가 일어난 역사적 사건의 명칭을 확인해 보세요.'),
    2: ('사건 명칭과 생산 방식 전환을 설명하나 생산 증가 설명이 없음', '역사적 사건과 생산 방식의 변화를 설명했습니다. 면직물 생산량의 변화까지 연결해 보세요.'),
    1: ('해당 내용을 서술하지 못함', '생산 도구와 작업 장소를 비교한 뒤, 역사적 사건과 생산량 변화에 관한 내용을 구성해 보세요.'),
}
RUBRICS = {
    'industry': {
        'production': ('산업혁명의 역사 이해', COMMON),
        'positive': ('산업혁명의 긍정적 영향 분석', {
            4: ('박람회의 기계 전시와 산업·국력 과시 또는 철도의 생활·여가·시간 개념 변화를 구체적으로 설명', '선택한 변화와 구체적인 영향을 자료에 연결했습니다. 한 가지 사례를 중심으로 설명을 정돈해 보세요.'),
            3: ('박람회의 성과 알림 또는 철도의 생활 범위·여가 확대를 설명', '긍정적 영향과 그 결과를 설명했습니다. 기사에 나타난 구체적 근거를 더 살펴보세요.'),
            2: ('박람회 또는 철도 발달을 긍정적 영향으로 제시', '긍정적 변화의 사례를 제시했습니다. 그 변화가 산업이나 생활에 어떤 영향을 주었는지 설명해 보세요.'),
            1: ('긍정적인 영향을 서술하지 못함', '기사에서 생활이나 산업의 변화를 보여주는 사례 한 가지를 골라 그 의미를 살펴보세요.'),
        }),
        'negative': ('산업혁명의 부정적 영향 분석', {
            4: ('인터뷰에 근거한 아동 노동 착취 또는 열악한 도시 위생과 전염병을 구체적으로 설명', '부정적 영향과 구체적인 피해를 자료의 근거로 설명했습니다. 근거와 결론의 연결을 확인해 보세요.'),
            3: ('아동의 힘든 노동 또는 환경 오염과 전염병 유행을 설명', '부정적 영향과 피해를 설명했습니다. 인터뷰나 도시 환경에서 구체적인 근거를 찾아 보완해 보세요.'),
            2: ('아동 노동 또는 환경 오염 문제를 제시', '문제의 종류를 제시했습니다. 자료에 나타난 피해와 그 원인을 함께 설명해 보세요.'),
            1: ('부정적인 영향을 서술하지 못함', '기사 속 사람들의 생활과 건강을 살펴보고 문제가 드러나는 사례 한 가지를 골라 보세요.'),
        }),
        'critique': ('산업혁명의 영향에 대한 비판적 이해', {
            8: ('박람회의 산업·국력 발전과 식민지 전시장·착취를 연결하여 비판', '산업적 번영과 식민지 주민의 희생을 자료에 연결하여 비판했습니다. 누구에게 혜택과 비용이 돌아갔는지 논리를 확인해 보세요.'),
            6: ('박람회의 긍정적 영향과 러다이트 운동 같은 구체적 노동 문제·격차를 비판', '긍정적 영향과 구체적인 사회 문제를 연결했습니다. 질문에서 요구한 해외 팽창과의 관계까지 검토해 보세요.'),
            4: ('박람회의 긍정적 영향과 일반적인 노동 문제·빈부 격차를 설명', '긍정적 영향과 사회 문제를 함께 제시했습니다. 구체적인 자료 근거와 해외 팽창의 관계를 보완해 보세요.'),
            3: ('비판적인 면만 서술', '비판적 관점을 제시했습니다. 비판의 대상이 되는 긍정적 영향과 자료의 근거도 함께 제시해 보세요.'),
            2: ('긍정적인 면만 서술', '긍정적 영향을 제시했습니다. 그 발전 과정에서 나타난 다른 집단의 피해도 함께 살펴보세요.'),
            1: ('산업혁명의 영향에 대한 내용을 서술하지 못함', '자료 속 변화 한 가지를 골라 그 혜택과 피해를 구분하는 것부터 시작해 보세요.'),
        }),
    },
    'imperialism': {
        'production': ('산업혁명의 역사 이해', COMMON),
        'rhodes': ('제국주의에 대한 자료 분석력', {
            6: ('실업·계층 갈등·인구·시장 등 정책의 원인과 식민지 확보 결과를 모두 설명', '정책의 배경과 결과를 함께 설명했습니다. 발언과 지도 각각의 근거가 인과관계를 뒷받침하는지 확인하세요.'),
            4: ('정책의 원인 또는 식민지 확보 결과 중 한 가지를 설명', '배경이나 결과 중 한 측면을 설명했습니다. 다른 측면도 해당 자료와 연결해 보세요.'),
            1: ('세실 로즈의 제국주의 정책을 서술하지 못함', '발언에 나타난 정책 추진 이유와 지도에 나타난 변화를 나누어 살펴보세요.'),
        }),
        'france': ('제국주의에 대한 사실적 이해', {
            4: ('프랑스인의 관점에서 횡단정책과 파쇼다 사건을 모두 서술', '정책과 충돌 사건을 프랑스인의 관점에서 설명했습니다. 당시 반응의 근거를 자료에서 확인해 보세요.'),
            3: ('프랑스의 정책 명칭과 충돌 사건명 중 하나만 서술', '정책 명칭과 충돌 사건명 중 하나를 제시했습니다. 나머지 요소와 프랑스인의 관점을 보완해 보세요.'),
            2: ('두 명칭 없이 제국주의에 관해 서술', '제국주의의 상황을 설명했습니다. 요구된 정책과 사건을 구분하고 프랑스인의 관점으로 정리해 보세요.'),
            1: ('제국주의에 관해 서술하지 못함', '지도에서 두 국가의 세력 확대 방향을 비교하고 프랑스가 느꼈을 반응을 생각해 보세요.'),
        }),
        'africa': ('제국주의에 대한 비판적 이해', {
            6: ('아프리카인의 관점에서 영국의 종단정책을 명시하여 비판 (원본 횡단 표기 정정)', '정책 명칭과 현지 주민의 관점을 연결해 비판했습니다. 구체적인 생활 경험과 감정이 주장을 뒷받침하는지 살펴보세요.'),
            4: ('제국주의 정책에 대한 부분적인 이해를 가지고 서술', '정책에 대한 부분적인 이해가 드러납니다. 요구된 정책 명칭과 현지 주민의 경험·감정을 연결해 보세요.'),
            1: ('아프리카인의 관점에서 제국주의를 비판하는 글을 서술하지 못함', '식민지 지배를 겪는 주민의 생활과 감정에서 출발하여 자신의 말로 반응을 구성해 보세요.'),
        }),
    },
}

def bands(exam, key):
    return RUBRICS[exam][key][1]

def band_feedback(exam, key, score):
    return bands(exam, key)[score][1]

def rubric_rows(exam):
    return [{'평가 항목': title, '점수': score, '채점 기준': description, '점수별 피드백': feedback}
            for key, (title, levels) in RUBRICS[exam].items()
            for score, (description, feedback) in levels.items()]

def score_answer(exam, key, answers):
    text = answers.get(key, '').strip()
    combined = (answers.get('event', '') + ' ' + text) if key == 'production' else text
    compact = re.sub(r'\s+', '', combined).lower()
    evidence = []

    def has(label, *terms):
        matches = [term for term in terms if re.sub(r'\s+', '', term).lower() in compact]
        if matches:
            evidence.append(f'{label}: ' + ', '.join(matches))
        return bool(matches)

    # A rule engine cannot safely interpret negation, reversed attribution, or
    # contradictory context. It abstains instead of awarding a high band.
    ambiguous = bool(re.search(r'않|아니|못했|못하|없었|없다|감소|줄어|영국(?:의|은|는)?횡단|프랑스(?:의|는|은)?종단', compact))
    reason = ''
    score = None
    if key == 'production':
        event = has('사건 명칭', '산업혁명', 'industrialrevolution')
        transition = has('이전 생산 방식', '가내수공업', '수공업') and has('이후 생산 방식', '공장제', '기계공업', '공장')
        growth = has('생산물', '면직물', '직물', '옷감') and has('생산 증가', '증가', '늘어', '늘었', '많아', '대량생산', '급증')
        if transition and growth:
            score = 4 if event else 3
        elif event and transition:
            score = 2
        elif not any([event, transition, growth]):
            score = 1
    elif key == 'positive':
        exhibition = has('박람회', '박람회')
        rail = has('철도', '철도', '기차')
        display = has('기계 전시', '기계전시', '기계를전시', '기계를보여')
        power = has('산업·국력', '국력', '산업발전', '산업이발전')
        achievement = has('성과 소개', '성과', '전시', '기술', '발전')
        life = has('생활 범위', '생활범위', '이동범위')
        leisure = has('여가', '여가', '여행')
        time = has('시간 개념', '시간개념', '시간표', '규칙적인시간', '규칙적시간')
        if (exhibition and display and power) or (rail and life and leisure and time):
            score = 4
        elif (exhibition and achievement) or (rail and life and leisure):
            score = 3
        elif exhibition or rail:
            score = 2
        else:
            score = 1
    elif key == 'negative':
        labour = has('아동 노동', '아동', '어린이') and has('노동', '노동', '일했', '일하')
        pollution = has('환경 문제', '환경오염', '환경문제', '매연', '폐수', '위생')
        exploitation = has('착취·장시간 노동', '착취', '장시간', '15시간', '14시간', '16시간', '4시간이하')
        source = has('인터뷰 근거', '인터뷰', '(다)', '기사', '자료')
        suffering = has('노동 피해', '힘들', '힘든', '고된', '고통', '혹독')
        disease = has('전염병', '콜레라', '전염병')
        city = has('도시 생활 조건', '빈민가', '노동자밀집', '도시')
        poor = has('열악한 위생', '열악', '위생악화', '비위생')
        if (labour and exploitation and source) or (pollution and disease and city and poor):
            score = 4
        elif (labour and (suffering or exploitation)) or (pollution and disease):
            score = 3
        elif labour or pollution:
            score = 2
        else:
            score = 1
    elif key == 'critique':
        exhibition = has('박람회', '박람회')
        prosperity = has('산업 발전', '발전', '국력', '번영', '풍요', '성과')
        positive = exhibition and prosperity
        colony = has('식민지', '식민지')
        exhibit = has('식민지 전시', '식민지전시장', '식민지전시관', '식민지를전시')
        exploitation = has('식민지 피해', '착취', '수탈', '희생', '침략')
        labour = has('사회 문제', '노동문제', '빈부격차', '노동착취', '아동노동', '계층격차')
        luddite = has('구체적 노동 운동', '러다이트', '기계파괴운동', '기계를파괴')
        critical = colony and exploitation or labour or luddite
        if positive and colony and exhibit and exploitation:
            score = 8
        elif positive and luddite:
            score = 6
        elif positive and labour:
            score = 4
        elif critical and not positive:
            score = 3
        elif positive and not critical:
            score = 2
        elif not positive and not critical:
            score = 1
    elif key == 'rhodes':
        cause = has('배경', '실업', '계층갈등', '인구', '시장', '빈부격차')
        # A future goal ("확보하기 위해") is not an achieved result.
        outcome = re.search(r'식민지[^.!?。]{0,35}(?:확보하였|확보했|확보했다|확장하였|확장했|확대하였|확대했|편입되|지배하였|지배했|차지하였|차지했|점령하였|점령했)', compact)
        result = bool(outcome)
        if outcome:
            evidence.append('확보 결과: ' + outcome.group())
        score = 6 if cause and result else 4 if cause or result else 1
    elif key == 'france':
        policy = has('프랑스 정책', '횡단정책')
        incident = has('충돌 사건', '파쇼다')
        viewpoint = has('프랑스 관점', '우리프랑스', '프랑스인', '프랑스의입장', '프랑스입장', '나는', '우리')
        imperial = has('제국주의 상황', '제국주의', '식민지', '영국', '프랑스', '아프리카')
        if policy and incident and viewpoint:
            score = 4
        elif policy != incident:
            score = 3
        elif not policy and not incident:
            score = 2 if imperial else 1
    elif key == 'africa':
        policy = has('영국 정책 (표기 정정)', '종단정책')
        viewpoint = has('현지 주민 관점', '우리', '나는', '아프리카인의입장', '아프리카인으로')
        critical = has('비판·피해', '착취', '수탈', '빼앗', '침략', '강제노동', '주권침탈', '분노', '저항', '반대')
        partial = has('제국주의 이해', '제국주의', '식민지', '종단', '지배', '광산', '토지')
        score = 6 if policy and viewpoint and critical else 4 if partial or critical else 1

    if ambiguous:
        score = None
        reason = '부정 표현·반대 방향의 변화가 포함되어 문맥 확인이 필요합니다.'
    elif score is None:
        reason = '서술 요소의 조합이 원본 점수 구간에 명확히 대응하지 않아 교사 확인이 필요합니다.'
    return {
        'score': score, 'max_score': max(bands(exam, key)),
        'rubric_title': RUBRICS[exam][key][0],
        'rubric_descriptor': bands(exam, key)[score][0] if score is not None else reason,
        'score_feedback': band_feedback(exam, key, score) if score is not None else '문맥과 자료 근거를 확인한 뒤 선생님이 해당 점수 구간을 결정합니다.',
        'evidence': evidence, 'needs_review': True,
        'rubric_source': {'file': f"논술형 문항{1 if exam == 'industry' else 2} 답안.pdf", 'pages': [1], 'version': VERSION},
    }
