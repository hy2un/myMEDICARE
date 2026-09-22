import streamlit as st

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


# =========================================================
# 메인 페이지
# =========================================================
def home_page():

    st.title("💊 MyMed Care")

    st.caption(
        "내 약의 중복 성분을 확인하고 "
        "실제 의약품을 검색하는 서비스"
    )

    # 데이터 불러오기
    try:
        drug_data, _ = load_data()

    except Exception as error:

        st.error(
            "데이터 파일을 불러오지 못했습니다."
        )

        st.code(str(error))

        st.stop()


    # -----------------------------------------------------
    # 메인 화면 탭
    # -----------------------------------------------------
    tab_my_drugs, tab_search = st.tabs(
        [
            "나의 약",
            "약 검색",
        ]
    )


    # =====================================================
    # 나의 약
    # =====================================================
    with tab_my_drugs:

        st.subheader("나의 약")

        selected_names = st.multiselect(
            "확인할 약을 2개 이상 선택하세요.",
            options=sorted(
                drug_data["제품명"].tolist()
            ),
            placeholder="약 이름을 선택하세요.",
        )

        selected_drugs = get_selected_drugs(
            drug_data,
            selected_names,
        )


        # 선택한 제품 표시
        if not selected_drugs.empty:

            st.dataframe(
                selected_drugs[
                    [
                        "제품명",
                        "제조사",
                        "카테고리",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )


        # 중복 성분 분석
        if st.button(
            "중복 성분 분석",
            type="primary",
            width="stretch",
        ):

            if len(selected_names) < 2:

                st.warning(
                    "2개 이상의 약을 선택해 주세요."
                )

            else:

                duplicates, ingredient_map = (
                    find_duplicates(
                        selected_drugs
                    )
                )


                # 중복 없음
                if not duplicates:

                    st.success(
                        "중복 성분이 발견되지 않았습니다."
                    )


                # 중복 있음
                else:

                    st.warning(
                        f"중복 성분 "
                        f"{len(duplicates)}개가 "
                        "발견되었습니다."
                    )

                    for ingredient, products in (
                        duplicates.items()
                    ):

                        st.write(
                            f"**{ingredient}** — "
                            f"{', '.join(products)}"
                        )


                # 전체 성분 확인
                with st.expander(
                    "선택한 약의 전체 성분 보기"
                ):

                    import pandas as pd

                    rows = []

                    for ingredient, products in (
                        sorted(
                            ingredient_map.items()
                        )
                    ):

                        rows.append(
                            {
                                "성분명":
                                    ingredient,

                                "포함 제품 수":
                                    len(products),

                                "포함 제품":
                                    ", ".join(
                                        sorted(products)
                                    ),
                            }
                        )

                    st.dataframe(
                        pd.DataFrame(rows),
                        width="stretch",
                        hide_index=True,
                    )


        st.info(
            "중복 성분 여부만 확인하는 교육용 기능입니다. "
            "실제 병용 가능 여부나 복용량은 "
            "판단하지 않습니다."
        )


    # =====================================================
    # 약 검색
    # =====================================================
    with tab_search:

        st.subheader("약 검색")

        st.caption(
            "제품명, 제조사, 약 종류 또는 "
            "성분명으로 검색할 수 있습니다."
        )

        keyword = st.text_input(
            "검색어",
            placeholder=(
                "예: 타이레놀 / "
                "아세트아미노펜 / 감기약"
            ),
        )


        if keyword.strip():

            result = search_drugs(
                drug_data,
                keyword,
            )


            if result.empty:

                st.info(
                    "검색 결과가 없습니다."
                )


            else:

                st.success(
                    f"{len(result)}개의 "
                    "제품을 찾았습니다."
                )

                st.dataframe(
                    result[
                        [
                            "제품명",
                            "제조사",
                            "카테고리",
                            "성분",
                        ]
                    ],
                    width="stretch",
                    hide_index=True,
                )

        else:

            st.info(
                "검색어를 입력해 주세요."
            )


# =========================================================
# 왼쪽 메뉴 설정
# =========================================================

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
