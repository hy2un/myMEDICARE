import streamlit as st
from google import genai
from google.genai import types


# ============================================================
# 1. 채팅창 디자인
# ============================================================

st.markdown(
    """
    <style>

    /* 상단 안내 영역 */

    .mc-chat-header {
        background: linear-gradient(
            110deg,
            #e6f6ec,
            #f5fbf7
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
        background-color: #ffffff !important;
        border-radius: 14px !important;
        border: 1.5px solid #a4d8b8 !important;
        color: #263e36 !important;
    }


    /* 초록색 전송 버튼 */

    .st-key-gemini_chat_area
    [data-testid="stFormSubmitButton"] button {
        background-color: #147f66 !important;
        border: 1px solid #147f66 !important;
        border-radius: 14px !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        min-height: 48px;
    }

    .st-key-gemini_chat_area
    [data-testid="stFormSubmitButton"] button:hover {
        background-color: #0c6451 !important;
        border-color: #0c6451 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. 상단 제목 및 안내
# ============================================================

st.title("💬 증상 AI 상담")

st.markdown(
    """
    <div class="mc-chat-header">
        <strong>무엇이 궁금하신가요?</strong>
        <p>
            증상 관리, 식단, 약물 성분에 대해
            질문해 보세요.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "질문을 보내면 질문 내용이 Google Gemini API로 전송됩니다. "
    "이름, 전화번호, 주소 등 개인정보는 입력하지 마세요."
)


# ============================================================
# 3. Gemini API 키 확인
# ============================================================

try:
    api_key = st.secrets.get(
        "GEMINI_API_KEY",
        ""
    )

except (FileNotFoundError, KeyError):
    api_key = ""

if not api_key:

    st.error(
        "Streamlit Secrets에 GEMINI_API_KEY를 등록해 주세요."
    )

    st.stop()


# ============================================================
# 4. 대화 기록 초기화
# ============================================================

if "gemini_history" not in st.session_state:
    st.session_state.gemini_history = []

if "gemini_last_unfinished" not in st.session_state:
    st.session_state.gemini_last_unfinished = False


# ============================================================
# 5. 상단 민트색 질문 입력창
# ============================================================

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


# ============================================================
# 6. 상담 설정
# ============================================================

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
        "이 옵션을 켰을 때만 앱에 등록한 약·질병 이름도 "
        "Gemini API로 전송됩니다."
    )


# ============================================================
# 7. Gemini 모델 설정
# ============================================================

MODEL_NAME = "gemini-3.6-flash"

# 기존 1400 -> 8192로 확대
MAX_OUTPUT_TOKENS = 8192


# ============================================================
# 8. Gemini 답변 원칙
# ============================================================

SYSTEM_INSTRUCTION = """
당신은 한국어로 답하는 건강정보 안내 도우미입니다.

[기본 역할]
- 사용자의 증상에 대한 일반적인 건강 관리 방법을 안내합니다.
- 관련 의약품 성분군과 일반적인 주의사항을 설명합니다.
- 질병에 대한 이해를 돕고 필요한 진료 정보를 제공합니다.
- 이해하기 쉽고 정확한 한국어로 답변합니다.

[의약품 안내]
- 특정 의약품을 임의로 처방하지 않습니다.
- 개인별 복용량과 복용 간격을 결정하지 않습니다.
- 약물 병용 가능성을 확인 없이 단정하지 않습니다.
- 약과 음식의 상호작용을 불확실한 상태에서 단정하지 않습니다.
- 의약품의 성분, 용도, 주의사항을 구분하여 설명합니다.
- 필요한 경우 의사나 약사 상담을 안내합니다.

[응급 증상]
- 호흡곤란, 심한 가슴 통증, 의식 변화 등은
  즉시 응급진료를 안내합니다.
- 위험 신호가 있으면 답변의 앞부분에 먼저 설명합니다.

[어린이 및 반려동물]
- 어린이에게 성인용 약을 임의로 권하지 않습니다.
- 반려동물에게 사람용 약을 임의로 권하지 않습니다.
- 동물의 약물 관련 질문에는 수의사 상담을 안내합니다.

[답변 작성 규칙]
- 불필요하게 긴 설명은 피합니다.
- 중요한 정보를 우선적으로 설명합니다.
- 항목을 나누어 이해하기 쉽게 작성합니다.
- 답변은 중간에 끊지 않고 마지막 문장까지 완결합니다.
- 필요한 경우 마지막에 핵심 내용을 간단히 정리합니다.
"""


# ============================================================
# 9. Gemini 생성 설정
# ============================================================

def make_config():

    return types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,

        max_output_tokens=MAX_OUTPUT_TOKENS,

        thinking_config=types.ThinkingConfig(
            thinking_level="low"
        ),
    )


# ============================================================
# 10. 답변 종료 원인 확인
# ============================================================

def finish_reason_of(response):

    candidates = getattr(
        response,
        "candidates",
        None
    ) or []

    if not candidates:
        return "UNKNOWN"

    reason = getattr(
        candidates[0],
        "finish_reason",
        None
    )

    if reason is None:
        return "UNKNOWN"

    return getattr(
        reason,
        "name",
        str(reason)
    ).split(".")[-1]


# ============================================================
# 11. 대화 기록을 Gemini 형식으로 변환
# ============================================================

def as_contents(messages):

    contents = []

    for message in messages:

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

    return contents


# ============================================================
# 12. Gemini API 호출 함수
# ============================================================

def generate(client, contents):

    response = client.models.generate_content(
        model=MODEL_NAME,

        contents=contents,

        config=make_config(),
    )

    answer = response.text or ""

    reason = finish_reason_of(response)

    return answer, reason


# ============================================================
# 13. 잘린 답변 이어쓰기 함수
# ============================================================

