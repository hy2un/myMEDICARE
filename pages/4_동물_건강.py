
from pathlib import Path

import pandas as pd
import requests
import streamlit as st


# ==========================================
# 1. CSV 데이터 불러오기
# ==========================================

DATA_DIR = Path(__file__).resolve().parent.parent


@st.cache_data
def load_animal_data():
    drug_path = DATA_DIR / "animal_drug_data.csv"
    ingredient_path = DATA_DIR / "animal_ingredient_data.csv"

    if not drug_path.exists() or not ingredient_path.exists():
        raise FileNotFoundError(
            "동물 약물 CSV 파일이 없습니다. "
            "GitHub 저장소 최상위 폴더를 확인하세요."
        )

    drug_data = pd.read_csv(drug_path).fillna("")
    ingredient_data = pd.read_csv(ingredient_path).fillna("")

    return drug_data, ingredient_data


# ==========================================
# 2. 카카오 API 연결
# ==========================================

def kakao_key():
    try:
        return st.secrets.get("KAKAO_REST_API_KEY", "")
    except (FileNotFoundError, KeyError):
        return ""


def kakao_get(endpoint, params, key):
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
# 3. 주소를 좌표로 변환
# ==========================================

def find_location(address, key):
    result = kakao_get(
        "address",
        {"query": address},
        key,
    )

    places = result.get("documents", [])

    if not places:
        return None

    x = float(places[0]["x"])
    y = float(places[0]["y"])

    return x, y


# ==========================================
# 4. 동물병원 검색
# ==========================================

def find_vet_hospitals(x, y, radius_m, key):
    found = {}

    for page in range(1, 4):
        result = kakao_get(
            "keyword",
            {
                "query": "동물병원",
                "x": x,
                "y": y,
                "radius": radius_m,
                "sort": "distance",
                "size": 15,
                "page": page,
            },
            key,
        )

        for place in result.get("documents", []):
            name = place.get("place_name", "")
            category = place.get("category_name", "")

            # 동물병원과 관련 없는 검색 결과 제외
            if (
                "동물병원" not in name
                and "동물병원" not in category
            ):
                continue

            place_id = place.get("id") or name
            found[place_id] = place

        if result.get("meta", {}).get("is_end", True):
            break

    return sorted(
        found.values(),
        key=lambda p: int(p.get("distance") or 0),
    )


# ==========================================
# 5. 동물 건강 페이지 시작
# ==========================================

st.title("🐾 동물 건강")

st.caption(
    "동물 약물, 약 성분, 동물병원 위치를 "
    "한 페이지에서 확인할 수 있습니다."
)

st.info(
    "동물 약물 자료는 교육용입니다. "
    "제품별 사용 가능 동물과 용량이 다르므로 "
    "반드시 수의사에게 확인하세요. "
    "사람용 약을 동물에게 임의로 투여하지 마세요."
)


try:
    drug_data, ingredient_data = load_animal_data()

except (FileNotFoundError, ValueError) as error:
    st.error(str(error))
    st.stop()


# ==========================================
# 6. 세 개의 탭 만들기
# ==========================================

medicine_tab, ingredient_tab, hospital_tab = st.tabs(
    [
        "💊 동물 약",
        "🧪 동물 약 성분",
        "📍 동물병원 위치",
    ]
)


# ==========================================
# 첫 번째 탭 : 동물 약
# ==========================================

