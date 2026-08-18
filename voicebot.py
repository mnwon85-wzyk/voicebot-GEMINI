import streamlit as st
from google import genai
from streamlit_mic_recorder import speech_to_text

# 페이지 기본 설정
st.set_page_config(page_title="수정구슬 Gemini", page_icon="🔮")

# ---------------------------------------------------------
# 사이드바: API 키 및 모델 선택
# ---------------------------------------------------------
st.sidebar.title("⚙️ 설정")

api_key = st.sidebar.text_input(
    "Google Gemini API Key 입력",
    type="password",
    placeholder="AIzaSy...",
    help="개인 API 키를 입력하면 음성 질문을 실행할 수 있습니다."
)

selected_model = st.sidebar.selectbox(
    "Gemini 모델 선택",
    options=[
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash"
    ],
    index=0
)

# ---------------------------------------------------------
# 메인 화면 UI
# ---------------------------------------------------------
st.title("🔮 뭐가 궁금한데?")
st.subheader("수정구슬에게 물어보듯, 목소리로 질문하면 답을 들려드립니다.")

st.markdown("---")

# 마이크 음성 입력 컴포넌트
st.markdown("##### 🎙️ 아래 마이크 버튼을 누르고 질문을 말씀해 주세요.")
text_input_from_speech = speech_to_text(
    language='ko',
    start_prompt="🔴 녹음 시작 (말씀하세요)",
    stop_prompt="⬛ 녹음 중지",
    just_once=True,
    key='STT'
)

# 세션 상태 초기화 (질문/답변 기록 유지)
if "question" not in st.session_state:
    st.session_state.question = ""
if "response" not in st.session_state:
    st.session_state.response = ""

# 음성이 인식되었을 때 처리
if text_input_from_speech:
    st.session_state.question = text_input_from_speech

    if not api_key:
        st.error("👈 왼쪽 사이드바에 Gemini API 키를 먼저 입력해 주세요!")
    else:
        with st.spinner("🔮 수정구슬이 답을 찾고 있습니다..."):
            try:
                # 최신 google-genai SDK 클라이언트 생성
                client = genai.Client(api_key=api_key)
                
                # Gemini 답변 생성
                response = client.models.generate_content(
                    model=selected_model,
                    contents=text_input_from_speech,
                )
                
                st.session_state.response = response.text
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# ---------------------------------------------------------
# 결과 출력 영역
# ---------------------------------------------------------
if st.session_state.question:
    st.markdown("### 🗣️ 인식된 질문")
    st.info(st.session_state.question)

if st.session_state.response:
    st.markdown("### ✨ 수정구슬의 답변")
    st.success(st.session_state.response)
