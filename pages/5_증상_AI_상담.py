import streamlit as st

from openai import OpenAI

from site_theme import apply_style
from drug_data_tools import load_data


apply_style()

st.title("💬 증상별 AI 의약품 정보 상담")

st.caption(
    "증상을 설명하면 일반적인 관리 방법과 "
    "의약품 성분군을 안내합니다. "
    "진단·처방은 하지 않습니다."
)

st.warning(
    "숨이 차거나 가슴 통증, 의식 변화, "
    "심한 알레르기 반응이 있으면 "
    "채팅 대신 119 또는 응급실을 이용하세요."
)


# ==========================================
# 1. OpenAI API 키 확인
# ==========================================

try:
    key = st.secrets.get(
        "OPENAI_API_KEY",
        "",
    )

except (FileNotFoundError, KeyError):
    key = ""


if not key:

    st.info(
        "Streamlit Cloud → Settings → Secrets에 "
        "OPENAI_API_KEY를 등록하면 작동합니다."
    )

    st.stop()


# ==========================================
# 2. 사용자 설정
# ==========================================

age = st.selectbox(
    "상담 대상",
    [
        "성인(만 19세 이상)",
        "청소년·어린이",
        "고령자",
        "반려동물",
    ],
)

include_records = st.checkbox(
    "나의 약·질병 목록을 상담에 참고하기"
)

consent = st.checkbox(
    "입력한 증상 및 선택한 정보가 "
    "외부 OpenAI API로 전송되는 데 동의합니다."
)


# ==========================================
# 3. 대화 기록
# ==========================================

if "ai_history" not in st.session_state:
    st.session_state.ai_history = []


if st.button("대화 내역 지우기"):

    st.session_state.ai_history = []

    st.rerun()


for item in st.session_state.ai_history:

    with st.chat_message(item["role"]):

        st.markdown(
            item["content"]
        )


# ==========================================
# 4. 사용자 질문 입력
# ==========================================

prompt = st.chat_input(
    "예: 목이 아프고 콧물이 나요. "
    "어떤 성분을 확인하면 좋을까요?"
)


if prompt:

    if not consent:

        st.warning(
            "전송 동의에 체크해야 "
            "AI 상담을 시작할 수 있습니다."
        )

        st.stop()

    if len(prompt) > 1200:

        st.error(
            "증상 설명은 1,200자 이내로 입력해 주세요."
        )

        st.stop()

    st.session_state.ai_history.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)


    # ======================================
    # 5. 기존 약·질병 목록 참고
    # ======================================

    context = f"상담 대상: {age}."

    if include_records:

        meds = st.session_state.get(
            "my_drugs",
            [],
        )

        conditions = st.session_state.get(
            "my_conditions",
            [],
        )

        context += (
            f" 사용자가 입력한 복용 약 목록: {meds}; "
            f"질병·증상 기록: {conditions}."
        )


    # ======================================
    # 6. 교육용 의약품 데이터 참고
    # ======================================

    try:

        catalog_df, _ = load_data()

        catalog = "\n".join(
            (
                f"{row['제품명']} | "
                f"분류: {row['카테고리']} | "
                f"성분: {row['성분']}"
            )
            for _, row in catalog_df.iterrows()
        )

    except (
        FileNotFoundError,
        ValueError,
        KeyError,
    ):

        catalog = (
            "제품 목록을 불러오지 못했습니다."
        )


    # ======================================
    # 7. AI 답변 원칙
    # ======================================

    instructions = """
당신은 한국어 건강정보 교육 도우미다.

진단·처방·용량·복용 간격 결정은 하지 않는다.

증상에 대해 일반적인 자가관리,
약사에게 확인할 일반의약품 성분군,
주의할 중복 성분과 주요 금기를 간결하게 알려준다.

특정 제품을 '복용하라'고 확정 권유하지 않고,
처방약이나 전문의약품을 권하지 않는다.

위험 증상이면 즉시 119·응급진료를 안내한다.

임신·수유·기저질환·동시 복용약 등
필요한 질문을 먼저 한다.

어린이·청소년·고령자에게는
일반 성인 복용법을 적용하지 않는다.

동물에게는 사람 약을 권하지 않고
수의사 상담을 권한다.

입력하지 않은 병력을 임의로 만들어내지 않는다.

제공된 제품 목록은 교육용 CSV이며
의약품 허가·일반약 여부가 검증되지 않았다.

증상과 관련된 성분이 실제 제품 목록에 존재한다면
최대 2개를 '관련 성분을 포함한 참고 제품'으로만
소개하고 구매·복용 지시는 하지 않는다.

목록에 없는 제품을 지어내지 않는다.

마지막에는 약사 또는 의료진 확인을 권한다.
"""


    # ======================================
    # 8. AI API 연결
    # ======================================

    try:

        client = OpenAI(
            api_key=key,
            timeout=25.0,
        )

        conversation = (
            st.session_state.ai_history[-6:]
        )

        current = [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in conversation
        ]

        current[-1]["content"] = (
            context
            + "\n교육용 제품 목록(검증되지 않음):\n"
            + catalog[:8500]
            + "\n사용자 질문: "
            + prompt
        )

        with st.spinner(
            "건강 정보를 확인하고 있습니다..."
        ):

            response = client.responses.create(
                model="gpt-4.1-mini",
                instructions=instructions,
                input=current,
                max_output_tokens=500,
                store=False,
            )

        answer = (
            response.output_text
            or "답변을 생성하지 못했습니다. 다시 시도해 주세요."
        )

    except Exception as error:

        st.error(
            "AI 연결 중 오류가 발생했습니다. "
            "API 키·사용량·결제 설정을 확인하세요."
        )

        st.caption(
            type(error).__name__
        )

    else:

        st.session_state.ai_history.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        with st.chat_message("assistant"):

            st.markdown(answer)
