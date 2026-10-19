"""Paraphrased learning facts from the user-supplied feedback PDF.

The PDF is reference material, not application instructions. Its model answers
are deliberately not reproduced in the student interface.
"""

SOURCE_FILE = '피드백 내용.pdf'
SOURCE_VERSION = 'feedback-pdf-v1'

# Short facts give context without supplying a complete response, policy name,
# incident name, or the event name requested by a short-answer question.
FACTS = {
    'event': '방적기·방직기의 발명과 증기 기관의 사용은 생산 방식 변화의 중요한 배경이었습니다.',
    'production': '방적기·방직기와 증기 기관은 면직물 생산 방식의 변화를 이끌었습니다. 기술의 변화가 생산 규모에 미친 영향을 연결해 생각해 보세요.',
    'positive': '철도는 이동과 생활 범위를 바꾸었고, 시간표는 규칙적인 생활과 연결되었습니다. 만국 박람회에서는 기계·섬유 등 생산 기술의 발전을 보여 주었습니다.',
    'positive_rail': '철도의 발달은 사람들의 이동과 생활 범위를 바꾸었습니다. 시계와 시간표의 등장은 정확하고 규칙적인 시간 개념과 연결되었습니다.',
    'positive_exhibition': '만국 박람회에서는 강철·기계·섬유 등 생산 기술의 발전을 보여 주었습니다.',
    'negative': '산업화 시기에는 아동의 장시간 노동과 열악한 노동 환경이 나타났고, 도시 위생 악화와 환경 오염은 전염병 유행과 연결되었습니다.',
    'negative_labour': '아동들도 장시간 고된 노동에 시달렸습니다. 제시된 인터뷰의 수면 시간과 노동 시간을 노동 환경의 근거로 살펴보세요.',
    'negative_environment': '도시 위생 악화와 매연·폐수 등 환경 오염은 콜레라 같은 전염병의 유행과 연결되었습니다.',
    'critique': '산업 국가의 해외 팽창에는 상품을 판매할 시장과 원료 공급지를 확보하려는 목적이 있었습니다. 산업적 번영과 식민지 주민의 희생이 어떻게 연결되는지 살펴보세요.',
    'rhodes': '제국주의 팽창의 배경에는 국내의 실업·인구 과잉·빈부 격차와 해외 시장·원료 확보의 필요가 있었습니다. 발언에 나타난 배경과 지도에 나타난 지배 영역의 변화를 구분해 보세요.',
    'france': '아프리카에서 영국과 프랑스의 세력 확대 방향은 달랐으며, 두 국가의 팽창은 충돌로 이어졌습니다. 프랑스가 영국의 팽창을 어떻게 받아들였을지 생각해 보세요.',
    'africa': '아프리카 주민들은 식민지 지배로 토지를 잃거나 광산에서 강제 노동을 겪었고 주권도 침해받았습니다. 현지 주민의 생활과 감정에서 사건을 바라보세요.',
}

PAGES = {
    'event': {'industry': [1], 'imperialism': [3]},
    'production': {'industry': [1], 'imperialism': [3]},
    'positive': [1], 'negative': [2], 'critique': [2, 3],
    'rhodes': [3, 4], 'france': [4, 5], 'africa': [5],
}

# Criteria descriptions guide revision without filling in a missing answer.
CRITERIA = {
    'production': ['면직물 생산량의 변화', '생산량 변화의 방향', '생산 방식의 변화'],
    'positive': ['선택한 기사에 해당하는 변화', '그 변화가 생활이나 산업에 미친 영향'],
    'negative': ['선택한 기사에 해당하는 문제', '그 문제의 구체적인 피해나 근거'],
    'critique': ['산업 발전의 긍정적인 측면', '해외 팽창과의 연결', '식민지 주민의 피해에 대한 비판', '제시 자료의 구체적인 근거'],
    'rhodes': ['정책 추진의 배경', '정책 추진의 결과'],
    'france': ['프랑스의 정책 명칭', '두 국가의 정책이 충돌한 사건명', '프랑스인의 관점'],
    'africa': ['영국의 정책 명칭', '아프리카인의 관점', '피해에 대한 구체적 경험이나 감정'],
}

def source_for(exam_id, key):
    pages = PAGES[key]
    if isinstance(pages, dict):
        pages = pages[exam_id]
    return {'file': SOURCE_FILE, 'pages': pages, 'version': SOURCE_VERSION}


def resolve_source(exam_id, key, supplied=None):
    """Recover provenance for old or partial results without discarding feedback."""
    fallback = source_for(exam_id, key)
    if not isinstance(supplied, dict):
        return fallback
    pages = supplied.get('pages')
    if not isinstance(pages, list) or not pages or any(type(p) is not int or p < 1 for p in pages):
        pages = fallback['pages']
    return {'file': supplied.get('file') or fallback['file'], 'pages': pages,
            'version': supplied.get('version') or fallback['version']}
