from pathlib import Path

import pandas as pd
import streamlit as st

from drug_data_tools import load_data
from drug_data_tools import load_condition_data
from drug_data_tools import get_selected_drugs
from drug_data_tools import find_duplicates
from drug_data_tools import search_drugs
from drug_data_tools import search_conditions
from drug_data_tools import split_ingredients


# ==========================================
# 1. 기본 설정
# ==========================================

st.set_page_config(
    page_title="MyMedi Care",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent


# ==========================================
# 2. 디자인 설정
# ==========================================

st.markdown(
    """
<style>
.stApp {
    background: #fbfcfb;
    color: #1b3040;
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stMainBlockContainer"] {
    max-width: 1150px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e8efea;
}

[data-testid="stSidebarNav"] a {
    border-radius: 12px;
    margin: 3px 4px;
}

[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: #eaf5ef;
    color: #126f5b;
}

/* 상단 그림 배너 */

.st-key-home_hero {
    background: linear-gradient(
        110deg,
        #f1f8f3 0%,
        #f7faf4 55%,
        #eaf5ef 100%
    );

    border: 1px solid #e6f0e9;
    border-radius: 24px;

    padding: 24px 30px 10px;
    margin-bottom: 17px;

    overflow: hidden;
}

.st-key-home_hero h1 {
    color: #137a65;
    font-size: clamp(2.1rem, 3.2vw, 3.05rem);
    font-weight: 850;
    letter-spacing: -0.045em;
    margin-bottom: 5px;
}

.st-key-home_hero h3 {
    color: #1b3340;
    font-size: clamp(1.15rem, 1.75vw, 1.55rem);
    letter-spacing: -0.03em;
    margin-top: 5px;
}

.st-key-home_hero [data-testid="stCaptionContainer"] {
    color: #537066;
    font-size: 0.95rem;
}

.st-key-home_hero img {
    width: 100%;
    object-fit: contain;
}

/* 기존 기능 탭 */

.stTabs [data-baseweb="tab-list"] {
    gap: 9px;
    border-bottom: 1px solid #e2ece6;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 12px 12px 0 0;
    padding: 11px 19px;
    font-weight: 700;
}

.stTabs [aria-selected="true"] {
    color: #0d7a65 !important;
    background: #edf7f1 !important;
}

/* 버튼 */

.stButton button {
    border-radius: 11px;
}

.stButton button[kind="primary"] {
    background: #16836b;
    border-color: #16836b;
}

.stButton button[kind="primary"]:hover {
    background: #106751;
    border-color: #106751;
}

/* 검색창 */

[data-testid="stTextInput"] input {
    border-radius: 11px;
}

/* 데이터 표 */

[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

/* 모바일 화면 */

@media (max-width: 720px) {
    .st-key-home_hero {
        padding: 18px 18px 10px;
    }

    .st-key-home_hero h1 {
        font-size: 2rem;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# ==========================================
# 3. 메인 페이지
# ==========================================

def home_page():

    # 데이터 불러오기
    try:
        drug_data, _ = load_data()
        condition_data = load_condition_data()

    except Exception as error:
        st.error("CSV 데이터 파일을 불러오지 못했습니다.")
        st.code(str(error))
        st.stop()

    # 사용자 정보 초기화
    if "my_drugs" not in st.session_state:
        st.session_state.my_drugs = []

    if "my_conditions" not in st.session_state:
        st.session_state.my_conditions = []

    # ======================================
    # 상단 그림 디자인
    # ======================================

    with st.container(key="home_hero"):

        left, right = st.columns(
            [1.05, 1],
            gap="medium",
        )

        with left:

            st.title("MyMedi Care")

            st.markdown(
                "### 건강한 오늘을 함께해요"
            )

            st.caption(
                "나의 약과 건강 기록, "
                "그리고 반려동물까지."
            )

        with right:

            picture = (
                BASE_DIR
                / "hero_characters.png"
            )

            if picture.is_file():

                st.image(
                    str(picture),
                    use_container_width=True,
                )

            else:

                st.caption(
                    "assets/hero_characters.png "
                    "이미지를 추가해 주세요."
                )

    # ======================================
    # 기존의 3개 탭만 유지
    # ======================================

    tab_my_drugs, tab_compare, tab_conditions = st.tabs(
        [
            "나의 약",
            "성분 분석",
            "나의 질병",
        ]
    )

    # ======================================
    # 첫 번째 탭: 나의 약
    # ======================================

    with tab_my_drugs:

        st.subheader("💊 나의 약")

        st.caption(
            "약을 검색해 추가하거나 삭제할 수 있습니다."
        )

        keyword = st.text_input(
            "약 이름 검색",
            placeholder="예: 타이레놀, 게보린, 판콜",
            key="my_drug_search_keyword",
        )

        if keyword.strip():

            result = search_drugs(
                drug_data,
                keyword,
            )

            if result.empty:

                st.info("검색 결과가 없습니다.")

            else:

                st.dataframe(
                    result[
                        [
                            "제품명",
                            "제조사",
                            "카테고리",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                name = st.selectbox(
                    "추가할 약 선택",
                    result["제품명"].tolist(),
                    key="selected_search_drug",
                )

                if st.button(
                    "나의 약에 추가",
                    type="primary",
                    key="add_my_drug_button",
                ):

                    if name in st.session_state.my_drugs:

                        st.info(
                            "이미 추가된 제품입니다."
                        )

                    else:

                        st.session_state.my_drugs.append(
                            name
                        )

                        st.rerun()

        else:

            st.info(
                "약 이름을 입력하면 검색할 수 있습니다."
            )

        st.divider()

        st.markdown("#### 현재 나의 약")

        if st.session_state.my_drugs:

            chosen = get_selected_drugs(
                drug_data,
                st.session_state.my_drugs,
            )

            st.dataframe(
                chosen[
                    [
                        "제품명",
                        "제조사",
                        "카테고리",
                        "성분",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            remove_name = st.selectbox(
                "삭제할 약 선택",
                st.session_state.my_drugs,
                key="remove_drug_select",
            )

            a, b = st.columns(2)

            with a:

                if st.button(
                    "선택한 약 삭제",
                    key="remove_drug_button",
                    use_container_width=True,
                ):

                    st.session_state.my_drugs.remove(
                        remove_name
                    )

                    st.rerun()

            with b:

                if st.button(
                    "나의 약 전체 삭제",
                    key="clear_my_drugs_button",
                    use_container_width=True,
                ):

                    st.session_state.my_drugs = []

                    st.rerun()

        else:

            st.write(
                "아직 추가된 약이 없습니다."
            )

        st.caption(
            "나의 약은 현재 앱 세션에만 임시 저장됩니다."
        )

    # ======================================
    # 두 번째 탭: 성분 분석
    # ======================================

    with tab_compare:

        st.subheader("🧪 성분 분석")

        st.caption(
            "약 2~5개를 선택해 공통 성분과 "
            "제품별 성분을 비교합니다."
        )

        names = st.multiselect(
            "비교할 약 선택",
            sorted(
                drug_data[
                    "제품명"
                ].dropna().unique().tolist()
            ),
            max_selections=5,
            placeholder="의약품 2~5개를 선택하세요",
            key="compare_drug_names",
        )

        st.caption(
            f"현재 {len(names)}개 선택 / 최대 5개"
        )

        if names:

            chosen = get_selected_drugs(
                drug_data,
                names,
            )

            st.dataframe(
                chosen[
                    [
                        "제품명",
                        "제조사",
                        "카테고리",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

        if st.button(
            "성분 비교하기",
            type="primary",
            key="compare_ingredients_button",
        ):

            if len(names) < 2:

                st.warning(
                    "약을 2개 이상 선택해 주세요."
                )

            else:

                chosen = get_selected_drugs(
                    drug_data,
                    names,
                )

                duplicates, ingredient_map = find_duplicates(
                    chosen
                )

                all_ingredients = sorted(
                    ingredient_map.keys()
                )

                x, y, z = st.columns(3)

                x.metric(
                    "비교 제품 수",
                    len(names),
                )

                y.metric(
                    "고유 성분 수",
                    len(all_ingredients),
                )

                z.metric(
                    "중복 성분 수",
                    len(duplicates),
                )

                st.markdown("#### 중복 성분")

                if duplicates:

                    rows = [
                        {
                            "중복 성분": ingredient,
                            "포함 제품 수": len(products),
                            "포함 제품": ", ".join(products),
                        }
                        for ingredient, products
                        in sorted(duplicates.items())
                    ]

                    st.dataframe(
                        pd.DataFrame(rows),
                        use_container_width=True,
                        hide_index=True,
                    )

                else:

                    st.success(
                        "성분명 기준으로 중복된 성분이 "
                        "발견되지 않았습니다."
                    )

                sets = {
                    row["제품명"]: set(
                        split_ingredients(
                            row["성분"]
                        )
                    )
                    for _, row in chosen.iterrows()
                }

                rows = []

                for ingredient in all_ingredients:

                    item = {
                        "성분명": ingredient
                    }

                    for name in names:

                        item[name] = (
                            "✓"
                            if ingredient in sets.get(
                                name,
                                set(),
                            )
                            else ""
                        )

                    rows.append(item)

                st.markdown(
                    "#### 제품별 성분 비교표"
                )

                st.dataframe(
                    pd.DataFrame(
                        rows,
                        columns=["성분명"] + names,
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                st.info(
                    "같은 성분의 포함 여부만 비교하며, "
                    "실제 병용 안전성을 판단하지 않습니다."
                )

    # ======================================
    # 세 번째 탭: 나의 질병
    # ======================================

    with tab_conditions:

        st.subheader("📋 나의 질병")

        st.caption(
            "질병이나 증상을 검색하고 "
            "목록에 추가할 수 있습니다."
        )

        keyword = st.text_input(
            "질병·증상 검색",
            placeholder="예: 감기, 독감, 비염",
            key="condition_search_keyword",
        )

        if keyword.strip():

            result = search_conditions(
                condition_data,
                keyword,
            )

            if result.empty:

                st.info("검색 결과가 없습니다.")

            else:

                st.dataframe(
                    result[
                        [
                            "질병명",
                            "분류",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                name = st.selectbox(
                    "추가할 질병·증상 선택",
                    result["질병명"].tolist(),
                    key="selected_condition",
                )

                if st.button(
                    "나의 질병에 추가",
                    type="primary",
                    key="add_condition_button",
                ):

                    if name in st.session_state.my_conditions:

                        st.info(
                            "이미 추가된 항목입니다."
                        )

                    else:

                        st.session_state.my_conditions.append(
                            name
                        )

                        st.rerun()

        else:

            st.info(
                f"현재 {len(condition_data)}개 "
                "질병·증상 항목에서 검색할 수 있습니다."
            )

        st.divider()

        st.markdown("#### 현재 나의 질병")

        if st.session_state.my_conditions:

            chosen = condition_data[
                condition_data[
                    "질병명"
                ].isin(
                    st.session_state.my_conditions
                )
            ]

            st.dataframe(
                chosen[
                    [
                        "질병명",
                        "분류",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            remove_name = st.selectbox(
                "삭제할 항목 선택",
                st.session_state.my_conditions,
                key="remove_condition_select",
            )

            a, b = st.columns(2)

            with a:

                if st.button(
                    "선택한 항목 삭제",
                    key="remove_condition_button",
                    use_container_width=True,
                ):

                    st.session_state.my_conditions.remove(
                        remove_name
                    )

                    st.rerun()

            with b:

                if st.button(
                    "나의 질병 전체 삭제",
                    key="clear_condition_button",
                    use_container_width=True,
                ):

                    st.session_state.my_conditions = []

                    st.rerun()

        else:

            st.write(
                "아직 추가된 질병·증상이 없습니다."
            )

        st.caption(
            "질병·증상 기록용 기능이며 "
            "진단 서비스가 아닙니다."
        )


# ==========================================
# 4. 기존 왼쪽 메뉴 유지
# ==========================================

home = st.Page(
    home_page,
    title="MyMedi Care",
    icon="💊",
    default=True,
)

ingredient_page = st.Page(
    "pages/1_성분_사전.py",
    title="성분 사전",
    icon="📘",
)

category_page = st.Page(
    "pages/2_약_종류.py",
    title="약 종류",
    icon="🗂️",
)

nearby_page = st.Page(
    "pages/3_근처_병원_약국.py",
    title="근처 병원·약국",
    icon="📍",
)

animal_page = st.Page(
    "pages/4_동물_건강.py",
    title="동물 건강",
    icon="🐾",
)

navigation = st.navigation(
    [
        home,
        ingredient_page,
        category_page,
        nearby_page,
        animal_page,
    ],
    position="sidebar",
)

navigation.run()
