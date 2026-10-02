import streamlit as st
import pandas as pd

from drug_data_tools import load_data
from drug_data_tools import load_condition_data
from drug_data_tools import get_selected_drugs
from drug_data_tools import find_duplicates
from drug_data_tools import search_drugs
from drug_data_tools import search_conditions
from drug_data_tools import split_ingredients

st.set_page_config(
    page_title="MyMedi Care",
    page_icon="💊",
    layout="wide",
)

def home_page():
    st.title("💊 MyMedi Care")
    st.caption(
        "나의 약을 관리하고, 최대 5개의 의약품 성분을 비교하며, "
        "나의 질병·증상을 선택할 수 있는 서비스"
    )

    try:
        drug_data, _ = load_data()
        condition_data = load_condition_data()
    except Exception as error:
        st.error("데이터 파일을 불러오지 못했습니다.")
        st.code(str(error))
        st.stop()

    if "my_drugs" not in st.session_state:
        st.session_state.my_drugs = []

    if "my_conditions" not in st.session_state:
        st.session_state.my_conditions = []

    tab_my_drugs, tab_compare, tab_conditions = st.tabs(
        ["나의 약", "성분 분석", "나의 질병"]
    )

    with tab_my_drugs:
        st.subheader("나의 약")
        st.caption(
            "약 이름을 검색한 뒤 원하는 제품을 선택해 나의 약에 추가하세요."
        )

        my_drug_keyword = st.text_input(
            "약 이름 검색",
            placeholder="예: 타이레놀, 게보린, 판콜",
            key="my_drug_search_keyword",
        )

        if my_drug_keyword.strip():
            search_result = search_drugs(drug_data, my_drug_keyword)

            if search_result.empty:
                st.info("검색 결과가 없습니다.")
            else:
                st.dataframe(
                    search_result[["제품명", "제조사", "카테고리"]],
                    use_container_width=True,
                    hide_index=True,
                )

                selected_search_drug = st.selectbox(
                    "추가할 약 선택",
                    options=search_result["제품명"].tolist(),
                    key="selected_search_drug",
                )

                if st.button(
                    "나의 약에 추가",
                    type="primary",
                    key="add_my_drug_button",
                ):
                    if selected_search_drug in st.session_state.my_drugs:
                        st.info("이미 나의 약에 추가된 제품입니다.")
                    else:
                        st.session_state.my_drugs.append(selected_search_drug)
                        st.rerun()
        else:
            st.info("약 이름을 입력하면 검색 결과가 표시됩니다.")

        st.divider()
        st.markdown("### 현재 나의 약")

        if st.session_state.my_drugs:
            selected_drugs = get_selected_drugs(
                drug_data,
                st.session_state.my_drugs,
            )

            st.dataframe(
                selected_drugs[["제품명", "제조사", "카테고리", "성분"]],
                use_container_width=True,
                hide_index=True,
            )

            remove_drug = st.selectbox(
                "삭제할 약 선택",
                options=st.session_state.my_drugs,
                key="remove_drug_select",
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "선택한 약 삭제",
                    key="remove_drug_button",
                    use_container_width=True,
                ):
                    st.session_state.my_drugs.remove(remove_drug)
                    st.rerun()

            with col2:
                if st.button(
                    "나의 약 전체 삭제",
                    key="clear_my_drugs_button",
                    use_container_width=True,
                ):
                    st.session_state.my_drugs = []
                    st.rerun()
        else:
            st.write("아직 나의 약에 추가된 제품이 없습니다.")

        st.info("나의 약은 현재 앱 세션 동안만 임시로 저장됩니다.")

    with tab_compare:
        st.subheader("성분 분석")
        st.caption(
            "비교할 의약품을 2개 이상, 최대 5개까지 선택해 "
            "공통 성분과 제품별 성분을 비교할 수 있습니다."
        )

        compare_names = st.multiselect(
            "비교할 약 선택",
            options=sorted(drug_data["제품명"].tolist()),
            max_selections=5,
            placeholder="비교할 약을 2~5개 선택하세요.",
            key="compare_drug_names",
        )

        st.caption(f"현재 {len(compare_names)}개 선택 / 최대 5개")

        if compare_names:
            compare_drugs = get_selected_drugs(
                drug_data,
                compare_names,
            )

            st.markdown("#### 선택한 제품")
            st.dataframe(
                compare_drugs[["제품명", "제조사", "카테고리"]],
                use_container_width=True,
                hide_index=True,
            )

        if st.button(
            "성분 비교하기",
            type="primary",
            key="compare_ingredients_button",
            use_container_width=True,
        ):
            if len(compare_names) < 2:
                st.warning("성분 비교를 위해 약을 2개 이상 선택해 주세요.")
            else:
                compare_drugs = get_selected_drugs(
                    drug_data,
                    compare_names,
                )

                duplicates, ingredient_map = find_duplicates(compare_drugs)
                unique_ingredients = sorted(ingredient_map.keys())

                metric1, metric2, metric3 = st.columns(3)
                metric1.metric("비교 제품 수", len(compare_names))
                metric2.metric("전체 고유 성분 수", len(unique_ingredients))
                metric3.metric("중복 성분 수", len(duplicates))

                st.markdown("### 중복 성분")

                if duplicates:
                    duplicate_rows = []

                    for ingredient, products in sorted(duplicates.items()):
                        duplicate_rows.append(
                            {
                                "중복 성분": ingredient,
                                "포함 제품 수": len(products),
                                "포함 제품": ", ".join(products),
                            }
                        )

                    st.dataframe(
                        pd.DataFrame(duplicate_rows),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.success(
                        "선택한 제품 사이에서 중복 성분이 발견되지 않았습니다."
                    )

                st.markdown("### 제품별 성분 비교표")

                drug_ingredient_sets = {}
                for _, row in compare_drugs.iterrows():
                    drug_ingredient_sets[row["제품명"]] = set(
                        split_ingredients(row["성분"])
                    )

                comparison_rows = []

                for ingredient in unique_ingredients:
                    row_data = {"성분명": ingredient}

                    for drug_name in compare_names:
                        row_data[drug_name] = (
                            "✓"
                            if ingredient
                            in drug_ingredient_sets.get(drug_name, set())
                            else ""
                        )

                    comparison_rows.append(row_data)

                comparison_df = pd.DataFrame(comparison_rows)

                only_duplicates = st.checkbox(
                    "중복 성분만 보기",
                    value=False,
                    key="show_only_duplicates",
                )

                if only_duplicates:
                    comparison_df = comparison_df[
                        comparison_df["성분명"].isin(duplicates.keys())
                    ]

                st.dataframe(
                    comparison_df,
                    use_container_width=True,
                    hide_index=True,
                )

                st.info(
                    "✓ 표시는 해당 제품에 그 성분이 포함되어 있다는 뜻입니다. "
                    "중복 성분 여부만 비교하며 실제 병용 가능 여부는 판단하지 않습니다."
                )

    with tab_conditions:
        st.subheader("나의 질병")
        st.caption(
            "질병이나 증상 이름을 검색한 뒤 원하는 항목을 선택해 추가하세요."
        )

        condition_keyword = st.text_input(
            "질병·증상 검색",
            placeholder="예: 감기, 독감, 생리통, 비염",
            key="condition_search_keyword",
        )

        if condition_keyword.strip():
            condition_result = search_conditions(
                condition_data,
                condition_keyword,
            )

            if condition_result.empty:
                st.info("검색 결과가 없습니다.")
            else:
                st.dataframe(
                    condition_result[["질병명", "분류"]],
                    use_container_width=True,
                    hide_index=True,
                )

                selected_condition = st.selectbox(
                    "추가할 질병·증상 선택",
                    options=condition_result["질병명"].tolist(),
                    key="selected_condition",
                )

                if st.button(
                    "나의 질병에 추가",
                    type="primary",
                    key="add_condition_button",
                ):
                    if selected_condition in st.session_state.my_conditions:
                        st.info("이미 추가된 항목입니다.")
                    else:
                        st.session_state.my_conditions.append(
                            selected_condition
                        )
                        st.rerun()
        else:
            st.info(
                f"현재 {len(condition_data)}개의 질병·증상 항목에서 검색할 수 있습니다."
            )

        st.divider()
        st.markdown("### 현재 나의 질병")

        if st.session_state.my_conditions:
            my_condition_rows = condition_data[
                condition_data["질병명"].isin(
                    st.session_state.my_conditions
                )
            ][["질병명", "분류"]]

            st.dataframe(
                my_condition_rows,
                use_container_width=True,
                hide_index=True,
            )

            remove_condition = st.selectbox(
                "삭제할 항목 선택",
                options=st.session_state.my_conditions,
                key="remove_condition_select",
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button(
                    "선택한 항목 삭제",
                    key="remove_condition_button",
                    use_container_width=True,
                ):
                    st.session_state.my_conditions.remove(remove_condition)
                    st.rerun()

            with col2:
                if st.button(
                    "나의 질병 전체 삭제",
                    key="clear_condition_button",
                    use_container_width=True,
                ):
                    st.session_state.my_conditions = []
                    st.rerun()
        else:
            st.write("아직 추가된 질병·증상 항목이 없습니다.")

        st.warning(
            "이 기능은 사용자가 알고 있는 질병·증상을 기록하기 위한 기능입니다. "
            "진단 기능이 아니며, 선택한 질병과 약의 복용 가능 여부를 자동으로 판단하지 않습니다."
        )

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

navigation = st.navigation(
    [
        home,
        ingredient_page,
        category_page,
        nearby_page,
    ],
    position="sidebar",
)

navigation.run()
