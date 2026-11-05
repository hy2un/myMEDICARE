"""My MediCare 홈과 사이드바: 나의 약·성분 분석·나의 질병."""
from pathlib import Path

import pandas as pd
import streamlit as st
from drug_data_tools import (
    load_data, load_condition_data, search_drugs, search_conditions,
    get_selected_drugs, find_duplicates, split_ingredients,
)

st.set_page_config(
    page_title="My MediCare", page_icon="💊", layout="wide",
    initial_sidebar_state="expanded",
)

# 홈 화면의 초록색 디자인
st.markdown("""
<style>
.stApp {background: #fbfdfc;}
h1,h2,h3 {color: #193d34 !important;letter-spacing:-.025em;}
.st-key-home_hero {background:#eaf7ef;border:1px solid #d5eadf;
  border-radius:22px;padding:22px 25px;margin-bottom:16px;}
.st-key-home_hero img {max-height:260px;object-fit:contain;}
.stTabs [data-baseweb="tab-list"] {gap:18px;border-bottom:1px solid #dcece3;}
.stTabs [data-baseweb="tab"] {color:#52665b !important;font-weight:700;
  padding:10px 3px 12px;}
.stTabs [data-baseweb="tab"]:hover,
.stTabs [aria-selected="true"] {color:#137f62 !important;}
.stTabs [data-baseweb="tab-highlight"] {background:#137f62 !important;
  height:3px !important;border-radius:3px !important;}
.stButton > button, .stFormSubmitButton > button {border-radius:14px !important;
  font-weight:700 !important;}
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {background:#137f62 !important;
  border-color:#137f62 !important;color:#fff !important;}
.stButton > button[kind="primary"]:hover {background:#0f6b53 !important;}
.stTextInput input, div[data-baseweb="select"]>div {border-radius:13px !important;}
div[data-testid="stMetric"] {background:#f0faf4;border:1px solid #dcece3;
  border-radius:16px;padding:10px 14px;}
div[data-testid="stAlert"] {border-radius:17px !important;}
div[data-testid="stDataFrame"] {border-radius:14px;overflow:hidden;}
@media(max-width:700px) {.st-key-home_hero {padding:14px;}}
</style>
""", unsafe_allow_html=True)

ROOT = Path(__file__).resolve().parent


