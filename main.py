import base64
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st

from drug_data_tools import load_data
from drug_data_tools import load_condition_data
from drug_data_tools import get_selected_drugs
from drug_data_tools import find_duplicates
from drug_data_tools import search_drugs
from drug_data_tools import search_conditions
from drug_data_tools import search_ingredient
from drug_data_tools import split_ingredients


# ==========================================
# 1. 앱 기본 설정
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="MyMedi Care",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================
# 2. CSS 디자인 불러오기
# ==========================================

css_path = BASE_DIR / "style.css"

if css_path.exists():
    st.markdown(
        f"<style>{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


# ==========================================
# 3. 캐릭터 이미지 불러오기
# ==========================================

@st.cache_data(show_spinner=False)
def encode_image(relative_path):
    path = BASE_DIR / relative_path

    if not path.is_file():
        return ""

    return base64.b64encode(
        path.read_bytes()
    ).decode("ascii")


def card_art(name):
    encoded = encode_image(
        f"assets/card_{name}.png"
    )

    if not encoded:
        return ""

    return (
        '<img class="mc-card-art" '
        f'src="data:image/png;base64,{encoded}" '
        'alt="서비스 안내 캐릭터">'
    )


# ==========================================
# 4. 기능 선택
# ==========================================

def choose_tool(tool):
    st.session_state["home_tool"] = tool


def drug_list(data):
    return sorted(
        data["제품명"].dropna().unique().tolist()
    )


# ==========================================
# 5. 메인 홈페이지
# ==========================================

def home_page():

    # 데이터 불러오기
    try:
        drug_data, ingredient_data = load_data()
        condition_data = load_condition_data()

    except (
        FileNotFoundError,
        KeyError,
        ValueError,
    ) as error:

        st.error(
            "데이터 파일을 확인해 주세요. "
            "CSV 파일은 main.py와 같은 폴더에 있어야 합니다."
        )
        st.code(str(error))
        st.stop()

    # 사용자 저장 목록
    if "my_drugs" not in st.session_state:
        st.session_state.my_drugs = []

    if "my_conditions" not in st.session_state:
        st.session_state.my_conditions = []

    if "home_tool" not in st.session_state:
        st.session_state.home_tool = "나의 약"

    # ======================================
    # 5-1. 메인 배너
    # ======================================

    art = encode_image("assets/hero.png")

    art_html = (
        f'<img src="data:image/png;base64,{art}" '
        'alt="사람과 강아지, 고양이">'
        if art else ""
    )

    st.markdown(
        dedent(
            f"""
            <section class="mc-hero">
              <div class="mc-hero-copy">

                <div class="mc-kicker">
                  YOUR HEALTH COMPANION
                </div>

                <h1>
                  건강한 오늘이<br>
                  더 좋은 내일을 만듭니다.<br>
                  <em>MyMedi Care</em>
                </h1>

                <p>
                  나와 우리 가족, 반려동물까지.<br>
                  의약품 정보와 건강 기록을
                  한곳에서 관리하세요.
                </p>

                <a class="mc-cta"
                   href="#my-health-tools">
                  건강 관리 시작하기 →
                </a>

              </div>

              {art_html}

            </section>
            """
        ),
        unsafe_allow_html=True,
    )

    # ======================================
    # 5-2. 서비스 카드
    # ======================================

    st.markdown(
        '<div class="mc-section-tag">'
        'MAIN SERVICES'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="mc-section-head">'
        '필요한 서비스를 간편하게'
        '</div>',
        unsafe_allow_html=True,
    )

    a, b, c, d = st.columns(4, gap="medium")

    # 나의 약
    with a:
        with st.container(border=True):

            st.markdown(
                '<div class="mc-feature-head">'
                '<div class="mc-feature-icon mc-icon-mint">'
                '💊'
                '</div>'
                + card_art("my_drugs")
                + '</div>'
                '<div class="mc-card-title">'
                '나의 약'
                '</div>'
                '<div class="mc-card-text">'
                '복용 중인 약을 추가하고 목록을 관리해요.'
                '</div>',
                unsafe_allow_html=True,
            )

            st.button(
                "나의 약 열기 →",
                key="open_my_drugs",
                on_click=choose_tool,
                args=("나의 약",),
                use_container_width=True,
            )

    # 성분 분석
    with b:
        with st.container(border=True):

            st.markdown(
                '<div class="mc-feature-head">'
                '<div class="mc-feature-icon mc-icon-blue">'
                '🧪'
                '</div>'
                + card_art("compare")
                + '</div>'
                '<div class="mc-card-title">'
                '성분 분석'
                '</div>'
                '<div class="mc-card-text">'
                '최대 5개 의약품의 성분을 비교해요.'
                '</div>',
                unsafe_allow_html=True,
            )

            st.button(
                "성분 분석 열기 →",
                key="open_compare",
                on_click=choose_tool,
                args=("성분 분석",),
                use_container_width=True,
            )

    # 나의 질병
    with c:
        with st.container(border=True):

            st.markdown(
                '<div class="mc-feature-head">'
                '<div class="mc-feature-icon mc-icon-peach">'
                '📋'
                '</div>'
                + card_art("conditions")
                + '</div>'
                '<div class="mc-card-title">'
                '나의 질병'
                '</div>'
                '<div class="mc-card-text">'
                '질병과 증상을 선택하고 기록해요.'
                '</div>',
                unsafe_allow_html=True,
            )

            st.button(
                "나의 질병 열기 →",
                key="open_conditions",
                on_click=choose_tool,
                args=("나의 질병",),
                use_container_width=True,
            )

    # 동물 건강
    with d:
        with st.container(border=True):

            st.markdown(
                '<div class="mc-feature-head">'
                '<div class="mc-feature-icon mc-icon-violet">'
                '🐾'
                '</div>'
                + card_art("animals")
                + '</div>'
                '<div class="mc-card-title">'
                '동물 건강'
                '</div>'
                '<div class="mc-card-text">'
                '동물 약·성분·동물병원을 찾아봐요.'
                '</div>',
                unsafe_allow_html=True,
            )

            st.page_link(
                animal_page,
                label="동물 건강 열기 →",
                use_container_width=True,
            )

    # ======================================
    # 5-3. 빠른 검색
    # ======================================

    st.markdown(
        '<div class="mc-section-tag">'
        'EXPLORE MORE'
        '</div>',
        unsafe_allow_html=True,
    )

    left, center, right = st.columns(
        [1.25, 1, 1],
        gap="medium",
    )

    with left:
        with st.container(border=True):

            st.markdown("#### 🔎 빠른 검색")

            query = st.text_input(
                "제품명·성분·질병 검색",
                placeholder=(
                    "예: 타이레놀, "
                    "아세트아미노펜, 비염"
                ),
                key="mc_global_search",
            )

            if query.strip():

                drugs = search_drugs(
                    drug_data,
                    query,
                )

                illnesses = search_conditions(
                    condition_data,
                    query,
                )

                ingredients = search_ingredient(
                    ingredient_data,
                    drug_data,
                    query,
                )

                if not drugs.empty:

                    st.caption(
                        f"관련 의약품 {len(drugs)}개"
                    )

                    st.dataframe(
                        drugs[
                            [
                                "제품명",
                                "카테고리",
                                "성분",
                            ]
                        ].head(8),
                        hide_index=True,
                        use_container_width=True,
                    )

                if not ingredients.empty:

                    st.caption(
                        f"관련 성분 {len(ingredients)}개"
                    )

                    st.dataframe(
                        ingredients[
                            [
                                "성분명",
                                "분류",
                            ]
                        ].head(8),
                        hide_index=True,
                        use_container_width=True,
                    )

                if not illnesses.empty:

                    st.caption(
                        f"관련 질병·증상 {len(illnesses)}개"
                    )

                    st.dataframe(
                        illnesses[
                            [
                                "질병명",
                                "분류",
                            ]
                        ].head(8),
                        hide_index=True,
                        use_container_width=True,
                    )

                if (
                    drugs.empty
                    and ingredients.empty
                    and illnesses.empty
                ):

                    st.info(
                        "등록된 데이터에서 "
                        "검색 결과를 찾지 못했습니다."
                    )

            st.page_link(
                ingredient_page,
                label="📘 성분 사전 전체 보기",
            )

            st.page_link(
                category_page,
                label="🗂️ 약 종류 전체 보기",
            )

    # 건강 정보
    with center:
        with st.container(border=True):

            st.markdown(
                "#### 🌿 오늘의 건강 습관"
            )

            st.markdown(
                "**약을 복용하기 전, 이름과 성분을 "
                "한 번 더 확인해 보세요.**"
            )

            st.markdown(
                "<p class='mc-note'>"
                "서로 다른 제품이라도 같은 성분이 "
                "포함될 수 있습니다. "
                "성분 중복 결과만으로 병용 안전성을 "
                "판단할 수는 없습니다."
                "</p>",
                unsafe_allow_html=True,
            )

            st.page_link(
                nearby_page,
                label="📍 근처 병원·약국 찾기",
            )

    # 안내
    with right:
        with st.container(border=True):

            st.markdown("#### 📢 이용 안내")

            st.write(
                "✓ 약물·성분 목록은 참고용 데이터입니다."
            )

            st.write(
                "✓ 나의 약과 질병은 현재 세션에만 저장됩니다."
            )

            st.write(
                "✓ 동물용 약의 사용은 수의사와 상담하세요."
            )

            st.caption(
                "질병 진단이나 처방·복약 결정에는 "
                "이용할 수 없습니다."
            )

    # ======================================
    # 6. 기존 건강 관리 기능
    # ======================================

    st.markdown(
        '<div class="mc-tools-anchor" '
        'id="my-health-tools"></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="mc-section-tag">'
        'MY HEALTH TOOLS'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="mc-section-head">'
        '나의 건강 관리'
        '</div>',
        unsafe_allow_html=True,
    )

    selected = st.radio(
        "기능 선택",
        [
            "나의 약",
            "성분 분석",
            "나의 질병",
        ],
        horizontal=True,
        key="home_tool",
        label_visibility="collapsed",
    )

    # ======================================
    # 6-1. 나의 약
    # ======================================

    if selected == "나의 약":

        st.subheader("💊 나의 약")

        st.caption(
            "약 이름 또는 성분으로 찾아 "
            "선택한 약을 관리할 수 있습니다."
        )

        keyword = st.text_input(
            "약 검색",
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
                "약 이름이나 성분을 입력하여 "
                "검색해 주세요."
            )

        st.markdown("##### 현재 나의 약")

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

            remove = st.selectbox(
                "삭제할 약 선택",
                st.session_state.my_drugs,
                key="remove_drug_select",
            )

            ca, cb = st.columns(2)

            with ca:

                if st.button(
                    "선택한 약 삭제",
                    key="remove_drug_button",
                    use_container_width=True,
                ):

                    st.session_state.my_drugs.remove(
                        remove
                    )

                    st.rerun()

            with cb:

                if st.button(
                    "나의 약 전체 삭제",
                    key="clear_my_drugs_button",
                    use_container_width=True,
                ):

                    st.session_state.my_drugs = []

                    st.rerun()

        else:

            st.write(
                "아직 추가한 약이 없습니다."
            )

        st.caption(
            "나의 약은 현재 브라우저 세션에만 "
            "임시로 저장됩니다."
        )

    # ======================================
    # 6-2. 성분 분석
    # ======================================

    elif selected == "성분 분석":

        st.subheader("🧪 성분 분석")

        st.caption(
            "서로 다른 제품의 성분을 비교합니다. "
            "2개 이상 5개 이하를 선택해 주세요."
        )

        names = st.multiselect(
            "비교할 약 선택",
            options=drug_list(drug_data),
            max_selections=5,
            key="compare_drug_names",
        )

        st.caption(
            f"선택한 제품: {len(names)}개 / 최대 5개"
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

            st.session_state.compare_requested = True

        if st.session_state.get(
            "compare_requested"
        ):

            if len(names) < 2:

                st.warning(
                    "2개 이상의 의약품을 선택해 주세요."
                )

            else:

                chosen = get_selected_drugs(
                    drug_data,
                    names,
                )

                duplicates, ing_map = find_duplicates(
                    chosen
                )

                all_names = sorted(
                    ing_map.keys()
                )

                ca, cb, cc = st.columns(3)

                ca.metric(
                    "비교 제품 수",
                    len(names),
                )

                cb.metric(
                    "전체 고유 성분",
                    len(all_names),
                )

                cc.metric(
                    "중복 성분",
                    len(duplicates),
                )

                st.markdown(
                    "##### 중복 성분"
                )

                if duplicates:

                    duplicate_rows = [
                        {
                            "중복 성분": ing,
                            "포함 제품 수": len(products),
                            "포함 제품": ", ".join(products),
                        }
                        for ing, products
                        in sorted(duplicates.items())
                    ]

                    st.dataframe(
                        pd.DataFrame(duplicate_rows),
                        hide_index=True,
                        use_container_width=True,
                    )

                else:

                    st.success(
                        "선택한 제품 사이에 "
                        "일치하는 성분명이 없습니다."
                    )

                per_drug = {
                    row["제품명"]: set(
                        split_ingredients(
                            row["성분"]
                        )
                    )
                    for _, row in chosen.iterrows()
                }

                rows = [
                    {
                        "성분명": ing,
                        **{
                            nm: (
                                "✓"
                                if ing in per_drug.get(
                                    nm, set()
                                )
                                else ""
                            )
                            for nm in names
                        },
                    }
                    for ing in all_names
                ]

                only_duplicate = st.checkbox(
                    "중복 성분만 보기",
                    key="show_only_duplicates",
                )

                if only_duplicate:

                    rows = [
                        row
                        for row in rows
                        if row["성분명"] in duplicates
                    ]

                st.markdown(
                    "##### 제품별 성분 비교표"
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
                    "성분명이 같다는 것은 중복 가능성이 "
                    "있다는 뜻이며, 함께 복용 가능한지에 "
                    "대한 의학적 판단은 아닙니다."
                )

    # ======================================
    # 6-3. 나의 질병
    # ======================================

    else:

        st.subheader("📋 나의 질병")

        st.caption(
            "질병과 증상을 기록하는 기능이며, "
            "진단 기능은 아닙니다."
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

                st.info(
                    "검색 결과가 없습니다."
                )

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
                    "추가할 항목 선택",
                    result["질병명"].tolist(),
                    key="selected_condition",
                )

                if st.button(
                    "나의 질병에 추가",
                    type="primary",
                    key="add_condition_button",
                ):

                    if (
                        name
                        in st.session_state.my_conditions
                    ):

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
                f"등록된 {len(condition_data)}개 "
                "질병·증상 항목에서 검색해 보세요."
            )

        st.markdown(
            "##### 현재 나의 질병"
        )

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

            remove = st.selectbox(
                "삭제할 항목 선택",
                st.session_state.my_conditions,
                key="remove_condition_select",
            )

            ca, cb = st.columns(2)

            with ca:

                if st.button(
                    "선택한 항목 삭제",
                    key="remove_condition_button",
                    use_container_width=True,
                ):

                    st.session_state.my_conditions.remove(
                        remove
                    )

                    st.rerun()

            with cb:

                if st.button(
                    "나의 질병 전체 삭제",
                    key="clear_condition_button",
                    use_container_width=True,
                ):

                    st.session_state.my_conditions = []

                    st.rerun()

        else:

            st.write(
                "아직 선택한 항목이 없습니다."
            )

        st.warning(
            "이 기능은 개인 기록을 위한 것으로, "
            "질병을 진단하거나 적절한 약을 결정하지 않습니다."
        )

    # ======================================
    # 하단 안내
    # ======================================

    st.markdown(
        '<div class="mc-footer">'
        'MyMedi Care · Educational prototype · '
        '의약품 정보는 참고용입니다.'
        '</div>',
        unsafe_allow_html=True,
    )


# ==========================================
# 7. 왼쪽 메뉴 페이지 연결
# ==========================================

home = st.Page(
    home_page,
    title="홈",
    icon="🏠",
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


# ==========================================
# 8. 사이드바 구성
# ==========================================

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

sidebar_img = encode_image(
    "assets/mascot.png"
)

if sidebar_img:

    st.sidebar.markdown(
        '<div class="mc-sidebar-brand">'
        f'<img src="data:image/png;base64,{sidebar_img}" '
        'alt="MyMedi Care 캐릭터">'
        '<strong>건강한 하루, 함께해요!</strong>'
        '<span>나와 우리 가족의 건강 파트너</span>'
        '</div>',
        unsafe_allow_html=True,
    )


# ==========================================
# 9. 선택한 페이지 실행
# ==========================================

navigation.run()