with medicine_tab:

    st.subheader("동물 약 찾아보기")

    st.write(
        f"등록된 약물 항목: **{len(drug_data)}개**"
    )

    search_word = st.text_input(
        "동물 약 검색",
        placeholder="예: 셀라멕틴, 항균제",
        key="animal_drug_search",
    )

    categories = sorted(
        drug_data["분류"].unique().tolist()
    )

    category = st.selectbox(
        "동물 약 종류",
        ["전체 보기"] + categories,
        key="animal_drug_category",
    )

    result = drug_data.copy()

    if category != "전체 보기":
        result = result[
            result["분류"] == category
        ]

    if search_word.strip():
        word = search_word.strip()
        matched = False

        for column in [
            "약물명",
            "주요성분",
            "분류",
            "사용영역",
        ]:
            matched = matched | result[
                column
            ].str.contains(
                word,
                case=False,
                regex=False,
                na=False,
            )

        result = result[matched]

    st.write(
        f"검색 결과: **{len(result)}개**"
    )

    st.dataframe(
        result[
            [
                "약물명",
                "분류",
                "주요성분",
                "대상동물",
                "사용영역",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    if not result.empty:

        selected_drug = st.selectbox(
            "자세히 볼 동물 약 선택",
            result["약물명"].tolist(),
            key="selected_animal_drug",
        )

        detail = result[
            result["약물명"] == selected_drug
        ].iloc[0]

        st.markdown("### 약물 상세 정보")

        st.write(
            f"**약물명:** {detail['약물명']}"
        )

        st.write(
            f"**주요 성분:** {detail['주요성분']}"
        )

        st.write(
            f"**분류:** {detail['분류']}"
        )

        st.write(
            f"**대상 동물:** {detail['대상동물']}"
        )

        st.write(
            f"**사용 영역:** {detail['사용영역']}"
        )

        st.warning(
            f"주의사항: {detail['주의사항']}"
        )


# ==========================================
# 두 번째 탭 : 동물 약 성분
# ==========================================

with ingredient_tab:

    st.subheader("동물 약 성분 사전")

    st.write(
        f"등록된 성분: **{len(ingredient_data)}개**"
    )

    ingredient_word = st.text_input(
        "성분명 또는 영문명 검색",
        placeholder="예: Fluralaner, 아목시실린",
        key="animal_ingredient_search",
    )

    ingredient_result = ingredient_data.copy()

    if ingredient_word.strip():
        word = ingredient_word.strip()
        matched = False

        for column in [
            "성분명",
            "영문명",
            "분류",
            "설명",
        ]:
            matched = matched | ingredient_result[
                column
            ].str.contains(
                word,
                case=False,
                regex=False,
                na=False,
            )

        ingredient_result = ingredient_result[
            matched
        ]

    st.write(
        f"검색 결과: **{len(ingredient_result)}개**"
    )

    st.dataframe(
        ingredient_result,
        use_container_width=True,
        hide_index=True,
    )

    if not ingredient_result.empty:

        selected_ingredient = st.selectbox(
            "자세히 볼 성분 선택",
            ingredient_result["성분명"].tolist(),
            key="selected_animal_ingredient",
        )

        detail = ingredient_result[
            ingredient_result["성분명"]
            == selected_ingredient
        ].iloc[0]

        st.markdown("### 성분 상세 정보")

        st.write(
            f"**성분명:** {detail['성분명']}"
        )

        st.write(
            f"**영문명:** {detail['영문명']}"
        )

        st.write(
            f"**분류:** {detail['분류']}"
        )

        st.write(
            f"**설명:** {detail['설명']}"
        )

        st.warning(
            f"주의사항: {detail['주의사항']}"
        )


# ==========================================
# 세 번째 탭 : 동물병원 위치
# ==========================================

with hospital_tab:

    st.subheader("근처 동물병원 찾기")

    st.caption(
        "주소를 입력하면 주변 동물병원을 "
        "가까운 순으로 검색합니다."
    )

    api_key = kakao_key()

    if not api_key:

        st.warning(
            "카카오 REST API 키가 등록되지 않았습니다."
        )

        st.code(
            'KAKAO_REST_API_KEY = "REST_API_KEY"',
            language="toml",
        )

    else:

        with st.form("animal_hospital_form"):

            address = st.text_input(
                "검색 기준 주소",
                placeholder="예: 대전광역시 서구 둔산로 100",
            )

            radius_km = st.selectbox(
                "검색 반경",
                [1, 2, 3, 5, 10],
                index=2,
            )

            submitted = st.form_submit_button(
                "동물병원 검색",
                type="primary",
            )

        if submitted:

            if not address.strip():

                st.warning(
                    "주소를 입력해 주세요."
                )

            else:

                try:
                    location = find_location(
                        address.strip(),
                        api_key,
                    )

                    if location is None:

                        st.warning(
                            "주소를 찾지 못했습니다."
                        )

                        st.session_state.pop(
                            "vet_hospital_results",
                            None,
                        )

                    else:

                        x, y = location

                        places = find_vet_hospitals(
                            x,
                            y,
                            radius_km * 1000,
                            api_key,
                        )

                        rows = []

                        for place in places:
                            rows.append(
                                {
                                    "동물병원": place.get(
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
                            "vet_hospital_results"
                        ] = rows

                except (
                    requests.RequestException,
                    RuntimeError,
                    ValueError,
                ) as error:

                    st.error(
                        f"검색 중 오류가 발생했습니다: {error}"
                    )

        saved = st.session_state.get(
            "vet_hospital_results"
        )

        if saved is not None:

            if saved:

                df = pd.DataFrame(saved)

                st.success(
                    f"동물병원 {len(df)}곳을 찾았습니다."
                )

                st.dataframe(
                    df[
                        [
                            "동물병원",
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
                    "거리 값은 직선거리 기준입니다. "
                    "진료시간은 방문 전에 확인하세요."
                )

            else:

                st.info(
                    "설정한 반경에서 동물병원을 찾지 못했습니다."
                )
