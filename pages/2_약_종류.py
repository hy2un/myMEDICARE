from pathlib import Path

import pandas as pd
import streamlit as st

from drug_data_tools import load_data, search_drugs


# ==========================================
# 1. 공통 디자인 적용
# ==========================================

try:
    from site_theme import apply_style

except ModuleNotFoundError as exc:

    if exc.name != "site_theme":
        raise

    def apply_style():
        pass


apply_style()

ROOT = Path(__file__).resolve().parent.parent


# ==========================================
# 2. 페이지 제목
# ==========================================

st.title("🗂️ 약 종류")

st.caption(
    "등록 의약품, 성분 사전, 약물 분류 정보를 "
    "전체 조회하거나 검색할 수 있습니다."
)


# ==========================================
# 3. 의약품 및 성분 데이터 불러오기
# ==========================================

try:
    drugs, ingredients = load_data()

except (FileNotFoundError, KeyError, ValueError) as exc:

    st.error(
        f"의약품 데이터 파일을 확인해 주세요: {exc}"
    )

    st.stop()


# ==========================================
# 4. 확장 약물 카탈로그 데이터 불러오기
# ==========================================

extra_path = ROOT / "drug_catalog_extra.csv"

if extra_path.is_file():

    try:
        extra = pd.read_csv(
            extra_path,
            encoding="utf-8-sig",
        ).fillna("")

        required_columns = [
            "성분명",
            "약물분류",
            "설명",
            "주의사항",
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in extra.columns
        ]

        if missing_columns:
            st.error(
                "확장 카탈로그의 열 이름이 올바르지 않습니다: "
                + ", ".join(missing_columns)
            )
            st.stop()

    except (pd.errors.EmptyDataError, UnicodeError) as exc:
        st.error(
            f"확장 카탈로그 파일을 확인해 주세요: {exc}"
        )
        st.stop()

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
# 5. 전체 데이터 개수 표시
# ==========================================

col1, col2, col3 = st.columns(3)

col1.metric(
    "등록 의약품",
    len(drugs),
)

col2.metric(
    "성분 사전",
    len(ingredients),
)

col3.metric(
    "제품 분류",
    drugs["카테고리"].nunique(),
)


# ==========================================
# 6. 세 가지 조회 탭
# ==========================================

tab_products, tab_ingredients, tab_extra = st.tabs(
    [
        f"💊 의약품 전체 ({len(drugs)})",
        f"🧪 성분 전체 ({len(ingredients)})",
        f"📚 약물 분류 ({len(extra)})",
    ]
)


# ==========================================
# 7. 의약품 제품 전체 보기
# ==========================================

with tab_products:

    st.subheader("의약품 제품 전체 보기")

    # 제품 분류 목록
    categories = sorted(
        drugs["카테고리"]
        .dropna()
        .unique()
        .tolist()
    )

    category = st.selectbox(
        "제품 분류 선택",
        ["전체 보기"] + categories,
        key="catalog_drug_category",
    )

    # 제품 검색창
    query = st.text_input(
        "제품명·제조사·성분 검색",
        placeholder=(
            "검색하지 않으면 전체 제품을 표시합니다."
        ),
        key="catalog_drug_search",
    )

    # 전체 데이터 복사
    result = drugs.copy()

    # 분류별 필터링
    if category != "전체 보기":

        result = result[
            result["카테고리"] == category
        ].copy()

    # 제품명·제조사·성분 검색
    if query.strip():

        result = search_drugs(
            result,
            query.strip(),
        )

    # 검색 결과 개수
    st.write(
        f"조회된 제품 **{len(result)}개 "
        f"/ 전체 {len(drugs)}개**"
    )

    # 표에 표시할 정보
    columns = [
        "제품명",
        "제조사",
        "카테고리",
        "성분",
    ]

    # CSV에 해당 열이 있으면 함께 표시
    for optional in [
        "전문일반구분",
        "출처URL",
    ]:

        if optional in result.columns:
            columns.append(optional)

    config = {}

    if "출처URL" in columns:

        config["출처URL"] = (
            st.column_config.LinkColumn(
                "정보 출처"
            )
        )

    # ======================================
    # 예외 처리 1: 의약품 검색 결과 없음
    # ======================================

    if result.empty:

        st.info(
            "검색 조건에 해당하는 의약품이 없습니다. "
            "검색어 또는 제품 분류를 변경해 주세요."
        )

    else:

        st.dataframe(
            result[columns],
            use_container_width=True,
            hide_index=True,
            height=450,
            column_config=config,
        )

    st.caption(
        "제품별 허가·판매 현황은 변경될 수 있으므로 "
        "공식 의약품 정보를 확인해 주세요."
    )


