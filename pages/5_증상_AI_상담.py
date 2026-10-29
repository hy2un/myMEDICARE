import streamlit as st
from google import genai
from google.genai import types


# ==========================================
# 1. 페이지 기본 화면
# ==========================================

st.title("💬 증상 AI 상담")

st.caption(
    "Google Gemini로 증상 관리 방법과 의약품 성분 정보를 알아봅니다. "
    "진단·처방 서비스는 아닙니다."
)

st.warning(
    "호흡곤란, 심한 가슴 통증, 의식 변화 등 응급 증상이 있으면 "
    "AI 상담 대신 119나 응급실을 이용하세요."
)


# ==========================================
# 2. Gemini API 키 확인
# ==========================================

try:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
except (FileNotFoundError, KeyError):
    api_key = ""

if not api_key:
    st.error("Gemini API 키가 등록되지 않았습니다.")
    st.code(
        'GEMINI_API_KEY = "발급받은_API_키"',
        language="toml",
    )
    st.caption(
        "Streamlit Cloud → Manage app → "
        "Settings → Secrets에 등록하세요."
    )
    st.stop()


# ==========================================
# 3. 상담 옵션과 정보 전송 동의
# ==========================================

target = st.selectbox(
    "상담 대상",
    ["성인", "청소년·어린이", "고령자", "반려동물"],
)

use_my_records = st.checkbox(
    "나의 약·나의 질병에 등록한 항목을 참고하기",
    value=False,
)

consent = st.checkbox(
    "상담 내용이 Google Gemini API로 전송되는 데 동의합니다.",
    value=False,
)

st.caption(
    "실명, 주소, 전화번호 등 개인정보는 입력하지 마세요. "
    "무료 API 등급에서는 입력 내용이 "
    "Google 제품 개선에 활용될 수 있습니다."
)


# ==========================================
# 4. 이전 대화 표시
# ==========================================

if "gemini_history" not in st.session_state:
    st.session_state.gemini_history = []

if st.button("대화 내용 지우기"):
    st.session_state.gemini_history = []
    st.rerun()

for item in st.session_state.gemini_history:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])


# ==========================================
# 5. 새로운 질문 처리
# ==========================================

question = st.chat_input(
    "예: 콧물과 목 통증이 있어요. "
    "약사에게 어떤 성분을 문의하면 될까요?"
)

if question:

    if not consent:
        st.warning(
            "Gemini API 전송 동의를 먼저 선택해 주세요."
        )
        st.stop()

    if len(question) > 1200:
        st.warning(
            "질문은 1,200자 이내로 입력해 주세요."
        )
        st.stop()

    with st.chat_message("user"):
        st.markdown(question)

    # 사용자 정보
    extra = f"상담 대상: {target}\n"

    if use_my_records:

        my_drugs = st.session_state.get(
            "my_drugs", []
        )

        my_conditions = st.session_state.get(
            "my_conditions", []
        )

        extra += (
            f"사용자가 등록한 약 이름: "
            f"{my_drugs[:20]}\n"
        )

        extra += (
            f"사용자가 등록한 질병·증상: "
            f"{my_conditions[:20]}\n"
        )

    else:
        extra += (
            "복용 약 및 질병 정보는 "
            "별도로 제공되지 않았습니다.\n"
        )

    # Gemini의 답변 원칙
    system_instruction = """
당신은 한국어로 답하는 건강정보 교육용 상담 도우미입니다.

- 사용자의 증상과 관련된 일반적인 자가 관리 방법을 설명하세요.
- 의약품은 일반적인 성분군을 소개할 수 있지만
  진단, 처방, 용량, 복용 간격을 결정하지 마세요.
- 특정 약의 효과, 음식과의 상호작용, 병용 가능 여부를
  확인할 수 없다면 단정하지 마세요.
- 약물 중복 복용과 임신·수유·기저질환 등의 위험 요인을
  확인할 필요가 있으면 질문하세요.
- 어린이, 고령자, 반려동물에게 사람 성인용 약을
  임의로 권하지 마세요.
- 반려동물은 수의사 상담을 안내하세요.
- 증상이 심하거나 위험 신호가 있다면
  진료나 응급 대응을 권하세요.
- 식단 질문에는 일반적인 식사 원칙을 설명하고
  개인별 질환·약물에 따른 상담 필요성을 알려주세요.
- 실제 진료나 약사 상담을 대신하지 않는다는 점을
  명확히 하세요.
- 답변은 이해하기 쉬운 한국어로 간결하게 작성하세요.
"""

    # 이전 대화를 Gemini 형식으로 변환
    contents = []

    for item in st.session_state.gemini_history[-8:]:

        role = (
            "user"
            if item["role"] == "user"
            else "model"
        )

        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part(
                        text=item["content"]
                    )
                ],
            )
        )

    # 현재 질문 추가
    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=extra + "\n질문: " + question
                )
            ],
        )
    )

    # ======================================
    # 6. Gemini API 호출
    # ======================================

    try:

        with st.spinner(
            "Gemini가 답변을 작성하고 있습니다..."
        ):

            client = genai.Client(
                api_key=api_key
            )

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=1400,
                ),
            )

            answer = (
                response.text
                or "답변이 생성되지 않았습니다. "
                   "질문을 바꿔 다시 시도해 주세요."
            )

    except Exception as error:

        st.error(
            "Gemini 연결에 실패했습니다. "
            "API 키, 모델 접근 권한 또는 "
            "무료 사용 한도를 확인하세요."
        )

        st.caption(
            f"오류 유형: {type(error).__name__}"
        )

    else:

        st.session_state.gemini_history.extend(
            [
                {
                    "role": "user",
                    "content": question,
                },
                {
                    "role": "assistant",
                    "content": answer,
                },
            ]
        )

        with st.chat_message("assistant"):
            st.markdown(answer)
