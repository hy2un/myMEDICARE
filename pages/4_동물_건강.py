"""동물 건강: 동물 약·성분, 개/고양이 위험 약물, 동물병원 위치."""

from pathlib import Path
from urllib.parse import quote

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st


# ==========================================
# 1. 페이지 디자인
# ==========================================

st.markdown(
    """
    <style>
    .stApp {
        background: #fbfdfc;
    }

    h1, h2, h3 {
        color: #173d38 !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #147f66 !important;
    }

    .stTabs [aria-selected="true"] {
        color: #147f66 !important;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 12px;
    }

    div[data-testid="stSelectbox"] > div {
        border-radius: 12px;
    }

    div[data-testid="stFormSubmitButton"] button {
        background: #147f66;
        border-color: #147f66;
        color: white;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

ROOT = Path(__file__).resolve().parent.parent


# ==========================================
# 2. 동물 약물 CSV 불러오기
# ==========================================

def load_animal_data():

    drug_path = ROOT / "animal_drug_data.csv"
    ingredient_path = ROOT / "animal_ingredient_data.csv"

    if not drug_path.exists() or not ingredient_path.exists():

        st.error(
            "동물 약물 CSV가 없습니다. "
            "GitHub 최상위 폴더를 확인해 주세요."
        )

        st.stop()

    try:

        drug_data = pd.read_csv(
            drug_path,
            encoding="utf-8-sig",
        ).fillna("")

        ingredient_data = pd.read_csv(
            ingredient_path,
            encoding="utf-8-sig",
        ).fillna("")

        return drug_data, ingredient_data

    except (
        OSError,
        UnicodeError,
        pd.errors.ParserError,
    ) as err:

        st.error(
            f"동물 약 데이터 읽기 실패: {err}"
        )

        st.stop()


# ==========================================
# 3. CSV 검색 함수
# ==========================================

def filter_rows(df, q, columns):

    if not q.strip():
        return df

    mask = df[columns].astype(str).apply(
        lambda s: s.str.contains(
            q.strip(),
            case=False,
            regex=False,
            na=False,
        )
    ).any(axis=1)

    return df[mask]


# ==========================================
# 4. 카카오 API 키
# ==========================================

def kakao_key():

    try:
        return st.secrets.get(
            "KAKAO_REST_API_KEY", ""
        )

    except (KeyError, FileNotFoundError):
        return ""


# ==========================================
# 5. 카카오 장소 검색 요청
# ==========================================

def kakao_search(endpoint, params, key):

    url = (
        "https://dapi.kakao.com/v2/local/search/"
        f"{endpoint}.json"
    )

    response = requests.get(
        url,
        params=params,
        headers={
            "Authorization": f"KakaoAK {key}"
        },
        timeout=12,
    )

    response.raise_for_status()

    return response.json()


# ==========================================
# 6. 주소 또는 건물·장소명 검색
# ==========================================

def locate(query, key):
    """
    주소 API를 먼저 조회하고,
    결과가 없으면 장소명 키워드 API를 이용한다.
    """

    items = kakao_search(
        "address",
        {"query": query},
        key,
    ).get("documents", [])

    candidates = []

    for item in items[:8]:

        candidates.append(
            {
                "label": (
                    item.get("address_name")
                    or query
                ),
                "lon": float(item["x"]),
                "lat": float(item["y"]),
            }
        )

    # 주소 검색 결과가 없는 경우
    # 건물명과 장소명으로 다시 검색한다.

    if not candidates:

        items = kakao_search(
            "keyword",
            {
                "query": query,
                "size": 15,
            },
            key,
        ).get("documents", [])

        for item in items:

            name = item.get(
                "place_name", ""
            )

            address = (
                item.get("road_address_name")
                or item.get("address_name", "")
            )

            candidates.append(
                {
                    "label": f"{name} — {address}",
                    "lon": float(item["x"]),
                    "lat": float(item["y"]),
                }
            )

    return candidates


# ==========================================
# 7. 주변 동물병원 검색
# ==========================================

def nearby_vets(lon, lat, radius_km, key):
    """
    기준 좌표에서 선택한 반경 이내의
    동물병원을 카카오 키워드 API로 검색한다.
    """

    found = {}

    for page in range(1, 4):

        answer = kakao_search(
            "keyword",
            {
                "query": "동물병원",
                "x": lon,
                "y": lat,
                "radius": int(radius_km * 1000),
                "sort": "distance",
                "size": 15,
                "page": page,
            },
            key,
        )

        for place in answer.get(
            "documents", []
        ):

            info = (
                place.get("place_name", "")
                + " "
                + place.get("category_name", "")
            )

            if (
                "동물병원" not in info
                and "수의" not in info
            ):
                continue

            place_id = (
                place.get("id")
                or place.get("place_name")
            )

            found[place_id] = place

        if answer.get(
            "meta", {}
        ).get("is_end", True):
            break

    return sorted(
        found.values(),
        key=lambda p: int(
            p.get("distance") or 0
        ),
    )


# ==========================================
# 8. 작은 지도 핀 만들기
# ==========================================

def pin(color):

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="36" height="48" viewBox="0 0 36 48">'
        '<path '
        'd="M18 2C9 2 2 9 2 18c0 12 16 28 16 28'
        's16-16 16-28C34 9 27 2 18 2Z" '
        f'fill="{color}" '
        'stroke="white" stroke-width="2"/>'
        '<circle cx="18" cy="18" r="7" fill="white"/>'
        '</svg>'
    )

    return {
        "url": (
            "data:image/svg+xml;charset=utf-8,"
            + quote(svg)
        ),
        "width": 36,
        "height": 48,
        "anchorX": 18,
        "anchorY": 48,
    }


# ==========================================
# 9. 동물병원 지도 출력
# ==========================================

def show_map(df, center):

    points = df[
        ["이름", "lat", "lon"]
    ].copy()

    # 동물병원: 빨간색 핀
    points["icon"] = [
        pin("#ea5455")
        for _ in range(len(points))
    ]

    # 검색 기준 위치: 초록색 핀
    base = pd.DataFrame(
        [
            {
                "이름": "검색 기준 위치",
                "lat": center["lat"],
                "lon": center["lon"],
                "icon": pin("#147f66"),
            }
        ]
    )

    all_points = pd.concat(
        [points, base],
        ignore_index=True,
    )

    deck = pdk.Deck(
        map_style=(
            "https://basemaps.cartocdn.com/"
            "gl/positron-gl-style/style.json"
        ),
        initial_view_state=pdk.ViewState(
            latitude=center["lat"],
            longitude=center["lon"],
            zoom=13,
            pitch=0,
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                all_points,
                get_position="[lon, lat]",
                get_radius=4,
                radius_min_pixels=4,
                radius_max_pixels=4,
                get_fill_color=[230, 66, 65, 190],
                pickable=True,
            ),
            pdk.Layer(
                "IconLayer",
                all_points,
                get_icon="icon",
                get_position="[lon, lat]",
                get_size=22,
                size_scale=1,
                pickable=True,
            ),
        ],
        tooltip={
            "text": "{이름}"
        },
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
    )

    st.caption(
        "초록색 핀: 검색 기준 위치 / "
        "빨간색 핀: 동물병원. "
        "핀 크기는 검색 반경과 무관합니다."
    )


# ==========================================
# 10. 페이지 시작
# ==========================================

st.title("🐾 동물 건강")

st.caption(
    "반려동물 약물과 성분, "
    "동물종별 주의 약물, "
    "동물병원 위치를 확인하세요."
)

st.warning(
    "사람용 약을 반려동물에게 임의로 "
    "투여하지 마세요. 약물을 먹었거나 "
    "피부에 노출됐다면 수의사에게 "
    "즉시 문의하세요."
)

animal_drugs, animal_ingredients = (
    load_animal_data()
)


# ==========================================
# 11. 동물 건강 4개 탭
# ==========================================

tab_drug, tab_ing, tab_risk, tab_vet = st.tabs(
    [
        "💊 동물 약",
        "🧪 동물 약 성분",
        "⚠️ 강아지·고양이 주의 약물",
        "📍 동물병원 위치",
    ]
)


# ==========================================
# 12. 동물 약 탭
# ==========================================

with tab_drug:

    st.subheader("동물 약 찾아보기")

    species = st.radio(
        "동물 선택",
        ["전체", "강아지", "고양이"],
        horizontal=True,
        key="animal_drug_species",
    )

    q = st.text_input(
        "동물 약·성분 검색",
        placeholder="예: 플루랄라너, 외부기생충",
        key="animal_drug_q",
    )

    categories = sorted(
        animal_drugs["분류"]
        .astype(str)
        .unique()
    )

    category = st.selectbox(
        "동물 약 종류",
        ["전체 보기"] + categories,
        key="animal_drug_cat",
    )

    result = animal_drugs.copy()

    # 강아지 또는 고양이 선택 시
    # 해당 동물이 포함된 약물만 표시한다.

    if species != "전체":

        word = (
            "개"
            if species == "강아지"
            else "고양이"
        )

        result = result[
            result["대상동물"]
            .astype(str)
            .str.contains(
                word,
                regex=False,
            )
        ]

    # 약물 종류별 필터링
    if category != "전체 보기":

        result = result[
            result["분류"] == category
        ]

    # 검색어 필터링
    result = filter_rows(
        result,
        q,
        [
            "약물명",
            "분류",
            "주요성분",
            "사용영역",
        ],
    )

    st.write(
        f"검색 결과: **{len(result)}개** "
        f"/ 전체 {len(animal_drugs)}개"
    )

    if result.empty:

        st.info(
            "해당 조건의 동물 약 정보가 없습니다."
        )

    else:

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
            hide_index=True,
            use_container_width=True,
            height=310,
        )

        idx = st.selectbox(
            "자세히 볼 약물 선택",
            result.index.tolist(),
            format_func=lambda i: str(
                result.loc[i, "약물명"]
            ),
            key="animal_drug_detail",
        )

        item = result.loc[idx]

        st.write(
            f"**약물:** {item['약물명']} / "
            f"**대상 동물:** {item['대상동물']}"
        )

        st.write(
            f"**사용 영역:** {item['사용영역']}"
        )

        st.warning(
            f"주의사항: {item['주의사항']}"
        )

        if "데이터형태" in result.columns:

            st.caption(
                f"데이터 구분: {item['데이터형태']}"
            )


# ==========================================
# 13. 동물 약 성분 탭
# ==========================================

with tab_ing:

    st.subheader("동물 약 성분 사전")

    q = st.text_input(
        "성분명·영문명·설명 검색",
        placeholder="예: Fluralaner",
        key="animal_ingredient_q",
    )

    result = filter_rows(
        animal_ingredients.copy(),
        q,
        [
            "성분명",
            "영문명",
            "분류",
            "설명",
        ],
    )

    st.write(
        f"조회된 성분 **{len(result)}개 "
        f"/ 전체 {len(animal_ingredients)}개**"
    )

    if result.empty:

        st.info(
            "성분 검색 결과가 없습니다."
        )

    else:

        st.dataframe(
            result,
            hide_index=True,
            use_container_width=True,
            height=300,
        )

        idx = st.selectbox(
            "자세히 볼 성분 선택",
            result.index.tolist(),
            format_func=lambda i: str(
                result.loc[i, "성분명"]
            ),
            key="animal_ingredient_detail",
        )

        item = result.loc[idx]

        st.write(
            f"**{item['성분명']} "
            f"({item['영문명']})** — "
            f"{item['설명']}"
        )

        st.warning(
            f"주의사항: {item['주의사항']}"
        )


# ==========================================
# 14. 강아지·고양이별 주의 약물 자료
# ==========================================

# 대표적인 위험 사례만 정리한 목록이다.
# 모든 의약품의 금기 여부를 판단하는
# 완전한 목록은 아니다.

DOG_RISKS = [
    (
        "이부프로펜·나프록센 등 사람용 NSAIDs",
        "임의 투여 금지",
        "위장관 궤양·급성 신손상 위험",
        "https://www.petpoisonhelpline.com/poison/nsaids/",
    ),
    (
        "아세트아미노펜",
        "임의 투여 금지",
        "과량 노출 시 간·혈액 손상 위험",
        "https://www.aspca.org/news/protect-your-pet-top-5-toxic-dangers-your-home",
    ),
    (
        "자일리톨 함유 의약품·간식",
        "특히 주의",
        "개에게 저혈당·간 손상 위험",
        "https://www.aspca.org/news/updated-safety-warning-xylitol-how-protect-your-pets",
    ),
    (
        "슈도에페드린 등 감기약 성분",
        "임의 투여 금지",
        "심혈관·신경계 이상반응 가능",
        "https://www.aspca.org/news/can-human-allergy-medication-be-harmful-pets-our-experts-explain",
    ),
]

CAT_RISKS = [
    (
        "아세트아미노펜",
        "매우 위험",
        "소량 노출에도 심한 중독 발생 가능",
        "https://vcahospitals.com/know-your-pet/household-hazards-toxic-hazards-for-cats",
    ),
    (
        "이부프로펜·나프록센 등 NSAIDs",
        "임의 투여 금지",
        "위장관·신장 손상 위험",
        "https://www.petpoisonhelpline.com/poison/nsaids/",
    ),
    (
        "강아지용 퍼메트린 구충제",
        "고양이 사용 금지",
        "피부 노출 및 그루밍으로도 신경계 중독 위험",
        "https://vcahospitals.com/know-your-pet/household-hazards-toxic-hazards-for-cats",
    ),
    (
        "미녹시딜 외용제",
        "접촉·섭취 주의",
        "고양이에서 심장·호흡기계 이상 발생 가능",
        "https://vcahospitals.com/know-your-pet/household-hazards-toxic-hazards-for-cats",
    ),
    (
        "아스피린",
        "수의사 관리 필요",
        "고양이에서 대사·중독 위험이 커 "
        "임의 투여 금지",
        "https://www.aspca.org/news/not-all-pets-are-same-why-species-matters-pet-toxins",
    ),
]


# ==========================================
# 15. 강아지·고양이 주의 약물 탭
# ==========================================

with tab_risk:

    st.subheader(
        "동물종별 주의해야 할 약물과 제품"
    )

    species = st.radio(
        "동물종 선택",
        ["강아지", "고양이"],
        horizontal=True,
        key="risk_species",
    )

    if species == "강아지":
        info = DOG_RISKS
    else:
        info = CAT_RISKS

    table = pd.DataFrame(
        info,
        columns=[
            "성분·제품",
            "구분",
            "주의 이유",
            "근거 자료",
        ],
    )

    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
        column_config={
            "근거 자료": (
                st.column_config.LinkColumn(
                    "수의학 근거"
                )
            )
        },
    )

    st.info(
        "대표적인 위험 사례만 정리했습니다. "
        "여기에 없다고 안전한 것은 아니며, "
        "실제 투약·응급조치는 수의사가 "
        "결정해야 합니다."
    )

    st.warning(
        "의심되는 약물을 먹었거나 "
        "피부에 닿았다면 즉시 동물병원에 "
        "연락하세요. 임의로 구토를 "
        "유도하지 마세요."
    )


# ==========================================
# 16. 동물병원 위치 검색 탭
# ==========================================

with tab_vet:

    st.subheader(
        "근처 동물병원 찾기"
    )

    key = kakao_key()

    if not key:

        st.error(
            "Streamlit Secrets에 "
            "KAKAO_REST_API_KEY를 등록해 주세요."
        )

    else:

        # ----------------------------------
        # 기준 위치 검색
        # ----------------------------------

        with st.form("vet_location_form"):

            query = st.text_input(
                "검색 기준 위치",
                placeholder=(
                    "예: 둔산여고, 콘래드 서울, "
                    "대전 서구 둔산로 100"
                ),
                key="vet_query",
            )

            radius_km = st.selectbox(
                "검색 반경 (km)",
                [1, 2, 3, 5, 10],
                index=2,
                key="vet_radius",
            )

            st.caption(
                "반경 3km는 선택한 위치에서 "
                "직선거리 3,000m 이내를 뜻합니다. "
                "실제 이동거리는 아닙니다."
            )

            submitted = st.form_submit_button(
                "기준 위치 찾기",
                type="primary",
            )

        if submitted:

            if not query.strip():

                st.warning(
                    "주소 또는 장소명을 입력해 주세요."
                )

            else:

                try:

                    candidates = locate(
                        query.strip(),
                        key,
                    )

                    st.session_state[
                        "vet_candidates"
                    ] = candidates

                    st.session_state[
                        "vet_radius_choice"
                    ] = radius_km

                    st.session_state.pop(
                        "vet_results_1103",
                        None,
                    )

                    if not candidates:

                        st.warning(
                            "해당 위치를 찾지 못했습니다. "
                            "주소·장소명을 변경해 보세요."
                        )

                except (
                    requests.RequestException,
                    ValueError,
                    KeyError,
                ) as err:

                    st.error(
                        "위치 검색 오류: "
                        f"{type(err).__name__}"
                    )

        # ----------------------------------
        # 검색된 위치 후보에서 선택
        # ----------------------------------

        candidates = st.session_state.get(
            "vet_candidates", []
        )

        if candidates:

            selected_index = st.selectbox(
                "기준 위치 선택",
                range(len(candidates)),
                format_func=lambda i: (
                    f"{i+1}. "
                    f"{candidates[i]['label']}"
                ),
                key="vet_location_sel",
            )

            if st.button(
                "이 위치 주변 동물병원 검색",
                type="primary",
                key="vet_search_btn",
            ):

                place = candidates[selected_index]

                try:

                    raw = nearby_vets(
                        place["lon"],
                        place["lat"],
                        st.session_state.get(
                            "vet_radius_choice", 3
                        ),
                        key,
                    )

                    st.session_state[
                        "vet_center_1103"
                    ] = place

                    rows = []

                    for p in raw:

                        rows.append(
                            {
                                "이름": p.get(
                                    "place_name", ""
                                ),
                                "거리(m)": int(
                                    p.get("distance") or 0
                                ),
                                "전화": p.get(
                                    "phone", ""
                                ),
                                "주소": (
                                    p.get("road_address_name")
                                    or p.get(
                                        "address_name", ""
                                    )
                                ),
                                "상세정보": p.get(
                                    "place_url", ""
                                ),
                                "lat": float(p["y"]),
                                "lon": float(p["x"]),
                            }
                        )

                    st.session_state[
                        "vet_results_1103"
                    ] = rows

                except (
                    requests.RequestException,
                    ValueError,
                    KeyError,
                ) as err:

                    st.error(
                        "동물병원 검색 오류: "
                        f"{type(err).__name__}"
                    )

        # ----------------------------------
        # 동물병원 검색 결과 출력
        # ----------------------------------

        rows = st.session_state.get(
            "vet_results_1103"
        )

        if rows is not None:

            if not rows:

                st.info(
                    "선택한 반경에서 동물병원을 "
                    "찾지 못했습니다."
                )

            else:

                df = pd.DataFrame(rows)

                st.success(
                    f"동물병원 {len(df)}곳을 "
                    "찾았습니다."
                )

                if len(df) >= 45:

                    st.caption(
                        "최대 45곳까지 조회합니다. "
                        "다른 결과가 더 있을 수 있습니다."
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
                    hide_index=True,
                    use_container_width=True,
                    height=330,
                    column_config={
                        "상세정보": (
                            st.column_config.LinkColumn(
                                "카카오맵 열기"
                            )
                        )
                    },
                )

                # 검색 기준 위치와
                # 동물병원 위치를 지도에 표시한다.

                show_map(
                    df,
                    st.session_state[
                        "vet_center_1103"
                    ],
                )
