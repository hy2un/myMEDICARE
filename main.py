import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="MyMed Care",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


@st.cache_data
def load_data():
    """CSV 파일에서 의약품 데이터와 성분 사전 데이터를 불러온다."""
    drug_data = pd.read_csv(DATA_DIR / "drug_data.csv")
    ingredient_data = pd.read_csv(DATA_DIR / "ingredient_data.csv")

    for col in ["제품명", "제조사", "카테고리", "성분"]:
        drug_data[col] = drug_data[col].astype(str).str.strip()

    for col in ["성분명", "분류", "설명"]:
        ingredient_data[col] = ingredient_data[col].astype(str).str.strip()

    return drug_data, ingredient_data


def split_ingredients(ingredient_text):
    """'|'로 구분된 성분 문자열을 리스트로 변환한다."""
    return [
        ingredient.strip()
        for ingredient in str(ingredient_text).split("|")
        if ingredient.strip()
    ]


def get_selected_drugs(drug_data, selected_drug_names):
    """사용자가 선택한 제품만 추출한다."""
    return drug_data[
        drug_data["제품명"].isin(selected_drug_names)
    ].copy()


def find_duplicates(selected_drugs):
    """
    선택된 여러 약의 성분을 비교하여
    2개 이상의 제품에 포함된 성분만 찾는다.
    """
    ingredient_map = {}

    for _, row in selected_drugs.iterrows():
        drug_name = row["제품명"]

        for ingredient in split_ingredients(row["성분"]):
            ingredient_map.setdefault(ingredient, set()).add(drug_name)

    duplicates = {
        ingredient: sorted(products)
        for ingredient, products in ingredient_map.items()
        if len(products) >= 2
    }

    return duplicates, ingredient_map


def search_ingredient(ingredient_data, drug_data, keyword):
    """성분명 또는 분류에서 검색어를 찾아 결과를 반환한다."""
    keyword = keyword.strip()

    if not keyword:
        return pd.DataFrame()

    mask = (
        ingredient_data["성분명"].str.contains(
            keyword, case=False, na=False, regex=False
        )
        | ingredient_data["분류"].str.contains(
            keyword, case=False, na=False, regex=False
        )
    )

    result = ingredient_data[mask].copy()

    if result.empty:
        return result

    included_products = []

    for ingredient_name in result["성분명"]:
        products = []

        for _, drug in drug_data.iterrows():
            if ingredient_name in split_ingredients(drug["성분"]):
                products.append(drug["제품명"])

        included_products.append(", ".join(products) if products else "-")

    result["포함 제품"] = included_products

    return result[["성분명", "분류", "설명", "포함 제품"]]


def filter_drugs(drug_data, category):
    """선택한 약 종류에 해당하는 제품만 반환한다."""
    return drug_data[
        drug_data["카테고리"] == category
    ].copy()


def count_unique_ingredients(selected_drugs):
    """선택한 약 전체에 들어 있는 고유 성분 개수를 센다."""
    ingredients = set()

    for ingredient_text in selected_drugs["성분"]:
        ingredients.update(split_ingredients(ingredient_text))

    return len(ingredients)