def home_page():
    """등록·검색·성분 비교·질병 기록 기능을 제공하는 메인 페이지."""
    try:
        drugs, _ = load_data()
        conditions = load_condition_data()
    except (OSError, ValueError, KeyError, pd.errors.ParserError) as error:
        st.error(f"CSV 파일을 확인해 주세요: {error}")
        st.stop()

    st.session_state.setdefault("my_drugs", [])
    st.session_state.setdefault("my_conditions", [])

    with st.container(key="home_hero"):
        left, right = st.columns([1.25, 1], vertical_alignment="center")
        with left:
            st.title("My MediCare")
            st.subheader("건강한 오늘을 함께해요")
            st.caption("나의 약·성분·질병·증상을 한곳에서 확인하세요.")
        with right:
            banner = ROOT / "hero_characters.png"
            if banner.is_file():
                st.image(str(banner), use_container_width=True)

    tab_drug, tab_compare, tab_disease = st.tabs(
        ["💊 나의 약", "🧪 성분 분석", "📋 나의 질병"]
    )

    # 나의 약 등록·삭제
    with tab_drug:
        st.subheader("나의 약 관리")
        keyword = st.text_input(
            "약 이름·성분 검색",
            placeholder="예: 타이레놀, 아세트아미노펜",
            key="home_drug_query",
        )
        if keyword.strip():
            found = search_drugs(drugs, keyword)
            if found.empty:
                st.info("검색 결과가 없습니다. 다른 이름 또는 성분을 입력해 주세요.")
            else:
                st.dataframe(
                    found[["제품명", "제조사", "카테고리", "성분"]],
                    hide_index=True, use_container_width=True,
                )
                choice = st.selectbox(
                    "등록할 약 선택", found["제품명"].tolist(),
                    key="home_add_drug_select",
                )
                if st.button(
                    "나의 약에 추가", type="primary",
                    key="home_add_drug_btn",
                ):
                    if choice not in st.session_state.my_drugs:
                        st.session_state.my_drugs.append(choice)
                        st.rerun()
                    st.info("이미 등록된 약입니다.")

        st.markdown("#### 현재 나의 약 목록")
        if st.session_state.my_drugs:
            selected = get_selected_drugs(
                drugs, st.session_state.my_drugs
            )
            st.dataframe(
                selected[["제품명", "제조사", "카테고리", "성분"]],
                hide_index=True, use_container_width=True,
            )
            remove = st.selectbox(
                "삭제할 약", st.session_state.my_drugs,
                key="home_remove_drug_select",
            )
            left, right = st.columns(2)
            if left.button("선택한 약 삭제", key="home_remove_drug_btn"):
                st.session_state.my_drugs.remove(remove)
                st.rerun()
            if right.button("전체 삭제", key="home_clear_drugs_btn"):
                st.session_state.my_drugs = []
                st.rerun()
        else:
            st.info("추가된 약이 없습니다.")

        st.caption("등록한 약 목록은 현재 브라우저 세션에만 저장됩니다.")

    # 최대 5개 의약품 성분 비교
    with tab_compare:
        st.subheader("의약품 성분 비교")
        names = st.multiselect(
            "비교할 의약품 (2~5개)",
            sorted(drugs["제품명"].dropna().unique().tolist()),
            max_selections=5,
            key="home_compare_names",
        )
        if len(names) < 2:
            st.info("두 개 이상의 제품을 선택해 주세요.")
        else:
            selected = get_selected_drugs(drugs, names)
            duplicates, ingredient_map = find_duplicates(selected)

            a, b, c = st.columns(3)
            a.metric("선택 제품", len(names))
            b.metric("고유 성분", len(ingredient_map))
            c.metric("중복 성분", len(duplicates))

            if duplicates:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "중복 성분": name,
                            "포함 제품": ", ".join(products),
                        }
                        for name, products in sorted(duplicates.items())
                    ]),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.success("성분명 기준으로 중복이 없습니다.")

            per_product = {
                row["제품명"]: set(split_ingredients(row["성분"]))
                for _, row in selected.iterrows()
            }

            only_duplicates = st.checkbox(
                "중복 성분만 보기",
                key="home_compare_only_duplicates",
            )
            rows = []
            for ingredient in sorted(ingredient_map):
                if only_duplicates and ingredient not in duplicates:
                    continue
                rows.append({
                    "성분명": ingredient,
                    **{
                        product: (
                            "✓"
                            if ingredient in per_product.get(product, set())
                            else ""
                        )
                        for product in names
                    }
                })

            st.dataframe(
                pd.DataFrame(rows, columns=["성분명"] + names),
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "성분명 중복 여부만 확인할 수 있습니다. "
                "실제 병용 안전성은 의료진에게 확인하세요."
            )

    # 질병·증상 검색 및 등록
    with tab_disease:
        st.subheader("나의 질병·증상")
        st.caption(
            f"총 {len(conditions)}개 질병·증상 가운데 "
            "원하는 항목을 검색·선택할 수 있습니다."
        )
        keyword = st.text_input(
            "질병명·증상·일상 표현 검색",
            placeholder="예: 감기, 당뇨, 허리디스크",
            key="home_dis_query",
        )
        category = st.selectbox(
            "질병·증상 분류",
            ["전체 분류"] + sorted(
                conditions["분류"].dropna().unique().tolist()
            ),
            key="home_dis_category",
        )

        matches = (
            search_conditions(conditions, keyword)
            if keyword.strip()
            else conditions.copy()
        )
        if category != "전체 분류":
            matches = matches[
                matches["분류"] == category
            ].copy()

        st.write(
            f"**조회 결과 {len(matches)}개 / "
            f"전체 {len(conditions)}개**"
        )

        if matches.empty:
            st.info("검색 결과가 없습니다.")
        else:
            st.dataframe(
                matches[["질병명", "분류"]],
                hide_index=True,
                use_container_width=True,
                height=320,
            )

        selected_names = st.multiselect(
            "나의 질병에 추가할 항목 선택",
            matches["질병명"].tolist(),
            key="home_dis_add_many",
        )

        if st.button(
            "선택한 질병·증상 추가",
            type="primary",
            key="home_dis_add_btn",
        ):
            if not selected_names:
                st.warning("추가할 질병·증상을 선택해 주세요.")
            else:
                before = len(st.session_state.my_conditions)
                st.session_state.my_conditions = list(
                    dict.fromkeys(
                        st.session_state.my_conditions + selected_names
                    )
                )
                added = len(st.session_state.my_conditions) - before
                st.success(f"새 항목 {added}개를 추가했습니다.")
                st.rerun()

        st.markdown("#### 현재 나의 질병 목록")
        if st.session_state.my_conditions:
            registered = conditions[
                conditions["질병명"].isin(
                    st.session_state.my_conditions
                )
            ]
            st.dataframe(
                registered[["질병명", "분류"]],
                hide_index=True,
                use_container_width=True,
            )

            remove_names = st.multiselect(
                "삭제할 항목 선택",
                st.session_state.my_conditions,
                key="home_dis_remove_many",
            )
            left, right = st.columns(2)

            if left.button(
                "선택 항목 삭제",
                key="home_dis_remove_btn",
            ):
                if remove_names:
                    st.session_state.my_conditions = [
                        item
                        for item in st.session_state.my_conditions
                        if item not in remove_names
                    ]
                    st.rerun()
                st.warning("삭제할 항목을 선택해 주세요.")

            if right.button(
                "전체 삭제",
                key="home_dis_clear_btn",
            ):
                st.session_state.my_conditions = []
                st.rerun()
        else:
            st.info("아직 등록한 질병·증상이 없습니다.")

        st.caption(
            "질병·증상 기록은 진단이 아니며 "
            "현재 브라우저 세션에서만 유지됩니다."
        )


# 사이드바 페이지 연결
pages = [
    st.Page(home_page, title="My MediCare", icon="💊", default=True),
    st.Page("pages/1_성분_사전.py", title="성분 사전", icon="📘"),
    st.Page("pages/2_약_종류.py", title="약 종류", icon="🗂️"),
    st.Page("pages/3_근처_병원_약국.py", title="근처 병원·약국", icon="📍"),
    st.Page("pages/4_동물_건강.py", title="동물 건강", icon="🐾"),
    st.Page("pages/5_증상_AI_상담.py", title="증상 AI 상담", icon="💬"),
]

st.navigation(pages, position="sidebar").run()