# ==========================================
# 8. 의약품 성분 전체 보기
# ==========================================

with tab_ingredients:

    st.subheader("의약품 성분 전체 보기")

    # 성분 분류 목록
    categories = sorted(
        ingredients["분류"]
        .dropna()
        .unique()
        .tolist()
    )

    category = st.selectbox(
        "성분 분류 선택",
        ["전체 보기"] + categories,
        key="catalog_ingredient_category",
    )

    # 성분 검색창
    query = st.text_input(
        "성분명·분류·설명 검색",
        placeholder=(
            "예: 항히스타민, 완하, 아세트아미노펜"
        ),
        key="catalog_ingredient_search",
    )

    result = ingredients.copy()

    # 분류별 필터링
    if category != "전체 보기":

        result = result[
            result["분류"] == category
        ].copy()

    # 성분명·분류·설명 검색
    if query.strip():

        fields = [
            "성분명",
            "분류",
            "설명",
        ]

        matches = result[fields].astype(str).apply(
            lambda col: col.str.contains(
                query.strip(),
                case=False,
                regex=False,
                na=False,
            )
        ).any(axis=1)

        result = result[matches]

    # 검색 결과 개수
    st.write(
        f"조회된 성분 **{len(result)}개 "
        f"/ 전체 {len(ingredients)}개**"
    )

    # 표에 표시할 정보
    columns = [
        col
        for col in [
            "성분명",
            "분류",
            "설명",
            "출처URL",
        ]
        if col in result.columns
    ]

    config = {}

    if "출처URL" in columns:

        config["출처URL"] = (
            st.column_config.LinkColumn(
                "정보 출처"
            )
        )

    # ======================================
    # 예외 처리 2: 성분 검색 결과 없음
    # ======================================

    if result.empty:

        st.info(
            "검색 조건에 해당하는 성분이 없습니다. "
            "검색어 또는 성분 분류를 변경해 주세요."
        )

    else:

        st.dataframe(
            result[columns],
            use_container_width=True,
            hide_index=True,
            height=450,
            column_config=config,
        )

    st.caption(
        "성분 사전에서는 완하·완화·진해·거담 등 "
        "주요 의약품 용어의 의미도 확인할 수 있습니다."
    )


# ==========================================
# 9. 확장 약물 카탈로그 조회
# ==========================================

with tab_extra:

    st.subheader("성분·약물 분류 상세 정보")

    # 카탈로그 파일이 없거나 데이터가 없는 경우
    if extra.empty:

        st.warning(
            "확장 약물 카탈로그 데이터가 없습니다. "
            "GitHub 최상위 폴더의 "
            "drug_catalog_extra.csv 파일을 확인해 주세요."
        )

    else:

        # 약물 분류 목록
        categories = sorted(
            extra["약물분류"]
            .astype(str)
            .unique()
            .tolist()
        )

        category = st.selectbox(
            "약물 분류 선택",
            ["전체 보기"] + categories,
            key="catalog_extra_category",
        )

        # 카탈로그 검색창
        query = st.text_input(
            "성분명·설명·주의사항 검색",
            placeholder=(
                "검색하지 않으면 전체 약물 정보를 표시합니다."
            ),
            key="catalog_extra_search",
        )

        result = extra.copy()

        # 약물 분류 필터링
        if category != "전체 보기":

            result = result[
                result["약물분류"] == category
            ].copy()

        # 키워드 검색
        if query.strip():

            matches = result.astype(str).apply(
                lambda col: col.str.contains(
                    query.strip(),
                    case=False,
                    regex=False,
                    na=False,
                )
            ).any(axis=1)

            result = result[matches]

        # 검색 결과 개수
        st.write(
            f"조회된 약물 정보 **{len(result)}개 "
            f"/ 전체 {len(extra)}개**"
        )

        # ==================================
        # 예외 처리 3: 카탈로그 검색 결과 없음
        # ==================================

        if result.empty:

            st.info(
                "검색 조건에 해당하는 약물 정보가 없습니다. "
                "검색어 또는 약물 분류를 변경해 주세요."
            )

        else:

            st.dataframe(
                result,
                use_container_width=True,
                hide_index=True,
                height=450,
            )

    st.caption(
        "이 탭은 실제 시판 제품 목록이 아니라 "
        "성분 및 약물 계열에 대한 설명 자료입니다."
    )
