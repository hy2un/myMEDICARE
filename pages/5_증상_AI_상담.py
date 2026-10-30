import streamlit as st
from google import genai
from google.genai import types


# ==========================================
# 1. 채팅창 디자인
# ==========================================

st.markdown("""
<style>

/* 상단 안내 배너 */

.mc-chat-header {
    background: linear-gradient(
        110deg, #e6f6ec, #f5fbf7
    );
    border: 1px solid #d1e9db;
    border-radius: 18px;
    padding: 18px 22px;
    margin: 8px 0 14px;
    color: #176d58;
}

.mc-chat-header strong {
    font-size: 22px;
    font-weight: 800;
    display: block;
    margin-bottom: 8px;
}

.mc-chat-header p {
    margin: 0;
    color: #527767;
    font-size: 15px;
}

/* 민트색 질문 입력 영역 */

.st-key-gemini_chat_area {
    background: #e9f7ef;
    border: 1px solid #cee8d8;
    border-radius: 20px;
    padding: 18px 20px;
    margin: 12px 0 16px;
}

/* 질문 입력창 */

.st-key-gemini_chat_area textarea {
    background: #ffffff !important;
    border-radius: 14px !important;
    border: 1.5px solid #a4d8b8 !important;
    color: #263e36 !important;
}

/* 초록색 전송 버튼 */

.st-key-gemini_chat_area
[data-testid="stFormSubmitButton"] button {
    background: #147f66 !important;
    border: 1px solid #147f66 !important;
    border-radius: 14px !important;
    color: white !important;
    font-weight: 800 !important;
    min-height: 48px;
}

.st-key-gemini_chat_area
[data-testid="stFormSubmitButton"] button:hover {
    background: #0c6451 !important;
    border-color: #0c6451 !important;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 상단 화면
# ==========================================

st.title("💬 증상 AI 상담")

st.markdown("""
<div class="mc-chat-header">
    <strong>무엇이 궁금하신가요?</strong>
    <p>
        증상 관리, 식단, 약물 성분에 대해
        질문해 보세요.
    </p>
</div>
""", unsafe_allow_html=True)

st.caption(
    "질문을 보내면 내용이 Google Gemini API로 전송됩니다. "
    "개인정보는 입력하지 마세요."
)


# ==========================================
# 3. Gemini API 키 확인
# ==========================================

try:
    api_key = st.secrets.get(
        "GEMINI_API_KEY", ""
    )
except (FileNotFoundError, KeyError):
    api_key = ""

if not api_key:
    st.error(
        "Streamlit Secrets에 GEMINI_API_KEY를 등록하세요."
    )
    st.stop()


# ==========================================
# 4. 대화 기록 초기화
# ==========================================

if "gemini_history" not in st.session_state:
    st.session_state.gemini_history = []


# ==========================================
# 5. 상단 질문 입력창
# ==========================================

with st.container(key="gemini_chat_area"):

    with st.form(
        "gemini_chat_form",
        clear_on_submit=True
    ):

        question = st.text_area(
            "💬 질문 입력",
            placeholder=(
                "예: 콧물이 나고 목이 아파요. "
                "어떤 성분을 확인하면 될까요?"
            ),
            height=110,
            max_chars=1500,
        )

        send = st.form_submit_button(
            "질문 보내기",
            type="primary",
            use_container_width=True,
        )


# ==========================================
# 6. 상담 설정
# ==========================================

with st.expander(
    "상담 설정 · 선택 사항",
    expanded=False
):

    target = st.selectbox(
        "상담 대상",
        [
            "성인",
            "청소년·어린이",
            "고령자",
            "반려동물",
        ],
        key="gemini_target",
    )

    use_records = st.checkbox(
        "나의 약·질병 목록을 상담에 참고하기",
        value=False,
        key="gemini_records",
    )

    st.caption(
        "이 옵션을 켠 경우에만 등록된 약·질병 이름도 "
        "Gemini API로 전송됩니다."
    )


# ==========================================
# 7. 기존 대화 표시
# ==========================================

if st.button(
    "대화 내용 지우기",
    key="gemini_clear"
):

    st.session_state.gemini_history = []
    st.rerun()

st.divider()

if not st.session_state.gemini_history:
    st.info(
        "위의 초록색 질문 보내기 버튼으로 "
        "상담을 시작해 보세요."
    )

for message in st.session_state.gemini_history:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ==========================================
# 8. Gemini 답변 원칙
# ==========================================

SYSTEM_INSTRUCTION = """
당신은 한국어로 답하는 건강정보 안내 도우미입니다.

- 증상과 관련된 일반적인 건강 관리 방법을 설명합니다.
- 관련 의약품 성분군과 일반적인 주의사항을 안내합니다.
- 진단, 처방, 개인별 복용량과 복용 간격을 결정하지 않습니다.
- 약물 병용 및 음식과의 상호작용을 임의로 단정하지 않습니다.
- 호흡곤란, 심한 가슴 통증, 의식 변화 등의 증상에는 응급진료를 안내합니다.
- 어린이와 반려동물에게 성인용 약을 임의로 권하지 않습니다.
- 반려동물의 약물 관련 질문에는 수의사 상담을 안내합니다.
- 필요하면 의료진 또는 약사 상담을 권합니다.
- 답변은 쉽고 간결한 한국어로 작성합니다.
"""


# ==========================================
# 9. 질문 전송
# ==========================================

if send:

    question = question.strip()

    if not question:

        st.warning(
            "질문을 먼저 입력해 주세요."
        )

    else:

        context = f"상담 대상: {target}\n"

        # 선택한 경우에만 기록 참고
        if use_records:

            my_drugs = st.session_state.get(
                "my_drugs", []
            )

            my_conditions = st.session_state.get(
                "my_conditions", []
            )

            context += (
                f"사용자가 등록한 약 이름: "
                f"{my_drugs[:20]}\n"
            )

            context += (
                f"사용자가 등록한 질병·증상: "
                f"{my_conditions[:20]}\n"
            )

        # 이전 대화 연결
        contents = []

        for message in (
            st.session_state.gemini_history[-8:]
        ):

            role = (
                "user"
                if message["role"] == "user"
                else "model"
            )

            contents.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part(
                            text=message["content"]
                        )
                    ],
                )
            )

        # 현재 질문
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=(
                            context
                            + "\n질문: "
                            + question
                        )
                    )
                ],
            )
        )

        # ==================================
        # 10. Gemini API 호출
        # ==================================

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
                        system_instruction=SYSTEM_INSTRUCTION,
                        max_output_tokens=1400,
                    ),
                )

                answer = (
                    response.text
                    or "답변을 만들지 못했습니다. "
                       "다시 질문해 주세요."
                )

        except Exception as exc:

            st.error(
                "Gemini API 연결에 실패했습니다. "
                "API 키·사용 한도·모델 권한을 확인하세요."
            )

            st.caption(
                f"오류 종류: {type(exc).__name__}"
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

            st.rerun()
