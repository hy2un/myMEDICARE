import streamlit as st
import pandas as pd

from drug_data_tools import (
    load_data,
    get_selected_drugs,
    find_duplicates,
    search_drugs,
)

st.set_page_config(
    page_title="MyMed Care",
    page_icon="💊",
    layout="wide",
)


def home_page():
    st.title("💊 MyMed Care")
    st.caption(
        "약 이름을 검색해 나의 약에 추가하고, "
        "중복 성분을 확인할 수 있는 서비스"
    )

    try:
        drug_data, _ = load_data()
    except Exception as error:
        st.error("데이터 파일을 불러오지 못했습니다.")
        st.code(str(error))
        st.stop()

    # 세션 상태 초기화
    if "my_drugs" not in st.session_state:
        st.session_state.my_drugs = []

    if "my_conditions" not in st.session_state:
        st.session_state.my_conditions = []

    tab_my_drugs, tab_search, tab_conditions = st.tabs(
        ["나의 약", "약 검색", "나의 질병"]
    )

    # =====================================================
    # 나의 약
    # =====================================================
    with tab_my_drugs:
        st.subheader("나의 약")
        st.caption(
            "약 이름을 검색한 뒤 원하는 제품을 선택해 나의 약에 추가하세요."
        )

        # -------------------------------------------------
        # 1. 약 검색
        # -------------------------------------------------
        my_drug_keyword = st.text_input(
            "약 이름 검색",
            placeholder="예: 타이레놀, 게보린, 판콜",
            key="my_drug_search_keyword",
        )

        if my_drug_keyword.strip():
            search_result = search_drugs(
                drug_data,
                my_drug_keyword,
            )

            if search_result.empty:
                st.info("검색 결과가 없습니다.")
            else:
                st.success(
                    f"{len(search_result)}개의 제품을 찾았습니다."
                )

                # 검색 결과 간단 표시
                st.dataframe(
                    search_result[
                        ["제품명", "제조사", "카테고리"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                # -------------------------------------------------
                # 2. 검색 결과에서 제품 선택
                # -------------------------------------------------
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
                        st.session_state.my_drugs.append(
                            selected_search_drug
                        )
                        st.success(
                            f"{selected_search_drug}을(를) 나의 약에 추가했습니다."
                        )

        else:
            st.info("약 이름을 입력하면 검색 결과가 표시됩니다.")

        st.divider()

        # -------------------------------------------------
        # 3. 현재 나의 약 목록
        # -------------------------------------------------
        st.markdown("### 현재 나의 약")

        if st.session_state.my_drugs:
            selected_drugs = get_selected_drugs(
                drug_data,
                st.session_state.my_drugs,
            )

            st.dataframe(
                selected_drugs[
                    ["제품명", "제조사", "카테고리", "성분"]
                ],
                use_container_width=True,
                hide_index=True,
            )

            # 삭제
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

            # -------------------------------------------------
            # 4. 중복 성분 분석
            # -------------------------------------------------
            st.divider()

            if st.button(
                "중복 성분 분석",
                type="primary",
                key="analyze_duplicates_button",
                use_container_width=True,
            ):
                if len(st.session_state.my_drugs) < 2:
                    st.warning("2개 이상의 약을 추가해 주세요.")
                else:
                    duplicates, ingredient_map = find_duplicates(
                        selected_drugs
                    )

                    if not duplicates:
                        st.success(
                            "선택한 약 사이에서 중복 성분이 발견되지 않았습니다."
                        )
                    else:
                        st.warning(
                            f"중복 성분 {len(duplicates)}개가 발견되었습니다."
                        )

                        for ingredient, products in duplicates.items():
                            st.write(
                                f"**{ingredient}** — {', '.join(products)}"
                            )

                    with st.expander(
                        "선택한 약의 전체 성분 보기"
                    ):
                        rows = []

                        for ingredient, products in sorted(
                            ingredient_map.items()
                        ):
                            rows.append(
                                {
                                    "성분명": ingredient,
                                    "포함 제품 수": len(products),
                                    "포함 제품": ", ".join(
                                        sorted(products)
                                    ),
                                }
                            )

                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True,
                        )

        else:
            st.write("아직 나의 약에 추가된 제품이 없습니다.")

        st.info(
            "이 기능은 중복 성분 여부만 확인하는 교육용 기능입니다. "
            "실제 병용 가능 여부나 복용량은 판단하지 않습니다."
        )

    # =====================================================
    # 약 검색
    # =====================================================
    with tab_search:
        st.subheader("약 검색")

        st.caption(
            "제품명, 제조사, 약 종류 또는 성분명으로 검색할 수 있습니다."
        )

        keyword = st.text_input(
            "검색어",
            placeholder="예: 타이레놀 / 아세트아미노펜 / 감기약",
            key="drug_search_keyword",
        )

        if keyword.strip():
            result = search_drugs(
                drug_data,
                keyword,
            )

            if result.empty:
                st.info("검색 결과가 없습니다.")
            else:
                st.success(
                    f"{len(result)}개의 제품을 찾았습니다."
                )

                st.dataframe(
                    result[
                        ["제품명", "제조사", "카테고리", "성분"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("검색어를 입력해 주세요.")

    # =====================================================
    # 나의 질병
    # =====================================================
    with tab_conditions:
        st.subheader("나의 질병")

        st.caption(
            "본인이 알고 있는 질병이나 주의해야 할 건강 상태를 직접 입력할 수 있습니다."
        )

        st.info(
            "입력한 정보는 현재 앱 세션에서만 임시로 사용하며 "
            "CSV 파일이나 GitHub에 저장하지 않습니다."
        )

        condition_text = st.text_input(
            "질병 또는 건강 상태",
            placeholder="예: 고혈압, 당뇨병, 천식",
            key="condition_input",
        )

        if st.button(
            "질병 추가",
            type="primary",
            key="add_condition_button",
        ):
            new_condition = condition_text.strip()

            if not new_condition:
                st.warning("질병 또는 건강 상태를 입력해 주세요.")
            elif new_condition in st.session_state.my_conditions:
                st.info("이미 추가된 항목입니다.")
            else:
                st.session_state.my_conditions.append(
                    new_condition
                )
                st.success(
                    f"{new_condition} 항목을 추가했습니다."
                )

        if st.session_state.my_conditions:
            st.markdown("#### 등록한 질병/건강 상태")

            condition_df = pd.DataFrame(
                {
                    "질병/건강 상태":
                        st.session_state.my_conditions
                }
            )

            st.dataframe(
                condition_df,
                use_container_width=True,
                hide_index=True,
            )

            remove_condition = st.selectbox(
                "삭제할 항목 선택",
                st.session_state.my_conditions,
                key="remove_condition_select",
            )

            if st.button(
                "선택한 항목 삭제",
                key="remove_condition_button",
            ):
                st.session_state.my_conditions.remove(
                    remove_condition
                )
                st.rerun()

            if st.button(
                "전체 삭제",
                key="clear_condition_button",
            ):
                st.session_state.my_conditions = []
                st.rerun()

        else:
            st.write("아직 등록한 질병/건강 상태가 없습니다.")

        st.warning(
            "현재 기능은 질병 정보를 기록하는 기능만 제공합니다. "
            "특정 질병과 의약품의 복용 가능 여부나 금기 여부를 자동으로 판단하지 않습니다."
        )


home = st.Page(
    home_page,
    title="MyMed Care",
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
