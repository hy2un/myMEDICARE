from pathlib import Path

import pandas as pd
import streamlit as st

from drug_data_tools import load_data, search_drugs

try:
    from site_theme import apply_style
except ModuleNotFoundError as exc:
    if exc.name != "site_theme":
        raise

    def apply_style():
        pass


apply_style()

ROOT = Path(__file__).resolve().parent.parent

st.title("🗂️ 약 종류")

st.caption(
    "등록 의약품, 성분 사전, 약물 분류 정보를 "
    "전체 조회하거나 검색할 수 있습니다."
)


# ==========================================
# 데이터 불러오기
# ==========================================

try:
    drugs, ingredients = load_data()

except (FileNotFoundError, KeyError, ValueError) as exc:
    st.error(f"의약품 데이터 파일을 확인해 주세요: {exc}")
    st.stop()


extra_path = ROOT / "drug_catalog_extra.csv"

if extra_path.is_file():
    extra = pd.read_csv(
        extra_path,
        encoding="utf-8-sig",
    ).fillna("")
else:
    extra = pd.DataFrame(
        columns=[
            "성분명",
            "약물분류",
            "설명",
            "주의사항",
        ]
    )


# ==========================================
# 전체 데이터 개수
# ==========================================

col1, col2, col3 = st.columns(3)

col1.metric("등록 의약품", len(drugs))
col2.metric("성분 사전", len(ingredients))
col3.metric(
    "제품 분류",
    drugs["카테고리"].nunique(),
)


# ==========================================
# 세 가지 탭
# ==========================================

tab_products, tab_ingredients, tab_extra = st.tabs(
    [
        f"💊 의약품 전체 ({len(drugs)})",
        f"🧪 성분 전체 ({len(ingredients)})",
        f"📚 약물 분류 ({len(extra)})",
    ]
)


# ==========================================
# 1. 의약품 제품 전체 보기
# ==========================================

with tab_products:

    st.subheader("의약품 제품 전체 보기")

    category = st.selectbox(
        "제품 분류 선택",
        ["전체 보기"]
        + sorted(
            drugs["카테고리"]
            .dropna()
            .unique()
            .tolist()
        ),
        key="catalog_drug_category",
    )

    query = st.text_input(
        "제품명·제조사·성분 검색",
        placeholder="검색하지 않으면 전체 제품을 표시합니다.",
        key="catalog_drug_search",
    )

    result = drugs.copy()

    if category != "전체 보기":
        result = result[
            result["카테고리"] == category
        ].copy()

    if query.strip():
        result = search_drugs(result, query)

    st.write(
        f"조회된 제품 **{len(result)}개 "
        f"/ 전체 {len(drugs)}개**"
    )

    columns = [
        "제품명",
        "제조사",
        "카테고리",
        "성분",
    ]

    for optional in ["전문일반구분", "출처URL"]:
        if optional in result.columns:
            columns.append(optional)

    config = {}

    if "출처URL" in columns:
        config["출처URL"] = (
            st.column_config.LinkColumn("정보 출처")
        )

    st.dataframe(
        result[columns],
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config=config,
    )

    st.caption(
        "제품별 허가·판매 현황은 바뀔 수 있습니다. "
        "미확인 정보는 공식 의약품 정보에서 "
        "확인해 주세요."
    )


# ==========================================
# 2. 성분 사전 전체 보기
# ==========================================

with tab_ingredients:

    st.subheader("의약품 성분 전체 보기")

    categories = sorted(
        ingredients["분류"]
        .dropna()
        .unique()
        .tolist()
    )

    ing_category = st.selectbox(
        "성분 분류 선택",
        ["전체 보기"] + categories,
        key="catalog_ingredient_category",
    )

    ing_query = st.text_input(
        "성분명·분류·설명 검색",
        placeholder="예: 항히스타민, 완하, 아세트아미노펜",
        key="catalog_ingredient_search",
    )

    ing_result = ingredients.copy()

    if ing_category != "전체 보기":
        ing_result = ing_result[
            ing_result["분류"] == ing_category
        ].copy()

    if ing_query.strip():

        fields = [
            "성분명",
            "분류",
            "설명",
        ]

        found = ing_result[fields].astype(str).apply(
            lambda col: col.str.contains(
                ing_query.strip(),
                case=False,
                regex=False,
                na=False,
            )
        ).any(axis=1)

        ing_result = ing_result[found]

    st.write(
        f"조회된 성분 **{len(ing_result)}개 "
        f"/ 전체 {len(ingredients)}개**"
    )

    ing_columns = [
        c
        for c in [
            "성분명",
            "분류",
            "설명",
            "출처URL",
        ]
        if c in ing_result.columns
    ]

    ing_config = {}

    if "출처URL" in ing_columns:
        ing_config["출처URL"] = (
            st.column_config.LinkColumn("정보 출처")
        )

    st.dataframe(
        ing_result[ing_columns],
        use_container_width=True,
        hide_index=True,
        height=450,
        column_config=ing_config,
    )

    st.caption(
        "'성분 사전' 메뉴에서는 완하·완화·진해·거담 등 "
        "어려운 용어 해설도 볼 수 있습니다."
    )


# ==========================================
# 3. 확장 약물 분류
# ==========================================

with tab_extra:

    st.subheader("성분·약물 분류 상세 정보")

    if extra.empty:

        st.warning(
            "GitHub 최상위 폴더에 "
            "drug_catalog_extra.csv를 추가해 주세요."
        )

    else:

        extra_category = st.selectbox(
            "약물 분류 선택",
            ["전체 보기"]
            + sorted(
                extra["약물분류"]
                .astype(str)
                .unique()
                .tolist()
            ),
            key="catalog_extra_category",
        )

        extra_query = st.text_input(
            "성분명·설명·주의사항 검색",
            key="catalog_extra_search",
        )

        extra_result = extra.copy()

        if extra_category != "전체 보기":
            extra_result = extra_result[
                extra_result["약물분류"]
                == extra_category
            ].copy()

        if extra_query.strip():

            found = extra_result.astype(str).apply(
                lambda col: col.str.contains(
                    extra_query.strip(),
                    case=False,
                    regex=False,
                    na=False,
                )
            ).any(axis=1)

            extra_result = extra_result[found]

        st.write(
            f"조회된 약물 정보 **{len(extra_result)}개 "
            f"/ 전체 {len(extra)}개**"
        )

        st.dataframe(
            extra_result,
            hide_index=True,
            use_container_width=True,
            height=450,
        )

    st.caption(
        "이 탭은 시판 제품 목록이 아니라 "
        "성분 및 약물 계열 설명 자료입니다."
    )
