from pathlib import Path

import pandas as pd
import streamlit as st

from site_theme import apply_style

from drug_data_tools import load_data
from drug_data_tools import load_condition_data
from drug_data_tools import search_drugs
from drug_data_tools import search_conditions
from drug_data_tools import get_selected_drugs
from drug_data_tools import find_duplicates
from drug_data_tools import split_ingredients


# ==========================================
# 1. 앱 기본 설정
# ==========================================

st.set_page_config(
    page_title="MyMedi Care",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_style()

ROOT = Path(__file__).resolve().parent


# ==========================================
# 2. 메인 홈페이지
# ==========================================

def home_page():

    try:
        drugs, _ = load_data()
        conditions = load_condition_data()

    except (FileNotFoundError, ValueError, KeyError) as error:
        st.error(f"CSV 파일을 확인해 주세요: {error}")
        st.stop()

    if "my_drugs" not in st.session_state:
        st.session_state.my_drugs = []

    if "my_conditions" not in st.session_state:
        st.session_state.my_conditions = []


    # ======================================
    # 3. 홈페이지 디자인 배너
    # ======================================

    with st.container(key="home_hero"):

        left, right = st.columns([1.25, 1])

        with left:
            st.title("MyMedi Care")
            st.subheader("건강한 오늘을 함께해요")
            st.caption(
                "의약품 성분과 건강 기록을 "
                "한곳에서 확인하세요."
            )

        with right:
            picture = ROOT / "hero_characters.png"

            if picture.is_file():
                st.image(
                    str(picture),
                    use_container_width=True,
                )
            else:
                st.markdown("### 💊 🐶 🐱")


    # ======================================
    # 4. 기존 세 가지 탭
    # ======================================

    tab_drug, tab_compare, tab_condition = st.tabs(
        [
            "💊 나의 약",
            "🧪 성분 분석",
            "📋 나의 질병",
        ]
    )


    # ======================================
    # 첫 번째 탭: 나의 약
    # ======================================

    with tab_drug:

        st.subheader("나의 약 관리")

        keyword = st.text_input(
            "약 이름·성분 검색",
            placeholder="예: 타이레놀, 아세트아미노펜",
            key="my_drug_search",
        )

        if keyword.strip():

            result = search_drugs(
                drugs,
                keyword,
            )

            if result.empty:
                st.info("검색 결과가 없습니다.")

            else:
                st.dataframe(
                    result[
                        ["제품명", "제조사", "카테고리"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                new_drug = st.selectbox(
                    "추가할 약 선택",
                    result["제품명"].tolist(),
                    key="add_drug_name",
                )

                if st.button(
                    "나의 약에 추가",
                    type="primary",
                    key="add_drug",
                ):

                    if new_drug not in st.session_state.my_drugs:
                        st.session_state.my_drugs.append(
                            new_drug
                        )
                        st.rerun()

                    else:
                        st.info("이미 등록된 약입니다.")

        st.markdown("#### 현재 나의 약")

        if st.session_state.my_drugs:

            selected = get_selected_drugs(
                drugs,
                st.session_state.my_drugs,
            )

            st.dataframe(
                selected[
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

            delete = st.selectbox(
                "삭제할 약",
                st.session_state.my_drugs,
                key="remove_drug_name",
            )

            c1, c2 = st.columns(2)

            with c1:
                if st.button(
                    "선택한 약 삭제",
                    key="remove_drug",
                ):
                    st.session_state.my_drugs.remove(
                        delete
                    )
                    st.rerun()

            with c2:
                if st.button(
                    "전체 삭제",
                    key="clear_drugs",
                ):
                    st.session_state.my_drugs = []
                    st.rerun()

        else:
            st.info("추가한 약이 없습니다.")

        st.caption(
            "저장 정보는 현재 Streamlit 세션에만 유지됩니다."
        )


    # ======================================
    # 두 번째 탭: 성분 분석
    # ======================================

    with tab_compare:

        st.subheader("성분 비교")

        names = st.multiselect(
            "비교할 의약품 선택 (2~5개)",
            sorted(
                drugs["제품명"].dropna().unique().tolist()
            ),
            max_selections=5,
            key="compare_drugs",
        )

        if len(names) < 2:

            st.info(
                "비교할 약을 두 개 이상 선택해 주세요."
            )

        else:

            selected = get_selected_drugs(
                drugs,
                names,
            )

            duplicates, ingredient_map = find_duplicates(
                selected
            )

            u1, u2, u3 = st.columns(3)

            u1.metric("비교 제품", len(names))
            u2.metric("고유 성분", len(ingredient_map))
            u3.metric("중복 성분", len(duplicates))

            st.subheader("중복 성분")

            if duplicates:

                duplicate_rows = []

                for ingredient, products in sorted(
                    duplicates.items()
                ):
                    duplicate_rows.append(
                        {
                            "성분명": ingredient,
                            "포함 제품": ", ".join(products),
                        }
                    )

                st.dataframe(
                    pd.DataFrame(duplicate_rows),
                    hide_index=True,
                    use_container_width=True,
                )

            else:
                st.success(
                    "성분명 기준으로 일치하는 성분이 없습니다."
                )

            per_drug = {}

            for _, row in selected.iterrows():

                per_drug[row["제품명"]] = set(
                    split_ingredients(
                        row["성분"]
                    )
                )

            rows = []

            for ingredient in sorted(ingredient_map):

                item = {
                    "성분명": ingredient
                }

                for name in names:
                    item[name] = (
                        "✓"
                        if ingredient in per_drug.get(
                            name, set()
                        )
                        else ""
                    )

                rows.append(item)

            only_duplicates = st.checkbox(
                "중복 성분만 보기",
                key="only_duplicates",
            )

            if only_duplicates:
                rows = [
                    row
                    for row in rows
                    if row["성분명"] in duplicates
                ]

            st.subheader("제품별 성분 비교표")

            st.dataframe(
                pd.DataFrame(
                    rows,
                    columns=["성분명"] + names,
                ),
                hide_index=True,
                use_container_width=True,
            )

            st.caption(
                "성분명의 중복을 보여줄 뿐 "
                "병용 안전성을 판단하지 않습니다."
            )


    # ======================================
    # 세 번째 탭: 나의 질병
    # ======================================

    with tab_condition:

        st.subheader("나의 질병·증상")

        keyword = st.text_input(
            "질병·증상 검색",
            placeholder="예: 감기, 비염",
            key="my_condition_search",
        )

        if keyword.strip():

            result = search_conditions(
                conditions,
                keyword,
            )

            if result.empty:
                st.info("검색 결과가 없습니다.")

            else:

                st.dataframe(
                    result[
                        ["질병명", "분류"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )

                name = st.selectbox(
                    "추가할 항목",
                    result["질병명"].tolist(),
                    key="add_condition_name",
                )

                if st.button(
                    "나의 질병에 추가",
                    type="primary",
                    key="add_condition",
                ):

                    if name not in st.session_state.my_conditions:
                        st.session_state.my_conditions.append(
                            name
                        )
                        st.rerun()

                    else:
                        st.info(
                            "이미 추가된 항목입니다."
                        )

        st.markdown("#### 기록된 질병·증상")

        if st.session_state.my_conditions:

            selected = conditions[
                conditions["질병명"].isin(
                    st.session_state.my_conditions
                )
            ]

            st.dataframe(
                selected[
                    ["질병명", "분류"]
                ],
                hide_index=True,
                use_container_width=True,
            )

            delete = st.selectbox(
                "삭제할 항목",
                st.session_state.my_conditions,
                key="remove_condition_name",
            )

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    "선택 항목 삭제",
                    key="remove_condition",
                ):
                    st.session_state.my_conditions.remove(
                        delete
                    )
                    st.rerun()

            with c2:

                if st.button(
                    "전체 삭제",
                    key="clear_conditions",
                ):
                    st.session_state.my_conditions = []
                    st.rerun()

        else:
            st.info(
                "기록된 질병·증상이 없습니다."
            )

        st.caption(
            "질병·증상 기록은 진단 기능이 아닙니다."
        )


# ==========================================
# 5. 전체 페이지 등록
# ==========================================

# 메인 홈페이지
home = st.Page(
    home_page,
    title="MyMedi Care",
    icon="💊",
    default=True,
)

# 성분 사전
ingredient_page = st.Page(
    "pages/1_성분_사전.py",
    title="성분 사전",
    icon="📘",
)

# 약 종류
category_page = st.Page(
    "pages/2_약_종류.py",
    title="약 종류",
    icon="🗂️",
)

# 근처 병원·약국
nearby_page = st.Page(
    "pages/3_근처_병원_약국.py",
    title="근처 병원·약국",
    icon="📍",
)

# 동물 건강
animal_page = st.Page(
    "pages/4_동물_건강.py",
    title="동물 건강",
    icon="🐾",
)

# 증상 AI 상담 - 새로 추가
ai_page = st.Page(
    "pages/5_증상_AI_상담.py",
    title="증상 AI 상담",
    icon="💬",
)


# ==========================================
# 6. 왼쪽 메뉴 구성
# ==========================================

navigation = st.navigation(
    [
        home,
        ingredient_page,
        category_page,
        nearby_page,
        animal_page,
        ai_page,
    ],
    position="sidebar",
)


# ==========================================
# 7. 앱 실행
# ==========================================

navigation.run()
