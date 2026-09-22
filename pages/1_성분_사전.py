import streamlit as st

from drug_data_tools import (
    load_data,
    search_ingredient,
)


st.title(
    "📘 성분 사전"
)

st.caption(
    "성분명 또는 성분 분류를 "
    "검색할 수 있습니다."
)


drug_data, ingredient_data = (
    load_data()
)


keyword = st.text_input(
    "검색어",
    placeholder=(
        "예: 아세트아미노펜 / "
        "항히스타민 / 진해"
    ),
)


if keyword.strip():

    result = search_ingredient(
        ingredient_data,
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
            "성분을 찾았습니다."
        )

        st.dataframe(
            result,
            width="stretch",
            hide_index=True,
        )


else:

    st.subheader(
        "전체 성분 목록"
    )

    st.dataframe(
        ingredient_data[
            [
                "성분명",
                "분류",
                "설명",
            ]
        ],
        width="stretch",
        hide_index=True,
    )
