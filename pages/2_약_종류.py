import streamlit as st

from drug_data_tools import (
    load_data,
    filter_drugs,
)


st.title(
    "🗂️ 약 종류"
)

st.caption(
    "약 종류를 선택하면 "
    "해당 제품을 확인할 수 있습니다."
)


drug_data, _ = (
    load_data()
)


categories = sorted(
    drug_data[
        "카테고리"
    ]
    .dropna()
    .unique()
    .tolist()
)


category = st.selectbox(
    "약 종류 선택",
    categories,
)


result = filter_drugs(
    drug_data,
    category,
)


st.write(
    f"**{category} : "
    f"{len(result)}개 제품**"
)


st.dataframe(
    result[
        [
            "제품명",
            "제조사",
            "성분",
        ]
    ],
    width="stretch",
    hide_index=True,
)
