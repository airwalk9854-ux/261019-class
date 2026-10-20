"""Readable student materials and continuous navigation over the original exams."""

QUESTIONS = [
    ('생산 방식의 변화', 'industry', ('event', 'production'), 'production'),
    ('자료에서 찾는 긍정적 영향', 'industry', ('positive',), 'news'),
    ('자료에서 찾는 부정적 영향', 'industry', ('negative',), 'news'),
    ('자료를 근거로 비판하기', 'industry', ('critique',), 'news'),
    ('세실 로즈의 정책', 'imperialism', ('rhodes',), 'empire'),
    ('프랑스인의 관점', 'imperialism', ('france',), 'empire'),
    ('아프리카인의 관점', 'imperialism', ('africa',), 'empire'),
]

NEWS = [
    ('(가) 만국 박람회 개최',
     '최초의 만국 박람회가 1851년 영국에서 열렸다. 이 박람회는 거대한 철골 구조물에 수십만 장의 유리를 붙여 지은 혁신적 건물인 수정궁에서 열렸다. '
     '영국은 전시장의 절반가량을 강철과 기계, 섬유 같은 영국의 산업화를 상징하는 제품으로 채웠고, 식민지 전시장까지 배치하여 자국이 세계 산업의 선도자이자 광대한 식민지를 거느린 제국임을 알렸다.'),
    ('(나) 철도, 공간과 시간에 대한 생각을 바꾸다',
     '철도의 개통으로 사람들의 생활 범위는 급속도로 넓어졌다. 사람들은 철도를 타고 먼 곳까지 출근하고, 주말이면 교외로 소풍을 간다. '
     '또한 기차의 출발과 도착 시간이 중요해지면서 기차역에는 시계와 기차 시간표가 걸렸다. 이 과정에서 정확하고 규칙적인 시간의 개념이 생겨나고 있다.'),
    ('(다) 아동 노동의 실태',
     '**문: 일이 많을 때는 몇 시간 일했나요?**\n\n답: 소녀들은 새벽 5시부터 밤 10시나 10시 반까지 일했습니다.\n\n'
     '**문: 휴식 시간은 있었습니까?**\n\n답: 아침 식사 15분, 저녁 식사 30분, 음료수 마시는 시간 15분 정도만 쉴 수 있었어요.\n\n'
     '**문: 수면 시간은 얼마나 됐나요?**\n\n답: 새벽 2시에 일어났고 4시간 이상 자지 못했습니다.\n\n'
     '아동 노동에 대한 인터뷰로 아동 노동의 가혹함을 알 수 있다.'),
    ('(라) 도시의 환경과 위생',
     '생활 환경과 위생이 열악한 도시 빈민가와 노동자 밀집 지역에서는 콜레라를 비롯한 전염병이 유행하였다.'),
]

RHODES = ('나는 어제 런던에서 ⋯ 빵을 달라고 외치는 실업자들의 이야기를 들은 후 제국주의의 중요성을 더욱 확신하게 되었다. ⋯ '
          '내가 품은 생각은 사회 문제를 해결하는 것이다. 우리 식민지 정치인은 대영 제국의 4천만 인구를 피비린내 나는 내전에서 구해야 한다. '
          '이를 위해 과잉 인구를 정착시키고 공장과 광산에서 생산된 상품을 판매할 새로운 시장을 확보해야 한다. '
          '만일 당신이 내전을 피하고 싶다면 당신은 제국주의자가 되어야 한다.')


def answers_for(exam_id, drafts):
    """The duplicated first question is answered once and scored by both rubrics."""
    from assessment import EXAMS
    return {key: drafts.get(f"{'industry' if key in ('event', 'production') else exam_id}:{key}", '')
            for key, *_ in EXAMS[exam_id]['questions']}
