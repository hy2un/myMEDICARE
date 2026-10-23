import pandas as pd
import requests
import streamlit as st


st.title("📍 근처 병원·약국")

st.caption(
    "주소를 기준으로 주변 병원·의원 또는 약국을 검색합니다."
)


# ==========================================
# 1. 카카오 API 키 불러오기
# ==========================================

def get_key():
    try:
        return st.secrets.get("KAKAO_REST_API_KEY", "")
    except (FileNotFoundError, KeyError):
        return ""


# ==========================================
# 2. 카카오 API 요청
# ==========================================

def get_kakao(endpoint, params, key):

    url = (
        "https://dapi.kakao.com/v2/local/search/"
        f"{endpoint}.json"
    )

    response = requests.get(
        url,
        headers={
            "Authorization": f"KakaoAK {key}"
        },
        params=params,
        timeout=12,
    )

    if not response.ok:

        try:
            message = response.json().get(
                "msg",
                "카카오 API 설정을 확인하세요."
            )
        except ValueError:
            message = "카카오 API 설정을 확인하세요."

        raise RuntimeError(
            f"카카오 API 오류 {response.status_code}: {message}"
        )

    return response.json()


# ==========================================
# 3. 동물병원인지 확인
# ==========================================

def is_animal_hospital(place):

    name = place.get("place_name", "")
    category = place.get("category_name", "")

    combined = name + " " + category

    animal_keywords = [
        "동물병원",
        "반려동물병원",
        "동물의료",
        "수의",
    ]

    return any(
        word in combined
        for word in animal_keywords
    )


# ==========================================
# 4. 사람 병원 또는 약국 검색
# ==========================================

def find_places(x, y, kind, radius, key):

    if kind == "병원·의원":
        category_code = "HP8"
    else:
        category_code = "PM9"

    found = {}

    for page in range(1, 4):

        result = get_kakao(
            "category",
            {
                "category_group_code": category_code,
                "x": x,
                "y": y,
                "radius": radius,
                "sort": "distance",
                "size": 15,
                "page": page,
            },
            key,
        )

        for place in result.get("documents", []):

            # 사람 병원 검색에서는 동물병원 제외
            if (
                kind == "병원·의원"
                and is_animal_hospital(place)
            ):
                continue

            place_id = (
                place.get("id")
                or place.get("place_name")
            )

            found[place_id] = place

        if result.get("meta", {}).get("is_end", True):
            break

    return sorted(
        found.values(),
        key=lambda p: int(p.get("distance") or 0),
    )


# ==========================================
# 5. API 키 확인
# ==========================================

api_key = get_key()

if not api_key:

    st.warning(
        "카카오 REST API 키가 등록되지 않았습니다."
    )

    st.code(
        'KAKAO_REST_API_KEY = "REST_API_KEY"',
        language="toml",
    )

    st.stop()


# ==========================================
# 6. 검색 조건 입력
# ==========================================

with st.form("human_hospital_form"):

    address = st.text_input(
        "검색 기준 주소",
        placeholder="예: 대전광역시 서구 둔산로 100",
    )

    kind = st.radio(
        "찾을 장소",
        [
            "병원·의원",
            "약국",
        ],
        horizontal=True,
    )

    radius_km = st.selectbox(
        "검색 반경",
        [1, 2, 3, 5, 10],
        index=2,
    )

    submitted = st.form_submit_button(
        "주변 검색",
        type="primary",
    )


# ==========================================
# 7. 검색 실행
# ==========================================

if submitted:

    if not address.strip():

        st.warning(
            "주소를 입력해 주세요."
        )

    else:

        try:

            address_result = get_kakao(
                "address",
                {
                    "query": address.strip()
                },
                api_key,
            )

            locations = address_result.get(
                "documents", []
            )

            if not locations:

                st.warning(
                    "주소를 찾지 못했습니다. "
                    "도로명 주소를 입력해 주세요."
                )

                st.session_state.pop(
                    "human_place_results",
                    None,
                )

            else:

                x = float(locations[0]["x"])
                y = float(locations[0]["y"])

                places = find_places(
                    x,
                    y,
                    kind,
                    radius_km * 1000,
                    api_key,
                )

                rows = []

                for place in places:

                    rows.append(
                        {
                            "이름": place.get(
                                "place_name", ""
                            ),
                            "거리(m)": int(
                                place.get("distance") or 0
                            ),
                            "전화": place.get(
                                "phone", ""
                            ),
                            "주소": (
                                place.get("road_address_name")
                                or place.get("address_name", "")
                            ),
                            "상세정보": place.get(
                                "place_url", ""
                            ),
                            "lat": float(place["y"]),
                            "lon": float(place["x"]),
                        }
                    )

                st.session_state[
                    "human_place_results"
                ] = rows

        except (
            requests.RequestException,
            RuntimeError,
            ValueError,
        ) as error:

            st.error(
                f"검색 중 오류가 발생했습니다: {error}"
            )


# ==========================================
# 8. 검색 결과 출력
# ==========================================

saved = st.session_state.get(
    "human_place_results"
)

if saved is not None:

    if not saved:

        st.info(
            "검색 결과가 없습니다. "
            "주소나 검색 반경을 변경해 보세요."
        )

    else:

        df = pd.DataFrame(saved)

        st.success(
            f"{len(df)}곳을 찾았습니다."
        )

        st.dataframe(
            df[
                [
                    "이름",
                    "거리(m)",
                    "전화",
                    "주소",
                    "상세정보",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "상세정보": st.column_config.LinkColumn(
                    "카카오맵 열기"
                )
            },
        )

        st.map(
            df[["lat", "lon"]]
        )

        st.caption(
            "동물병원은 명칭과 업종 정보를 기준으로 "
            "검색 결과에서 제외했습니다. "
            "지도 등록 정보에 따라 일부 예외가 있을 수 있습니다."
        )
