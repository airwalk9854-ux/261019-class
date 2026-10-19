"""Transparent Korean paraphrase rules; no external model or API is used.

Recognize equivalent curriculum expressions, not whole-answer similarity.
Negation and incorrectly attributed historical policies still require review.
"""
import re
import unicodedata


def normalized(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(text or ''))).casefold()


ALIASES = {
    '수공업': ('집에서손으로', '가정에서손으로', '손으로짜', '손수만들', '손으로만들'),
    '공장': ('기계를이용해', '기계로생산', '기계로만들', '기계를사용해'),
    '면직물': ('면제품', '면포', '면으로짠천'),
    '직물': ('옷감', '천을', '천의', '천생산'),
    '증가': ('늘어', '늘었', '많아', '급증', '대량생산', '더많이', '훨씬많이', '크게늘', '더많은'),
    '박람회': ('만국박람회', '국제박람회'),
    '철도': ('기차', '기찻길', '철길', '증기기관차'),
    '기계전시': ('기계를전시', '기계를보여', '기계를선보', '기계들을전시', '기계가전시', '기계의전시'),
    '국력': ('나라의힘', '국가의힘', '국가의위상'),
    '발전': ('발달', '성장', '진보'),
    '산업발전': ('산업의발전', '산업의발달', '산업의성장'),
    '생활범위': ('활동범위', '활동반경', '더먼곳', '멀리갈', '먼곳까지', '이동할수있는범위'),
    '여가': ('관광', '쉬는날여행', '휴가'),
    '시간개념': ('시간을지키', '시간약속', '정해진시각', '출발시각', '정확한시각', '규칙적인생활', '규칙적으로생활'),
    '아동': ('아이들', '어린아이', '어린노동자', '소년', '소녀'),
    '노동': ('일했', '일하', '일해야', '일을했', '일을하', '일시켰', '근로', '일에시달'),
    '환경오염': ('공기오염', '물이오염', '하천오염', '강물오염', '더러운공기', '더러운물', '연기와폐수'),
    '착취': ('가혹한노동', '혹독한노동', '노동력을빼앗', '값싼노동력', '부려먹'),
    '장시간': ('오랜시간', '긴시간', '하루종일', '열다섯시간', '열여섯시간', '밤늦게까지'),
    '인터뷰': ('면담', '증언', '문답'),
    '기사': ('신문',),
    '힘들': ('고생', '고달', '지쳤', '피곤', '괴로'),
    '전염병': ('전염성질병', '감염병', '전염되는병'),
    '빈민가': ('가난한동네', '빈민촌'),
    '열악': ('불결', '더러', '나쁜위생'),
    '식민지전시장': ('식민지전시관', '식민지관', '식민지전시실', '식민지를전시'),
    '수탈': ('자원을빼앗', '자원을가져가', '자원을약탈', '자원의약탈'),
    '노동문제': ('노동자의문제', '노동자들이겪는문제', '노동환경문제'),
    '빈부격차': ('빈부차이', '부의격차', '부자와가난한사람', '빈부의격차', '빈부의차이'),
    '실업': ('일자리부족', '일자리를잃', '일자리가없', '일자리가부족', '일자리를구하지못'),
    '계층갈등': ('계층간갈등', '계급갈등', '계급간갈등'),
    '시장': ('판매처', '물건을팔곳', '상품을팔곳', '상품판매처', '물건을팔새로운곳'),
    '횡단정책': ('아프리카횡단', '횡단을추진', '횡단노선', '횡단구상'),
    '종단정책': ('아프리카종단', '종단을추진', '종단노선', '종단구상'),
    '파쇼다': ('fashoda',),
    '우리': ('저희',),
    '나는': ('저는', '내가', '제가'),
    '아프리카인의입장': ('아프리카주민으로서', '아프리카사람으로서'),
    '빼앗': ('빼앗겼', '앗아', '약탈'),
    '강제노동': ('억지로일', '강제로일', '노역', '강제노역'),
    '주권침탈': ('주권을빼앗', '주권을침해', '주권침해', '자유를빼앗'),
    '분노': ('화가난', '화가났', '화가난다', '분하다', '분했다', '억울'),
}


def matching_terms(text, *terms):
    compact = normalized(text)
    found = []
    for term in terms:
        for candidate in (term, *ALIASES.get(term, ())):
            if normalized(candidate) in compact and candidate not in found:
                found.append(candidate)
    return found


def contains(text, *terms):
    return bool(matching_terms(text, *terms))


def needs_context(text, key):
    compact = normalized(text)
    if re.search(r'영국(?:의|은|는)?횡단|프랑스(?:의|는|은)?종단', compact):
        return True
    if key == 'production':
        return bool(re.search(r'아니|않|못|감소|줄어|줄었|늘지|증가대신', compact))
    # Criticism such as "정당화할 수 없다" or "쉬지도 못했다" is
    # compatible with these tasks. Negated rubric facts still require review.
    return bool(re.search(
        r'(?:착취|수탈|침략|전시|확보|확대|발전|발달|증가|발생|유행|충돌|노동|추진|빼앗|오염|일하)[가-힣]{0,5}(?:않|아니|없|못)|'
        r'(?:종단정책|횡단정책|파쇼다)[가-힣]{0,4}(?:아니|없)|'
        r'감소|줄어', compact))


def event_is_correct(text):
    compact = normalized(text).strip('.!。')
    if re.search(r'아니|않|못|없|프랑스혁명|명예혁명', compact):
        return False
    return bool(re.fullmatch(
        r'(?:(?:18세기(?:후반)?|영국(?:의|에서(?:일어난)?)?|역사적사건(?:은|명칭은)?|정답은))*'
        r'(?:산업혁명(?:\(industrialrevolution\))?|industrialrevolution)'
        r'(?:이다|입니다|이었다|이었습니다|이야|이라고생각한다|이라고합니다)?', compact))