st.markdown(
    """
    <style>
    .block-container {
        max-width: 1350px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    .title-box {
        border: 1px solid #e6e9ef;
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1.2rem;
        background: white;
    }

    .title-box h1 {
        margin: 0;
        font-size: 2rem;
    }

    .title-box p {
        margin: 0.45rem 0 0 0;
        color: #667085;
    }

    .result-box {
        border: 1px solid #e6e9ef;
        border-radius: 12px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.7rem;
        background: white;
    }

    .drug-card {
        border: 1px solid #e6e9ef;
        border-radius: 14px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        background: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def page_title(title, description):
    st.markdown(
        f"""
        <div class="title-box">
            <h1>{title}</h1>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


drug_data, ingredient_data = load_data()


with st.sidebar:
    st.title("💊 MyMed Care")
    st.caption("내 약 성분 중복 확인 서비스")

    page = st.radio(
        "메뉴",
        ["내 약", "성분 사전", "약 종류"],
        index=0,
    )

    st.divider()

    st.markdown(
        """
        **핵심 기능**
        - 여러 약 선택
        - 중복 성분 분석
        - 성분 사전 검색
        - 약 종류별 조회
        """
    )

    st.divider()

    st.caption(
        "교육용 수행평가 프로젝트입니다. "
        "실제 복용 여부나 병용 가능성은 의사·약사와 확인하세요."
    )


if page == "내 약":
    page_title(
        "내 약",
        "확인할 약을 2개 이상 선택하면 공통으로 들어 있는 성분을 찾아줍니다.",
    )

    selected_names = st.multiselect(
        "확인할 약을 선택하세요.",
        options=drug_data["제품명"].tolist(),
        placeholder="2개 이상의 약을 선택하세요.",
    )

    selected_drugs = get_selected_drugs(
        drug_data, selected_names
    )

    selected_count = len(selected_drugs)
    unique_count = (
        count_unique_ingredients(selected_drugs)
        if selected_count > 0
        else 0
    )

    if selected_count >= 2:
        current_duplicates, _ = find_duplicates(
            selected_drugs
        )
        duplicate_count = len(current_duplicates)
    else:
        duplicate_count = 0

    col1, col2, col3 = st.columns(3)
    col1.metric("선택한 약 수", selected_count)
    col2.metric("고유 성분 수", unique_count)
    col3.metric("중복 성분 수", duplicate_count)

    st.subheader("선택한 제품")

    if selected_drugs.empty:
        st.info("아직 선택한 약이 없습니다.")
    else:
        st.dataframe(
            selected_drugs[
                ["제품명", "제조사", "카테고리"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    if st.button(
        "중복 성분 분석",
        type="primary",
        use_container_width=True,
    ):
        if len(selected_names) <= 1:
            st.warning("2개 이상의 약을 선택해 주세요.")

        else:
            duplicates, ingredient_map = (
                find_duplicates(selected_drugs)
            )

            st.subheader("분석 결과")

            if not duplicates:
                st.success(
                    "선택한 제품 사이에서 "
                    "중복 성분이 발견되지 않았습니다."
                )
            else:
                st.warning(
                    f"중복 성분 {len(duplicates)}개가 발견되었습니다."
                )

                for ingredient, products in duplicates.items():
                    st.markdown(
                        f"""
                        <div class="result-box">
                            <b>⚠️ {ingredient}</b><br>
                            포함 제품: {" · ".join(products)}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            with st.expander("전체 성분과 포함 제품 보기"):
                rows = []

                for ingredient, products in sorted(
                    ingredient_map.items()
                ):
                    rows.append(
                        {
                            "성분명": ingredient,
                            "포함 제품 수": len(products),
                            "포함 제품": ", ".join(sorted(products)),
                        }
                    )

                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )

    st.info(
        "이 앱은 같은 성분이 여러 제품에 포함되어 있는지만 비교합니다. "
        "실제 병용 가능 여부나 복용량은 판단하지 않습니다."
    )


elif page == "성분 사전":
    page_title(
        "성분 사전",
        "성분명 또는 성분 계열을 검색해 설명과 포함 제품을 확인합니다.",
    )

    with st.form("ingredient_search_form"):
        keyword = st.text_input(
            "검색어",
            placeholder="예: 아세트아미노펜 / 항히스타민 / 진해",
        )

        search_button = st.form_submit_button(
            "검색",
            type="primary",
            use_container_width=True,
        )

    if search_button:
        if not keyword.strip():
            st.warning("검색어를 입력해 주세요.")

        else:
            result = search_ingredient(
                ingredient_data,
                drug_data,
                keyword,
            )

            if result.empty:
                st.info("검색 결과가 없습니다.")

            else:
                st.success(
                    f"{len(result)}개의 성분을 찾았습니다."
                )

                st.dataframe(
                    result,
                    use_container_width=True,
                    hide_index=True,
                )

    st.subheader("전체 성분 목록")

    st.dataframe(
        ingredient_data,
        use_container_width=True,
        hide_index=True,
    )


else:
    page_title(
        "약 종류",
        "카테고리를 선택해 준비된 의약품 목록을 조회합니다.",
    )

    categories = sorted(
        drug_data["카테고리"]
        .dropna()
        .unique()
        .tolist()
    )

    category = st.selectbox(
        "약 종류 선택",
        categories,
    )

    if st.button(
        "조회",
        type="primary",
        use_container_width=True,
    ):
        filtered = filter_drugs(
            drug_data,
            category,
        )

        st.subheader(f"{category} 제품")

        if filtered.empty:
            st.info("해당 카테고리의 제품이 없습니다.")

        else:
            for _, row in filtered.iterrows():
                ingredients = " · ".join(
                    split_ingredients(row["성분"])
                )

                st.markdown(
                    f"""
                    <div class="drug-card">
                        <b>{row["제품명"]}</b><br>
                        제조사: {row["제조사"]}<br>
                        주요 성분: {ingredients}<br>
                        샘플 추천 지수: {int(row["샘플추천지수"])} / 100
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.caption(
            "샘플 추천 지수는 수행평가 화면 구성을 위한 예시값이며 "
            "실제 의약품의 효과·안전성 우열을 의미하지 않습니다."
        )
