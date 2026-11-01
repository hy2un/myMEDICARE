import pandas as pd
import streamlit as st

from drug_data_tools import load_data, split_ingredients


# ==========================================
# 1. 공통 디자인
# ==========================================

try:
    from site_theme import apply_style

except ModuleNotFoundError as exc:

    if exc.name != "site_theme":
        raise

    def apply_style():
        pass


apply_style()


# ==========================================
# 2. 페이지 제목
# ==========================================

st.title("📘 성분 사전")

st.caption(
    "의약품 성분명과 분류, 설명을 검색하고 "
    "어려운 의약품 용어의 뜻을 확인하세요."
)


# ==========================================
# 3. CSV 데이터 불러오기
# ==========================================

try:

    drugs, ingredients = load_data()

except (
    FileNotFoundError,
    KeyError,
    ValueError,
    pd.errors.ParserError,
) as exc:

    st.error(
        f"의약품 CSV 파일을 확인해 주세요: {exc}"
    )

    st.stop()


# ==========================================
# 4. 성분 검색
# ==========================================

keyword = st.text_input(
    "검색어",
    placeholder=(
        "예: 아세트아미노펜 / 항히스타민 / 진해"
    ),
    key="ingredient_dictionary_search",
)

result = ingredients.copy().fillna("")

if keyword.strip():

    search_columns = [
        "성분명",
        "분류",
        "설명",
    ]

    mask = result[
        search_columns
    ].astype(str).apply(
        lambda column: column.str.contains(
            keyword.strip(),
            case=False,
            regex=False,
            na=False,
        )
    ).any(axis=1)

    result = result.loc[mask].copy()


# ==========================================
# 5. 전체 성분 목록 표시
# ==========================================

st.subheader("전체 성분 목록")

st.write(
    f"조회된 성분 **{len(result)}개 "
    f"/ 전체 {len(ingredients)}개**"
)

if result.empty:

    st.info(
        "검색 조건에 해당하는 성분이 없습니다. "
        "검색어를 변경해 주세요."
    )

else:

    columns = [
        "성분명",
        "분류",
        "설명",
    ]

    if "출처URL" in result.columns:
        columns.append("출처URL")

    column_config = {}

    if "출처URL" in columns:

        column_config["출처URL"] = (
            st.column_config.LinkColumn(
                "정보 출처"
            )
        )

    st.dataframe(
        result[columns],
        use_container_width=True,
        hide_index=True,
        height=380,
        column_config=column_config,
    )


    # ======================================
    # 6. 해당 성분이 포함된 제품 확인
    # ======================================

    selected = st.selectbox(
        "해당 성분이 포함된 의약품 확인 (선택)",
        options=["선택 안 함"]
        + result["성분명"].astype(str).tolist(),
        key="ingredient_dictionary_product_lookup",
    )

    if selected != "선택 안 함":

        matched_products = [
            row["제품명"]
            for _, row in drugs.iterrows()
            if selected in split_ingredients(
                row["성분"]
            )
        ]

        if matched_products:

            st.write(
                "포함 제품: "
                + ", ".join(
                    sorted(set(matched_products))
                )
            )

        else:

            st.info(
                "현재 등록된 제품 데이터에서 "
                "해당 성분이 확인되지 않습니다."
            )


# ==========================================
# 7. 의약품 용어 해설
# ==========================================

st.divider()

st.subheader("🔎 의약품 용어 쉽게 이해하기")

st.caption(
    "아래 설명은 검색 여부와 관계없이 "
    "항상 표시됩니다."
)


GLOSSARY = [

    (
        "완하",
        "대변을 부드럽게 하거나 장운동을 도와 "
        "배변을 쉽게 하는 작용. "
        "완하제는 변비에 사용하는 약입니다."
    ),

    (
        "완화",
        "통증·불편함·긴장 등의 정도를 "
        "덜어 주는 것. "
        "'통증 완화'처럼 사용합니다."
    ),

    (
        "항히스타민",
        "히스타민의 작용을 억제해 "
        "재채기·콧물·가려움 등 "
        "알레르기 증상을 줄이는 약물군입니다."
    ),

    (
        "거담",
        "가래가 묽어지거나 배출되도록 "
        "도와주는 작용입니다."
    ),

    (
        "진해",
        "기침을 줄이거나 억제하는 작용입니다."
    ),

    (
        "비충혈·비충혈 완화",
        "비충혈은 코 점막 혈관에 피가 몰려 "
        "붓는 상태이고, 비충혈 완화제는 "
        "코막힘을 줄이기 위해 사용합니다."
    ),

    (
        "비스테로이드성 소염진통제(NSAIDs)",
        "스테로이드가 아닌 소염·진통·해열 약물군. "
        "예를 들어 이부프로펜·나프록센이 있으며 "
        "위장관·신장 부작용에 주의합니다."
    ),

    (
        "이뇨",
        "소변 배출을 늘리는 작용. "
        "일부 부종이나 고혈압 등에서 "
        "이뇨제가 사용됩니다."
    ),

    (
        "생약 성분",
        "식물·동물·광물 등 천연물에서 "
        "유래한 약용 원료. "
        "천연 유래라고 항상 안전한 것은 아닙니다."
    ),

    (
        "담즙산",
        "간에서 만들어져 지방의 소화·흡수를 "
        "돕는 물질. 일부 담즙산 계열 성분은 "
        "특정 담도 질환의 치료에 사용됩니다."
    ),

    (
        "청량 성분",
        "멘톨처럼 피부나 점막에 시원한 "
        "감각을 주는 성분. "
        "시원한 느낌 자체가 질병의 치료를 "
        "뜻하지는 않습니다."
    ),

    (
        "코르티코스테로이드",
        "염증과 면역 반응을 줄이는 "
        "스테로이드 계열 약물. "
        "사용 부위와 기간에 따라 "
        "주의사항이 다릅니다."
    ),

    (
        "외용 소염진통제로 사용",
        "먹는 약이 아니라 피부에 바르거나 "
        "붙이는 겔·크림·파스 등으로 "
        "통증과 염증을 국소적으로 줄이는 "
        "용도라는 뜻입니다."
    ),

]


# ==========================================
# 8. 용어 해설 표 표시
# ==========================================

glossary_df = pd.DataFrame(
    GLOSSARY,
    columns=[
        "용어",
        "뜻",
    ],
)

st.dataframe(
    glossary_df,
    use_container_width=True,
    hide_index=True,
    height=490,
)

st.caption(
    "의약품 용어 해설은 일반적인 설명이며, "
    "실제 약의 사용법은 제품 설명서와 "
    "의료진 안내를 확인하세요."
)
