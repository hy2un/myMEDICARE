"""My MediCare | 동물 건강 페이지 전체 코드

기존 animal_drug_data.csv, animal_ingredient_data.csv를 그대로 사용합니다.
강아지/고양이/대상 동물 미확정 조회, 주의 약물, 장소명 기반 동물병원 검색.
"""

from html import escape
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st


# =========================================================
# 1. 이 페이지에서만 적용하는 민트색·둥근 디자인
#    다른 페이지나 main.py를 수정할 필요가 없습니다.
# =========================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #fbfdfb;
    }
    h1, h2, h3 {
        color: #183e35 !important;
        letter-spacing: -0.03em;
    }
    /* 상단 전환 탭: 둥근 연민트색 바탕과 알약형 버튼 */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        gap: 9px;
        padding: 10px;
        border: 1px solid #d1e8da;
        border-radius: 25px;
        background: #edf8f1;
        box-shadow: 0 3px 13px rgba(17, 95, 69, 0.04);
        overflow-x: auto;
    }
    .stTabs [data-baseweb="tab-list"] button[role="tab"] {
        flex-shrink: 0;
        padding: 10px 17px;
        border: 1px solid #d7ebdf !important;
        border-radius: 999px !important;
        background: #ffffff !important;
        color: #356b57 !important;
        font-size: 0.94rem;
        font-weight: 650;
        box-shadow: 0 2px 5px rgba(12, 81, 56, 0.03);
        transition: background-color 120ms ease;
    }
    .stTabs [data-baseweb="tab-list"] button[role="tab"]:hover {
        background: #dff3e8 !important;
        color: #105943 !important;
    }
    .stTabs [data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] {
        background: #137f62 !important;
        color: #ffffff !important;
        border-color: #137f62 !important;
        box-shadow: 0 3px 9px rgba(19, 127, 98, 0.17);
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 20px;
    }
    /* 둥근 안내 카드: 사람용 약 주의문 및 약물별 안내에 사용 */
    .animal-notice {
        margin: 12px 0 17px 0;
        padding: 18px 21px;
        background: linear-gradient(120deg, #e8f7ef, #f3fcf6);
        border: 1px solid #cce8d9;
        border-left: 5px solid #19866a;
        border-radius: 23px;
        color: #235548;
        box-shadow: 0 4px 12px rgba(12, 99, 70, 0.035);
        line-height: 1.7;
    }
    .animal-notice-title {
        font-weight: 750;
        font-size: 1.04rem;
        color: #11634f;
        margin-bottom: 5px;
    }
    .animal-notice-body {
        font-size: 0.94rem;
        color: #315d50;
    }
    /* 중독 의심 긴급 경고만 위험성을 알리기 위해 붉은색 유지 */
    .animal-notice.animal-urgent {
        border-color: #f2d9d4;
        border-left-color: #c75246;
        background: #fff5f2;
    }
    .animal-notice.animal-urgent .animal-notice-title {
        color: #a6382d;
    }
    .animal-notice.animal-urgent .animal-notice-body {
        color: #803d35;
    }
    /* 입력창·선택창·버튼을 부드러운 둥근 형태로 통일 */
    .stTextInput input {
        border-radius: 15px !important;
        background: #f6faf8 !important;
        border-color: #dcece3 !important;
    }
    div[data-baseweb="select"] > div {
        border-radius: 15px !important;
        background: #f6faf8 !important;
        border-color: #dcece3 !important;
    }
    .stButton button, .stFormSubmitButton button {
        border-radius: 999px !important;
        padding-left: 19px !important;
        padding-right: 19px !important;
        font-weight: 650 !important;
    }
    .stButton button[kind="primary"],
    .stFormSubmitButton button[kind="primary"] {
        background: #137f62 !important;
        border-color: #137f62 !important;
        color: white !important;
    }
    .stButton button[kind="primary"]:hover,
    .stFormSubmitButton button[kind="primary"]:hover {
        background: #0c6650 !important;
        border-color: #0c6650 !important;
    }
    /* 표, 일반 시스템 메시지, 데이터 수치 표시 */
    div[data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
    }
    div[data-testid="stMetric"] {
        border-radius: 18px;
        padding: 10px 13px;
        border: 1px solid #e0eee6;
        background: #f2faf5;
    }
    div[data-testid="stAlert"] {
        border-radius: 16px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

ROOT = Path(__file__).resolve().parent.parent


def show_notice(title, body, urgent=False):
    """CSV 내용도 안전하게 표시하는 둥근 안내 카드."""
    css_class = "animal-notice animal-urgent" if urgent else "animal-notice"
    st.markdown(
        f'<div class="{css_class}">'
        f'<div class="animal-notice-title">{escape(str(title))}</div>'
        f'<div class="animal-notice-body">{escape(str(body))}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


# =========================================================
# 2. CSV 데이터 조회
# =========================================================
@st.cache_data(show_spinner=False)
def load_animal_data():
    drug_path = ROOT / "animal_drug_data.csv"
    ingredient_path = ROOT / "animal_ingredient_data.csv"

    if not drug_path.is_file() or not ingredient_path.is_file():
        raise FileNotFoundError("동물 약·성분 CSV가 GitHub 최상위 폴더에 없습니다.")

    drug_df = pd.read_csv(drug_path, encoding="utf-8-sig").fillna("")
    ingredient_df = pd.read_csv(ingredient_path, encoding="utf-8-sig").fillna("")

    required_drug = {"약물명", "분류", "주요성분", "대상동물", "사용영역", "주의사항"}
    required_ing = {"성분명", "영문명", "분류", "설명", "주의사항"}
    if not required_drug.issubset(drug_df.columns):
        raise ValueError("동물 약 CSV의 열 이름을 확인해 주세요.")
    if not required_ing.issubset(ingredient_df.columns):
        raise ValueError("동물 성분 CSV의 열 이름을 확인해 주세요.")

    return drug_df, ingredient_df


def filter_rows(df, keyword, columns):
    """여러 열에서 입력한 검색어가 포함된 행만 찾는다."""
    keyword = keyword.strip()
    if not keyword:
        return df
    mask = df[columns].astype(str).apply(
        lambda col: col.str.contains(keyword, case=False, regex=False, na=False)
    ).any(axis=1)
    return df.loc[mask].copy()


# =========================================================
# 3. 카카오 지도 API
# =========================================================
def get_kakao_key():
    try:
        return st.secrets.get("KAKAO_REST_API_KEY", "")
    except (FileNotFoundError, KeyError):
        return ""


def kakao_search(endpoint, params, key):
    response = requests.get(
        f"https://dapi.kakao.com/v2/local/search/{endpoint}.json",
        params=params,
        headers={"Authorization": f"KakaoAK {key}"},
        timeout=12,
    )
    response.raise_for_status()
    return response.json()


def locate(query, key):
    """주소를 우선 조회하고 결과가 없다면 건물·기관 이름으로 조회."""
    candidates = []
    result = kakao_search("address", {"query": query}, key)
    for item in result.get("documents", [])[:8]:
        candidates.append({
            "label": item.get("address_name", "") or query,
            "lat": float(item["y"]),
            "lon": float(item["x"]),
        })

    if not candidates:
        result = kakao_search("keyword", {"query": query, "size": 15}, key)
        for item in result.get("documents", []):
            address = item.get("road_address_name") or item.get("address_name", "")
            name = item.get("place_name", "")
            candidates.append({
                "label": f"{name} — {address}",
                "lat": float(item["y"]),
                "lon": float(item["x"]),
            })
    return candidates


def nearby_vets(lon, lat, radius_km, key):
    """중심점에서 직선거리 내의 동물병원을 최대 45곳 조회."""
    found = {}
    for page in range(1, 4):
        result = kakao_search(
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
        for place in result.get("documents", []):
            combined = place.get("place_name", "") + " " + place.get("category_name", "")
            if "동물병원" not in combined and "수의" not in combined:
                continue
            place_id = place.get("id") or place.get("place_name", "")
            found[place_id] = place
        if result.get("meta", {}).get("is_end", True):
            break
    return sorted(found.values(), key=lambda place: int(place.get("distance") or 0))


def make_pin(color):
    """큰 원 대신 지도에서 사용하는 작은 핀 아이콘."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="48" '
        'viewBox="0 0 36 48">'
        '<path d="M18 2C9 2 2 9 2 18c0 12 16 28 16 28s16-16 16-28'
        f'C34 9 27 2 18 2Z" fill="{color}" stroke="white" stroke-width="2"/>'
        '<circle cx="18" cy="18" r="7" fill="white"/>'
        '</svg>'
    )
    return {
        "url": "data:image/svg+xml;charset=utf-8," + quote(svg),
        "width": 36,
        "height": 48,
        "anchorX": 18,
        "anchorY": 48,
    }


def show_map(df, center):
    points = df[["이름", "lat", "lon"]].copy()
    points["icon"] = [make_pin("#e85f57") for _ in range(len(points))]
    origin = pd.DataFrame([{
        "이름": "검색 기준 위치",
        "lat": center["lat"],
        "lon": center["lon"],
        "icon": make_pin("#137f62"),
    }])
    all_points = pd.concat([points, origin], ignore_index=True)
    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(
            latitude=center["lat"], longitude=center["lon"], zoom=13, pitch=0,
        ),
        layers=[
            pdk.Layer(
                "IconLayer",
                all_points,
                get_icon="icon",
                get_position="[lon, lat]",
                get_size=25,
                size_scale=1,
                pickable=True,
            ),
        ],
        tooltip={"text": "{이름}"},
    )
    st.pydeck_chart(deck, use_container_width=True)
    st.caption("🟢 초록색 핀: 검색 기준 위치 · 🔴 빨간색 핀: 동물병원")


# =========================================================
# 4. 실제 페이지
# =========================================================
st.title("🐾 동물 건강")
st.caption("반려동물 약과 성분, 동물종별 주의 약물, 주변 동물병원까지 확인하세요.")
show_notice(
    "💚 반려동물 약물 안전 안내",
    "사람용 약을 반려동물에게 임의로 투여하지 마세요. "
    "약물을 먹었거나 피부에 노출됐다면 수의사에게 즉시 문의하세요.",
)

try:
    animal_drugs, animal_ingredients = load_animal_data()
except (FileNotFoundError, ValueError, OSError, UnicodeError, pd.errors.ParserError) as err:
    st.error(f"동물 약 데이터 확인 필요: {err}")
    st.stop()

# 상단 탭은 이 페이지의 CSS로 모두 둥근 녹색 버튼 형태로 표시됩니다.
tab_drug, tab_ing, tab_risk, tab_vet = st.tabs([
    "💊 동물 약",
    "🧪 동물 약 성분",
    "⚠️ 강아지·고양이 주의 약물",
    "📍 동물병원 위치",
])


# =========================================================
# 5. 동물 약: 강아지·고양이·대상 동물 미확정 구분
# =========================================================
with tab_drug:
    st.subheader("동물 약 찾아보기")

    species_text = animal_drugs["대상동물"].astype(str)
    dog_mask = species_text.str.contains("개", regex=False)
    cat_mask = species_text.str.contains("고양이", regex=False)
    unconfirmed_mask = ~(dog_mask | cat_mask)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("강아지만 명시", int((dog_mask & ~cat_mask).sum()))
    c2.metric("고양이만 명시", int((~dog_mask & cat_mask).sum()))
    c3.metric("두 동물 모두 명시", int((dog_mask & cat_mask).sum()))
    c4.metric("대상 동물 미확정", int(unconfirmed_mask.sum()))

    show_notice(
        "🐕 🐈 동물별 분류 안내",
        "‘대상 동물 미확정’은 자료에 동물종이 명시되지 않거나 ‘수의사 판단’으로 표시된 제제입니다. "
        "다른 동물 전용이라는 뜻이 아니며, 사용 가능 여부는 허가정보와 수의사 판단을 확인해야 합니다.",
    )

    species = st.radio(
        "대상 동물 구분",
        ["전체", "강아지", "고양이", "대상 동물 미확정"],
        horizontal=True,
        key="animal_drug_species",
    )
    keyword = st.text_input(
        "동물 약·성분 검색",
        placeholder="예: 플루랄라너, 외부기생충",
        key="animal_drug_keyword",
    )
    categories = sorted(animal_drugs["분류"].astype(str).unique().tolist())
    category = st.selectbox(
        "동물 약 종류", ["전체 보기"] + categories, key="animal_drug_category"
    )

    result = animal_drugs.copy()
    if species == "강아지":
        result = result.loc[dog_mask].copy()
    elif species == "고양이":
        result = result.loc[cat_mask].copy()
    elif species == "대상 동물 미확정":
        result = result.loc[unconfirmed_mask].copy()

    if category != "전체 보기":
        result = result.loc[result["분류"] == category].copy()
    result = filter_rows(result, keyword, ["약물명", "분류", "주요성분", "사용영역"])
    st.write(f"조회된 동물 약 **{len(result)}개 / 전체 {len(animal_drugs)}개**")

    if result.empty:
        st.info("검색 결과가 없습니다. 동물 구분 또는 검색 조건을 변경해 주세요.")
    else:
        st.dataframe(
            result[["약물명", "분류", "주요성분", "대상동물", "사용영역"]],
            hide_index=True, use_container_width=True, height=330,
        )
        selected_idx = st.selectbox(
            "자세히 볼 약물 선택",
            result.index.tolist(),
            format_func=lambda i: str(result.loc[i, "약물명"]),
            key="animal_drug_detail",
        )
        selected = result.loc[selected_idx]
        st.write(f"**약물:** {selected['약물명']}   |   **대상 동물:** {selected['대상동물']}")
        st.write(f"**사용 영역:** {selected['사용영역']}")
        show_notice("🌿 약물 사용 시 주의사항", selected["주의사항"])
        if "데이터형태" in result.columns:
            st.caption(f"데이터 구분: {selected['데이터형태']}")


# =========================================================
# 6. 동물 약 성분 사전
# =========================================================
with tab_ing:
    st.subheader("동물 약 성분 사전")
    keyword = st.text_input(
        "성분명·영문명·설명 검색",
        placeholder="예: Fluralaner, 외부기생충",
        key="animal_ingredient_keyword",
    )
    result = filter_rows(
        animal_ingredients.copy(), keyword, ["성분명", "영문명", "분류", "설명"]
    )
    st.write(f"조회된 성분 **{len(result)}개 / 전체 {len(animal_ingredients)}개**")

    if result.empty:
        st.info("성분 검색 결과가 없습니다.")
    else:
        st.dataframe(result, hide_index=True, use_container_width=True, height=320)
        selected_idx = st.selectbox(
            "자세히 볼 성분 선택",
            result.index.tolist(),
            format_func=lambda i: str(result.loc[i, "성분명"]),
            key="animal_ingredient_detail",
        )
        selected = result.loc[selected_idx]
        st.write(f"**{selected['성분명']} ({selected['영문명']})** — {selected['설명']}")
        show_notice("🌿 해당 성분의 주의사항", selected["주의사항"])


# =========================================================
# 7. 강아지·고양이 주의 약물(대표 사례)
# =========================================================
DOG_RISKS = [
    (
        "이부프로펜·나프록센 등 사람용 NSAIDs", "임의 투여 금지",
        "위장관 궤양·급성 신손상 위험",
        "https://www.petpoisonhelpline.com/poison/nsaids/",
    ),
    (
        "아세트아미노펜", "임의 투여 금지",
        "과량 노출 시 간·혈액 손상 위험",
        "https://www.aspca.org/news/protect-your-pet-top-5-toxic-dangers-your-home",
    ),
    (
        "자일리톨 함유 의약품·간식", "특히 주의",
        "개에게 저혈당·간 손상 위험",
        "https://www.aspca.org/news/updated-safety-warning-xylitol-how-protect-your-pets",
    ),
    (
        "슈도에페드린 등 감기약 성분", "임의 투여 금지",
        "심혈관·신경계 이상반응 가능",
        "https://www.aspca.org/news/can-human-allergy-medication-be-harmful-pets-our-experts-explain",
    ),
]
CAT_RISKS = [
    (
        "아세트아미노펜", "매우 위험",
        "소량 노출에도 심한 중독 발생 가능",
        "https://vcahospitals.com/know-your-pet/household-hazards-toxic-hazards-for-cats",
    ),
    (
        "이부프로펜·나프록센 등 NSAIDs", "임의 투여 금지",
        "위장관·신장 손상 위험",
        "https://www.petpoisonhelpline.com/poison/nsaids/",
    ),
    (
        "강아지용 퍼메트린 구충제", "고양이 사용 금지",
        "피부 노출 및 그루밍으로도 신경계 중독 위험",
        "https://vcahospitals.com/know-your-pet/household-hazards-toxic-hazards-for-cats",
    ),
    (
        "미녹시딜 외용제", "접촉·섭취 주의",
        "고양이에서 심장·호흡기계 이상 발생 가능",
        "https://vcahospitals.com/know-your-pet/household-hazards-toxic-hazards-for-cats",
    ),
    (
        "아스피린", "수의사 관리 필요",
        "고양이에서 대사·중독 위험이 커 임의 투여 금지",
        "https://www.aspca.org/news/not-all-pets-are-same-why-species-matters-pet-toxins",
    ),
]

with tab_risk:
    st.subheader("강아지·고양이별 주의해야 할 약물")
    species = st.radio(
        "동물종 선택", ["강아지", "고양이"], horizontal=True, key="animal_risk_species"
    )
    risk_data = DOG_RISKS if species == "강아지" else CAT_RISKS
    risk_table = pd.DataFrame(
        risk_data, columns=["성분·제품", "구분", "주의 이유", "근거 자료"]
    )
    st.dataframe(
        risk_table, hide_index=True, use_container_width=True,
        column_config={"근거 자료": st.column_config.LinkColumn("수의학 참고자료")},
    )
    show_notice(
        "🌿 위험 약물 목록 안내",
        "대표적인 위험 사례만 정리했습니다. 목록에 없다고 안전한 것은 아닙니다. "
        "동물종, 용량, 제품 제형에 따라 위험성이 달라질 수 있습니다.",
    )
    show_notice(
        "⚠️ 중독이 의심되면 즉시 동물병원에 연락하세요",
        "의심되는 약물을 먹었거나 피부에 닿았다면 즉시 동물병원에 연락하고 "
        "임의로 구토를 유도하지 마세요.",
        urgent=True,
    )


# =========================================================
# 8. 동물병원: 서울 공공기관 예시, 주소/장소명, 작은 지도 핀
# =========================================================
with tab_vet:
    st.subheader("근처 동물병원 찾기")
    show_notice(
        "📍 위치 검색 방법",
        "주소나 장소명을 입력한 뒤 검색된 후보에서 기준 위치를 선택하세요. "
        "검색 반경은 직선거리이며 실제 자동차·도보 이동거리와 다릅니다.",
    )

    key = get_kakao_key()
    if not key:
        st.error("Streamlit Secrets에 KAKAO_REST_API_KEY를 등록해 주세요.")
    else:
        with st.form("vet_location_form"):
            query = st.text_input(
                "검색 기준 위치",
                placeholder="예: 서울시청, 서울특별시 중구 세종대로 110",
                key="vet_location_query",
            )
            st.caption("장소명 예시: 국회의사당 · 서울중앙지방법원 · 서울대학교")
            radius_km = st.selectbox(
                "검색 반경 (km)", [1, 2, 3, 5, 10], index=2, key="vet_radius_km"
            )
            st.caption(
                f"반경 {radius_km}km는 기준 위치로부터 직선거리 "
                f"{radius_km * 1000:,}m 이내를 의미합니다."
            )
            submitted = st.form_submit_button("기준 위치 찾기", type="primary")

        if submitted:
            if not query.strip():
                st.warning("주소 또는 장소명을 입력해 주세요.")
            else:
                try:
                    candidates = locate(query.strip(), key)
                    st.session_state["vet_candidates"] = candidates
                    st.session_state["vet_radius_choice"] = radius_km
                    st.session_state.pop("vet_results_mint", None)
                    if not candidates:
                        st.info("위치를 찾지 못했습니다. 주소나 장소명을 변경해 주세요.")
                except (requests.RequestException, ValueError, KeyError) as err:
                    st.error(f"위치 검색 중 오류가 발생했습니다: {type(err).__name__}")

        candidates = st.session_state.get("vet_candidates", [])
        if candidates:
            selected_idx = st.selectbox(
                "기준 위치 선택",
                range(len(candidates)),
                format_func=lambda i: f"{i + 1}. {candidates[i]['label']}",
                key="vet_location_selected",
            )
            if st.button("이 위치 주변 동물병원 검색", type="primary", key="vet_search_button"):
                center = candidates[selected_idx]
                try:
                    raw = nearby_vets(
                        center["lon"], center["lat"],
                        st.session_state.get("vet_radius_choice", 3), key,
                    )
                    rows = []
                    for place in raw:
                        rows.append({
                            "이름": place.get("place_name", ""),
                            "거리(m)": int(place.get("distance") or 0),
                            "전화": place.get("phone", ""),
                            "주소": place.get("road_address_name") or place.get("address_name", ""),
                            "상세정보": place.get("place_url", ""),
                            "lat": float(place["y"]),
                            "lon": float(place["x"]),
                        })
                    st.session_state["vet_center_mint"] = center
                    st.session_state["vet_results_mint"] = rows
                except (requests.RequestException, ValueError, KeyError) as err:
                    st.error(f"동물병원 검색 중 오류가 발생했습니다: {type(err).__name__}")

        rows = st.session_state.get("vet_results_mint")
        if rows is not None:
            if not rows:
                st.info("선택한 반경에서 동물병원을 찾지 못했습니다.")
            else:
                df = pd.DataFrame(rows)
                st.success(f"동물병원 {len(df)}곳을 찾았습니다.")
                if len(df) >= 45:
                    st.caption("최대 45곳까지 조회합니다. 다른 결과가 더 있을 수 있습니다.")
                st.dataframe(
                    df[["이름", "거리(m)", "전화", "주소", "상세정보"]],
                    hide_index=True, use_container_width=True, height=330,
                    column_config={
                        "상세정보": st.column_config.LinkColumn("카카오맵 열기")
                    },
                )
                show_map(df, st.session_state["vet_center_mint"])
