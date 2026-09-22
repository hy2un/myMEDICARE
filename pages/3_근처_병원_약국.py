import streamlit as st
import pandas as pd
import requests


st.title(
    "📍 근처 병원·약국"
)

st.caption(
    "주소를 기준으로 주변 병원 또는 "
    "약국을 찾고 지도에 표시합니다."
)


# =========================================================
# Kakao API Key
# =========================================================
def get_api_key():

    try:

        return st.secrets[
            "KAKAO_REST_API_KEY"
        ]

    except Exception:

        return None


# =========================================================
# Kakao API Header
# =========================================================
def kakao_headers(
    api_key
):

    return {
        "Authorization":
            f"KakaoAK {api_key}"
    }


# =========================================================
# 주소 → 좌표
# =========================================================
def address_to_coordinates(
    address,
    api_key,
):

    url = (
        "https://dapi.kakao.com/"
        "v2/local/search/address.json"
    )


    response = requests.get(
        url,
        headers=kakao_headers(
            api_key
        ),
        params={
            "query": address
        },
        timeout=10,
    )


    response.raise_for_status()


    documents = (
        response.json()
        .get(
            "documents",
            [],
        )
    )


    if not documents:

        return None


    longitude = float(
        documents[0]["x"]
    )

    latitude = float(
        documents[0]["y"]
    )


    return (
        longitude,
        latitude,
    )


# =========================================================
# 주변 병원 / 약국 검색
# =========================================================
def search_nearby(
    longitude,
    latitude,
    category_code,
    radius_meter,
    api_key,
):

    url = (
        "https://dapi.kakao.com/"
        "v2/local/search/category.json"
    )


    response = requests.get(
        url,
        headers=kakao_headers(
            api_key
        ),
        params={
            "category_group_code":
                category_code,

            "x":
                longitude,

            "y":
                latitude,

            "radius":
                radius_meter,

            "sort":
                "distance",

            "size":
                15,
        },
        timeout=10,
    )


    response.raise_for_status()


    return (
        response.json()
        .get(
            "documents",
            [],
        )
    )


# =========================================================
# API Key 확인
# =========================================================
api_key = get_api_key()


if not api_key:

    st.warning(
        "Kakao REST API 키가 "
        "아직 등록되지 않았습니다."
    )

    st.code(
        'KAKAO_REST_API_KEY = '
        '"여기에_REST_API_KEY_입력"'
    )

    st.caption(
        "Streamlit Cloud의 "
        "Settings → Secrets에 "
        "등록해 주세요."
    )

    st.stop()


# =========================================================
# 검색 UI
# =========================================================
address = st.text_input(
    "기준 주소",
    placeholder=(
        "예: 대전광역시 "
        "서구 둔산로 100"
    ),
)


place_type = st.radio(
    "찾을 장소",
    [
        "병원",
        "약국",
    ],
    horizontal=True,
)


radius_km = st.selectbox(
    "검색 반경",
    [
        1,
        2,
        3,
        5,
        10,
    ],
    index=2,
)


# =========================================================
# 검색 실행
# =========================================================
if st.button(
    "주변 검색",
    type="primary",
    width="stretch",
):


    if not address.strip():

        st.warning(
            "주소를 입력해 주세요."
        )

        st.stop()


    try:

        center = (
            address_to_coordinates(
                address,
                api_key,
            )
        )


        if center is None:

            st.info(
                "주소를 찾지 못했습니다. "
                "도로명 주소를 "
                "다시 확인해 주세요."
            )

            st.stop()


        longitude, latitude = (
            center
        )


        # 병원 HP8
        # 약국 PM9
        category_code = (
            "HP8"
            if place_type == "병원"
            else "PM9"
        )


        places = search_nearby(
            longitude,
            latitude,
            category_code,
            radius_km * 1000,
            api_key,
        )


        if not places:

            st.info(
                "선택한 반경에서 "
                "검색 결과가 없습니다."
            )

            st.stop()


        rows = []


        for place in places:

            rows.append(
                {
                    "이름":
                        place.get(
                            "place_name",
                            "",
                        ),

                    "거리(m)":
                        place.get(
                            "distance",
                            "",
                        ),

                    "전화":
                        place.get(
                            "phone",
                            "",
                        ),

                    "주소":
                        (
                            place.get(
                                "road_address_name"
                            )
                            or
                            place.get(
                                "address_name",
                                "",
                            )
                        ),

                    "카카오맵":
                        place.get(
                            "place_url",
                            "",
                        ),

                    "lat":
                        float(
                            place["y"]
                        ),

                    "lon":
                        float(
                            place["x"]
                        ),
                }
            )


        result = pd.DataFrame(
            rows
        )


        st.success(
            f"{len(result)}곳을 "
            "찾았습니다."
        )


        # -------------------------------------------------
        # 검색 결과
        # -------------------------------------------------
        st.dataframe(
            result[
                [
                    "이름",
                    "거리(m)",
                    "전화",
                    "주소",
                    "카카오맵",
                ]
            ],
            width="stretch",
            hide_index=True,

            column_config={
                "카카오맵":
                    st.column_config.LinkColumn(
                        "카카오맵"
                    )
            },
        )


        # -------------------------------------------------
        # 지도
        # -------------------------------------------------
        st.subheader(
            "지도"
        )


        st.map(
            result,
            latitude="lat",
            longitude="lon",
            size=80,
            width="stretch",
        )


    except requests.RequestException as error:

        st.error(
            "Kakao API 요청 중 "
            "오류가 발생했습니다."
        )

        st.code(
            str(error)
        )