def continue_answer(
    client,
    original_question,
    partial_answer,
    earlier_messages,
):

    continuation_prompt = (
        "원래 질문:\n"
        + original_question
        + "\n\n"

        + "지금까지 작성된 답변:\n"
        + partial_answer
        + "\n\n"

        + "위 답변이 출력 한도 때문에 중간에서 끊겼습니다. "
        + "이미 작성된 내용은 반복하지 마세요. "
        + "끊긴 부분부터 자연스럽게 이어서 설명하고, "
        + "남은 중요한 내용과 마지막 문장까지 마무리하세요."
    )

    contents = as_contents(
        earlier_messages
    )

    contents.append(
        types.Content(
            role="user",

            parts=[
                types.Part(
                    text=continuation_prompt
                )
            ],
        )
    )

    return generate(
        client,
        contents
    )


# ============================================================
# 14. 대화 내용 삭제
# ============================================================

if st.button(
    "대화 내용 지우기",
    key="gemini_clear"
):

    st.session_state.gemini_history = []

    st.session_state.gemini_last_unfinished = False

    st.rerun()


# ============================================================
# 15. 기존 대화 표시
# ============================================================

st.divider()

if not st.session_state.gemini_history:

    st.info(
        "위의 초록색 '질문 보내기' 버튼으로 "
        "상담을 시작해 보세요."
    )


for message in st.session_state.gemini_history:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# ============================================================
# 16. 출력 한도에 걸린 답변 수동 이어쓰기
# ============================================================

if (
    st.session_state.gemini_last_unfinished
    and len(st.session_state.gemini_history) >= 2
):

    st.warning(
        "답변이 출력 한도에 도달했습니다. "
        "아래 버튼을 누르면 이어서 볼 수 있습니다."
    )

    if st.button(
        "↪️ 잘린 답변 이어서 보기",
        type="primary",
    ):

        history = st.session_state.gemini_history

        try:

            with st.spinner(
                "남은 답변을 생성하고 있습니다..."
            ):

                client = genai.Client(
                    api_key=api_key
                )

                extra, reason = continue_answer(
                    client,

                    original_question=(
                        history[-2]["content"]
                    ),

                    partial_answer=(
                        history[-1]["content"]
                    ),

                    earlier_messages=(
                        history[:-2][-8:]
                    ),
                )

            if extra.strip():

                history[-1]["content"] += (
                    "\n\n" + extra.strip()
                )

                st.session_state.gemini_last_unfinished = (
                    reason == "MAX_TOKENS"
                )

                st.rerun()

            else:

                st.warning(
                    "이어지는 답변을 받지 못했습니다. "
                    "다시 시도해 주세요."
                )

        except Exception as exc:

            st.error(
                "답변 이어받기에 실패했습니다."
            )

            st.caption(
                f"오류 종류: {type(exc).__name__}"
            )


# ============================================================
# 17. 질문 전송 처리
# ============================================================

if send:

    question = question.strip()

    if not question:

        st.warning(
            "질문을 먼저 입력해 주세요."
        )

    else:

        # ==================================
        # 17-1. 상담 대상 설정
        # ==================================

        context = (
            f"상담 대상: {target}\n"
        )

        # ==================================
        # 17-2. 약·질병 기록 선택적 참조
        # ==================================

        if use_records:

            my_drugs = st.session_state.get(
                "my_drugs",
                []
            )

            my_conditions = st.session_state.get(
                "my_conditions",
                []
            )

            context += (
                "사용자가 등록한 약 이름: "
                + str(my_drugs[:20])
                + "\n"
            )

            context += (
                "사용자가 등록한 질병·증상: "
                + str(my_conditions[:20])
                + "\n"
            )

        # ==================================
        # 17-3. 이전 대화 가져오기
        # ==================================

        past_messages = (
            st.session_state.gemini_history[-8:]
        )

        original_question = (
            context
            + "\n질문: "
            + question
        )

        contents = as_contents(
            past_messages
        )

        contents.append(
            types.Content(
                role="user",

                parts=[
                    types.Part(
                        text=original_question
                    )
                ],
            )
        )

        # ==================================
        # 17-4. Gemini API 호출
        # ==================================

        try:

            with st.spinner(
                "Gemini가 답변을 작성하고 있습니다..."
            ):

                client = genai.Client(
                    api_key=api_key
                )

                answer, reason = generate(
                    client,
                    contents
                )

                # ==========================
                # 17-5. 중간 끊김 자동 복구
                # ==========================

                if (
                    reason == "MAX_TOKENS"
                    and answer.strip()
                ):

                    extra, reason = continue_answer(
                        client,

                        original_question=(
                            original_question
                        ),

                        partial_answer=answer,

                        earlier_messages=past_messages,
                    )

                    if extra.strip():

                        answer = (
                            answer.rstrip()
                            + "\n\n"
                            + extra.strip()
                        )

            # ==================================
            # 17-6. 빈 답변 처리
            # ==================================

            if not answer.strip():

                st.warning(
                    "답변이 생성되지 않았습니다. "
                    "질문을 조금 짧게 입력하여 "
                    "다시 시도해 주세요."
                )

            # ==================================
            # 17-7. 대화 기록 저장
            # ==================================

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

                st.session_state.gemini_last_unfinished = (
                    reason == "MAX_TOKENS"
                )

                st.rerun()

        # ==================================
        # 17-8. API 오류 처리
        # ==================================

        except Exception as exc:

            st.error(
                "Gemini API 연결에 실패했습니다. "
                "API 키, 사용 한도, 모델 접근 권한을 "
                "확인해 주세요."
            )

            st.caption(
                f"오류 종류: {type(exc).__name__}"
            )
