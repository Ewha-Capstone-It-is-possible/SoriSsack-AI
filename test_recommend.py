"""
test_recommend.py
--------------
FastAPI 없이 로직만 빠르게 테스트하는 스크립트.
python test_recommend.py 로 실행.

아동 프로필:
  baby_id=1  민준 (6세 남아) — 음식·요청 중심
  baby_id=2  서아 (4세 여아) — 감정·놀이·미디어 중심
  baby_id=3  지호 (5세 남아) — 장난감·야외활동 중심
  baby_id=4  하은 (7세 여아) — 학교·일상·사람 중심
  baby_id=5  준서 (3세 남아) — 기초 단어 위주

baby_card_id 참고:
  민준(1xx): 101=밥, 102=물, 103=우유, 104=먹다, 105=주세요
             106=배고파, 107=엄마, 108=싫어, 109=아파, 110=화장실
             111=더, 112=안해, 113=마시다, 114=과자, 115=라면
             116=맛있어, 117=빵, 118=컵
             119=김치찌개(커스텀), 120=떡볶이(커스텀), 121=된장국(커스텀)

  서아(2xx): 201=인형, 202=갖고싶어요, 203=좋아, 204=뽀로로
             205=보다, 206=놀다, 207=주세요, 208=엄마, 209=슬퍼, 210=싫어
             211=행복해, 212=무서워, 213=TV, 214=같이, 215=아빠
             216=블록, 217=신나, 218=틀어줘
             219=핑크퐁(커스텀), 220=티니핑(커스텀), 221=보고싶어(커스텀), 222=예뻐(커스텀)

  지호(3xx): 301=장난감, 302=사주세요, 303=갖고싶어요, 304=놀고싶어요
             305=놀이터, 306=가다, 307=주세요, 308=엄마, 309=싫어, 310=아파
             311=공, 312=친구, 313=달리다, 314=레고, 315=놀다, 316=아빠
             317=축구공(커스텀), 318=더뛰고싶어(커스텀), 319=같이놀자(커스텀)

  하은(4xx): 401=학교, 402=선생님, 403=친구, 404=가다, 405=좋아
             406=싫어, 407=읽다, 408=그리다, 409=먹다, 410=아파
             411=맛있어, 412=힘들어, 413=같이, 414=밥, 415=물
             416=피곤해, 417=엄마, 418=아빠, 419=도와줘, 420=안아줘
             421=숙제(커스텀), 422=발표(커스텀), 423=칭찬받고싶어(커스텀)

  준서(5xx): 501=엄마, 502=아빠, 503=밥, 504=물, 505=주세요
             506=싫어, 507=아파, 508=좋아, 509=화장실, 510=도와줘
             511=무서워, 512=우유
             513=무서워요(커스텀), 514=같이놀자(커스텀), 515=뽀뽀(커스텀)
"""

from recommend import recommend_words

def print_result(title: str, result: dict):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")
    print(f"  아동 ID     : {result['baby_id']}")
    print(f"  선택 단어   : {result['selected_word'] or '(첫 선택)'}")
    print(f"  추천 결과   :")
    for i, w in enumerate(result["recommended_words"], 1):
        source = f"baby_card_id={w['baby_card_id']}" if w['baby_card_id'] else "card_master(미사용)"
        card   = f"card_id={w['card_id']}" if w['card_id'] else "커스텀(card_id=null)"
        print(f"    {i}. {w['text']:<14} | {w['pos']:<10} | score={w['system_score']:<6} | {card} | {source}")
    print()


