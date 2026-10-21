"""Conservative, explicit spelling corrections for this assessment's vocabulary.

Original answers are preserved. Historical alternatives (e.g. 종단/횡단) are
never treated as spelling errors. This is not a general Korean spell checker.
"""
import unicodedata

TYPOS = {
    '산업혁멍': '산업혁명', '산업혁몀': '산업혁명', '산업혁명ㅇ': '산업혁명',
    '면직믈': '면직물', '면직뭄': '면직물', '가내수공엽': '가내수공업',
    '공장재': '공장제', '기계공엽': '기계공업', '생산랑': '생산량',
    '박람훼': '박람회', '박람희': '박람회', '아동노둥': '아동노동',
    '환경오엄': '환경오염', '전염뱡': '전염병', '콜래라': '콜레라',
    '제국주이': '제국주의', '제국주위': '제국주의', '식민디': '식민지',
    '종단정첵': '종단정책', '횡단정첵': '횡단정책',
    '파쇼타': '파쇼다', '파소다': '파쇼다', '아프리캬': '아프리카',
    '프랑쓰': '프랑스', '세실로즈으': '세실로즈',
    '증가햇': '증가했', '발전햇': '발전했', '착취햇': '착취했',
    '되엇': '되었', '돼었다': '되었다', '됬': '됐',
}


def check_spelling(text):
    corrected = unicodedata.normalize('NFKC', str(text or ''))
    notices = []
    for original, replacement in TYPOS.items():
        if original in corrected:
            corrected = corrected.replace(original, replacement)
            notices.append({'original': original, 'suggestion': replacement})
    return corrected, notices
