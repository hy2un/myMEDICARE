from pathlib import Path
import sys
import types

import pandas as pd
import streamlit as st

from drug_data_tools import (
    load_data,
    load_condition_data,
    search_drugs,
    search_conditions,
    get_selected_drugs,
    find_duplicates,
    split_ingredients,
)


# ==========================================
# 1. 앱 기본 설정
# ==========================================

st.set_page_config(
    page_title="MyMedi Care",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================
# 2. 공통 스타일
# ==========================================

try:
    from site_theme import apply_style

except ModuleNotFoundError as exc:

    if exc.name != "site_theme":
        raise

    def apply_style():

        st.markdown(
            """
            <style>
            .stApp {
                background: #fafcfb;
            }

            .st-key-home_hero {
                background: #eaf7ef;
                border-radius: 22px;
                border: 1px solid #d5eadf;
                padding: 20px;
            }

            .stButton button {
                border-radius: 13px;
            }

            .stButton button[kind="primary"] {
                background: #137d65;
                border-color: #137d65;
                color: white;
            }

            .stTabs [data-baseweb="tab"] {
                border-radius: 13px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    module = types.ModuleType("site_theme")
    module.apply_style = apply_style
    sys.modules["site_theme"] = module


apply_style()

ROOT = Path(__file__).resolve().parent


# ==========================================
# 3. 메인 페이지
# ==========================================

def home_page():

    try:
        drugs, _ = load_data()
        conditions = load_condition_data()

    except (
        FileNotFoundError,
        KeyError,
        ValueError,
    ) as exc:

        st.error(
            f"CSV 파일을 확인해 주세요: {exc}"
        )
        st.stop()

    st.session_state.setdefault(
        "my_drugs",
        [],
    )

    st.session_state.setdefault(
        "my_conditions",
        [],
    )


    # ======================================
    # 메인 배너
    # ======================================

    with st.container(key="home_hero"):

        left, right = st.columns(
            [1.25, 1],
            vertical_alignment="center",
        )

        with left:

            st.title("MyMedi Care")

            st.subheader(
                "건강한 오늘을 함께해요"
            )

            st.caption(
                "나의 약·성분·질병·증상을 "
                "한곳에서 확인하세요."
            )

        with right:

            picture = (
                ROOT / "hero_characters.png"
            )

            if picture.is_file():

                st.image(
                    str(picture),
                    use_container_width=True,
                )


    # ======================================
    # 메인 3개 탭
    # ======================================

    tab_drug, tab_compare, tab_disease = st.tabs(
        [
            "💊 나의 약",
            "🧪 성분 분석",
            "📋 나의 질병",
        ]
    )


    # ======================================
    # 4. 나의 약
    # ======================================

    with tab_drug:

        st.subheader("나의 약 관리")

        keyword = st.text_input(
            "약 이름·성분 검색",
            placeholder=(
                "예: 타이레놀, 아세트아미노펜"
            ),
            key="home_drug_query",
        )

        if keyword.strip():

            found = search_drugs(
                drugs,
                keyword,
            )

            if found.empty:

                st.info(
                    "검색 결과가 없습니다."
                )

            else:

                st.dataframe(
                    found[
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

                choice = st.selectbox(
                    "등록할 약 선택",
                    found["제품명"].tolist(),
                    key="home_add_drug_select",
                )

                if st.button(
                    "나의 약에 추가",
                    type="primary",
                    key="home_add_drug_btn",
                ):

                    if (
                        choice
                        not in st.session_state.my_drugs
                    ):

                        st.session_state.my_drugs.append(
                            choice
                        )

                        st.rerun()

                    else:

                        st.info(
                            "이미 등록된 약입니다."
                        )

        st.markdown(
            "#### 현재 나의 약 목록"
        )

        if st.session_state.my_drugs:

            chosen = get_selected_drugs(
                drugs,
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

            removal = st.selectbox(
                "삭제할 약",
                st.session_state.my_drugs,
                key="home_remove_drug_select",
            )

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "선택한 약 삭제",
                    key="home_remove_drug_btn",
                ):

                    st.session_state.my_drugs.remove(
                        removal
                    )

                    st.rerun()

            with c2:

                if st.button(
                    "전체 삭제",
                    key="home_clear_drugs_btn",
                ):

                    st.session_state.my_drugs = []

                    st.rerun()

        else:

            st.info(
                "추가된 약이 없습니다."
            )


    # ======================================
    # 5. 성분 분석
    # ======================================

    with tab_compare:

        st.subheader(
            "의약품 성분 비교"
        )

        names = st.multiselect(
            "비교할 의약품 (2~5개)",
            sorted(
                drugs["제품명"]
                .dropna()
                .unique()
                .tolist()
            ),
            max_selections=5,
            key="home_compare_names",
        )

        if len(names) < 2:

            st.info(
                "두 개 이상의 약을 선택해 주세요."
            )

        else:

            chosen = get_selected_drugs(
                drugs,
                names,
            )

            duplicates, ingredient_map = (
                find_duplicates(chosen)
            )

            k1, k2, k3 = st.columns(3)

            k1.metric(
                "선택 제품",
                len(names),
            )

            k2.metric(
                "고유 성분",
                len(ingredient_map),
            )

            k3.metric(
                "중복 성분",
                len(duplicates),
            )

            if duplicates:

                rows = []

                for ingredient, products in sorted(
                    duplicates.items()
                ):

                    rows.append(
                        {
                            "중복 성분": ingredient,
                            "포함 제품": ", ".join(
                                products
                            ),
                        }
                    )

                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.success(
                    "성분명 기준으로 중복이 없습니다."
                )

            by_drug = {}

            for _, row in chosen.iterrows():

                by_drug[row["제품명"]] = set(
                    split_ingredients(
                        row["성분"]
                    )
                )

            only_duplicates = st.checkbox(
                "중복 성분만 보기",
                key="home_compare_only_duplicates",
            )

            rows = []

            for ingredient in sorted(
                ingredient_map
            ):

                if (
                    only_duplicates
                    and ingredient not in duplicates
                ):
                    continue

                record = {
                    "성분명": ingredient
                }

                for name in names:

                    record[name] = (
                        "✓"
                        if ingredient in by_drug.get(
                            name,
                            set(),
                        )
                        else ""
                    )

                rows.append(record)

            st.dataframe(
                pd.DataFrame(
                    rows,
                    columns=["성분명"] + names,
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "성분명이 겹친다고 해서 "
                "병용 안전성을 판단할 수 있는 것은 아닙니다."
            )


    # ======================================
    # 6. 나의 질병: 355개 전체 조회
    # ======================================

    with tab_disease:

        st.subheader(
            "나의 질병·증상"
        )

        st.caption(
            f"등록된 질병·증상 전체 "
            f"{len(conditions)}개를 "
            "검색하거나 직접 선택할 수 있습니다."
        )

        keyword = st.text_input(
            "질병명·증상·일상적인 표현 검색 "
            "(비우면 전체 보기)",
            placeholder=(
                "예: 감기, 당뇨, 허리디스크, 이석증"
            ),
            key="home_dis_query",
        )

        categories = sorted(
            conditions["분류"]
            .dropna()
            .unique()
            .tolist()
        )

        category = st.selectbox(
            "질병·증상 분류",
            ["전체 분류"] + categories,
            key="home_dis_category",
        )

        if keyword.strip():

            matches = search_conditions(
                conditions,
                keyword,
            )

        else:

            matches = conditions.copy()

        if category != "전체 분류":

            matches = matches[
                matches["분류"] == category
            ].copy()

        st.write(
            f"**조회 결과: {len(matches)}개 "
            f"/ 전체 {len(conditions)}개**"
        )

        st.dataframe(
            matches[
                [
                    "질병명",
                    "분류",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            height=340,
        )

        # 여러 질병·증상 선택
        selected_names = st.multiselect(
            "나의 질병에 추가할 항목 선택 "
            "(여러 개 선택 가능)",
            options=matches[
                "질병명"
            ].tolist(),
            key="home_dis_add_many",
        )

        if st.button(
            "선택한 질병·증상 추가",
            type="primary",
            key="home_dis_add_btn",
        ):

            if not selected_names:

                st.warning(
                    "먼저 추가할 질병·증상을 "
                    "선택해 주세요."
                )

            else:

                before = len(
                    st.session_state.my_conditions
                )

                st.session_state.my_conditions = list(
                    dict.fromkeys(
                        st.session_state.my_conditions
                        + selected_names
                    )
                )

                added = (
                    len(st.session_state.my_conditions)
                    - before
                )

                st.success(
                    f"{added}개 항목을 추가했습니다."
                )

                st.rerun()

        st.markdown(
            "#### 현재 나의 질병 목록"
        )

        if st.session_state.my_conditions:

            registered = conditions[
                conditions["질병명"].isin(
                    st.session_state.my_conditions
                )
            ].copy()

            st.dataframe(
                registered[
                    [
                        "질병명",
                        "분류",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
            )

            delete_names = st.multiselect(
                "삭제할 질병·증상 선택",
                st.session_state.my_conditions,
                key="home_dis_remove_many",
            )

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "선택 항목 삭제",
                    key="home_dis_remove_btn",
                ):

                    if delete_names:

                        st.session_state.my_conditions = [
                            name
                            for name
                            in st.session_state.my_conditions
                            if name not in delete_names
                        ]

                        st.rerun()

                    else:

                        st.warning(
                            "삭제할 항목을 선택해 주세요."
                        )

            with c2:

                if st.button(
                    "전체 삭제",
                    key="home_dis_clear_btn",
                ):

                    st.session_state.my_conditions = []

                    st.rerun()

        else:

            st.info(
                "아직 등록한 질병·증상이 없습니다."
            )

        st.caption(
            "진단 기능이 아닌 개인 기록용 목록입니다. "
            "기록은 현재 세션에만 유지됩니다."
        )


# ==========================================
# 7. 전체 페이지 메뉴
# ==========================================

pages = [

    st.Page(
        home_page,
        title="MyMedi Care",
        icon="💊",
        default=True,
    ),

    st.Page(
        "pages/1_성분_사전.py",
        title="성분 사전",
        icon="📘",
    ),

    st.Page(
        "pages/2_약_종류.py",
        title="약 종류",
        icon="🗂️",
    ),

    st.Page(
        "pages/3_근처_병원_약국.py",
        title="근처 병원·약국",
        icon="📍",
    ),

    st.Page(
        "pages/4_동물_건강.py",
        title="동물 건강",
        icon="🐾",
    ),

    st.Page(
        "pages/5_증상_AI_상담.py",
        title="증상 AI 상담",
        icon="💬",
    ),
]


# ==========================================
# 8. 앱 실행
# ==========================================

navigation = st.navigation(
    pages,
    position="sidebar",
)

navigation.run()