if __name__ == "__main__":

    # ================================================================
    print("\n" + "★"*65)
    print("  baby_id=1  민준 (6세 남아) — 음식·요청 중심")
    print("★"*65)

    print_result("민준 — 첫 화면 (아무것도 안 선택)",
        recommend_words(baby_id=1, selected_baby_card_id=None))

    print_result("민준 — '배고파' 선택 → 밥/먹다/주세요 기대",
        recommend_words(baby_id=1, selected_baby_card_id=106))

    print_result("민준 — '밥' 선택 → 먹다/더/맛있어 기대",
        recommend_words(baby_id=1, selected_baby_card_id=101))

    print_result("민준 — '아파' 선택 → 엄마/도와줘/약 기대",
        recommend_words(baby_id=1, selected_baby_card_id=109))

    print_result("민준 — '김치찌개(커스텀)' 선택 → 먹다/맛있어/주세요 기대",
        recommend_words(baby_id=1, selected_baby_card_id=119))


    # ================================================================
    print("\n" + "★"*65)
    print("  baby_id=2  서아 (4세 여아) — 감정·놀이·미디어 중심")
    print("★"*65)

    print_result("서아 — 첫 화면",
        recommend_words(baby_id=2, selected_baby_card_id=None))

    print_result("서아 — '인형' 선택 → 갖고싶어요/사주세요 기대",
        recommend_words(baby_id=2, selected_baby_card_id=201))

    print_result("서아 — '뽀로로' 선택 → 보다/틀어줘/TV 기대",
        recommend_words(baby_id=2, selected_baby_card_id=204))

    print_result("서아 — '슬퍼' 선택 → 엄마/같이/안아줘 기대",
        recommend_words(baby_id=2, selected_baby_card_id=209))

    print_result("서아 — '핑크퐁(커스텀)' 선택 → 보다/틀어줘/TV 기대",
        recommend_words(baby_id=2, selected_baby_card_id=219))


    # ================================================================
    print("\n" + "★"*65)
    print("  baby_id=3  지호 (5세 남아) — 장난감·야외활동 중심")
    print("★"*65)

    print_result("지호 — 첫 화면",
        recommend_words(baby_id=3, selected_baby_card_id=None))

    print_result("지호 — '장난감' 선택 → 사주세요/갖고싶어요 기대",
        recommend_words(baby_id=3, selected_baby_card_id=301))

    print_result("지호 — '놀이터' 선택 → 가다/같이/달리다 기대",
        recommend_words(baby_id=3, selected_baby_card_id=305))

    print_result("지호 — '사주세요' 선택 → 장난감/레고/공 기대",
        recommend_words(baby_id=3, selected_baby_card_id=302))

    print_result("지호 — '축구공(커스텀)' 선택 → 사주세요/갖고싶어요 기대",
        recommend_words(baby_id=3, selected_baby_card_id=317))


    # ================================================================
    print("\n" + "★"*65)
    print("  baby_id=4  하은 (7세 여아) — 학교·일상·사람 중심")
    print("★"*65)

    print_result("하은 — 첫 화면",
        recommend_words(baby_id=4, selected_baby_card_id=None))

    print_result("하은 — '학교' 선택 → 가다/선생님/친구 기대",
        recommend_words(baby_id=4, selected_baby_card_id=401))

    print_result("하은 — '힘들어' 선택 → 엄마/도와줘/안아줘 기대",
        recommend_words(baby_id=4, selected_baby_card_id=412))

    print_result("하은 — '숙제(커스텀)' 선택 → 싫어/힘들어/도와줘 기대",
        recommend_words(baby_id=4, selected_baby_card_id=421))

    print_result("하은 — '밥' 선택 → 먹다/맛있어/더 기대",
        recommend_words(baby_id=4, selected_baby_card_id=414))


    # ================================================================
    print("\n" + "★"*65)
    print("  baby_id=5  준서 (3세 남아) — 기초 단어 위주")
    print("★"*65)

    print_result("준서 — 첫 화면 (기초 단어 위주)",
        recommend_words(baby_id=5, selected_baby_card_id=None))

    print_result("준서 — '엄마' 선택 → 주세요/아빠/안아줘 기대",
        recommend_words(baby_id=5, selected_baby_card_id=501))

    print_result("준서 — '밥' 선택 → 주세요/먹다/더 기대",
        recommend_words(baby_id=5, selected_baby_card_id=503))

    print_result("준서 — '무서워' 선택 → 엄마/도와줘/안아줘 기대",
        recommend_words(baby_id=5, selected_baby_card_id=511))


    # ================================================================
    print("\n" + "★"*65)
    print("  같은 단어, 다른 아이 — 개인화 비교")
    print("★"*65)

    # 민준 vs 서아 vs 지호 vs 하은 vs 준서 모두 '싫어' 눌렀을 때
    print_result("민준 — '싫어' 선택",
        recommend_words(baby_id=1, selected_baby_card_id=108))
    print_result("서아 — '싫어' 선택",
        recommend_words(baby_id=2, selected_baby_card_id=210))
    print_result("지호 — '싫어' 선택",
        recommend_words(baby_id=3, selected_baby_card_id=309))
    print_result("하은 — '싫어' 선택",
        recommend_words(baby_id=4, selected_baby_card_id=406))
    print_result("준서 — '싫어' 선택",
        recommend_words(baby_id=5, selected_baby_card_id=506))
