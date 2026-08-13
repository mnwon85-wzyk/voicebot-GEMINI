import os
import streamlit as st
from audio_recorder_streamlit import audio_recorder

# --- 1. 페이지 및 세션 상태 설정 ---
st.set_page_config(page_title="음성 비서 프로그램", page_icon="🎙️", layout="wide")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_audio" not in st.session_state:
    st.session_state.last_audio = None


# --- 2. 백그라운드 API 키 자동 로드 함수 ---
def get_gemini_api_key():
    """
    화면에 표시하지 않고 내부에서 API 키를 로드합니다.
    1순위: Streamlit Cloud Secrets (st.secrets["GEMINI_API"])
    2순위: 로컬 api_key.txt 파일
    """
    # 1) Streamlit Cloud Secrets 확인
    try:
        if "GEMINI_API" in st.secrets:
            return st.secrets["GEMINI_API"]
    except Exception:
        pass

    # 2) 로컬 api_key.txt 파일 확인
    if os.path.exists("api_key.txt"):
        try:
            with open("api_key.txt", "r", encoding="utf-8") as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass

    return None


# API 키를 백그라운드 세션에 저장
GEMINI_API_KEY = get_gemini_api_key()
if GEMINI_API_KEY:
    st.session_state["GEMINI_API"] = GEMINI_API_KEY


# --- 3. 사이드바 영역 (초기화 버튼만 남김) ---
with st.sidebar:
    # 대화 초기화 버튼
    if st.button("🔄 대화 내용 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_audio = None
        st.rerun()


# --- 4. 메인 화면 ---
st.title("🎙️ AI 음성 비서")
st.write("음성으로 질문을 녹음하고 채팅으로 대화를 확인하세요.")

# 1) 음성 입력 영역
st.subheader("1. 음성 입력")
st.write("마이크 아이콘을 눌러 녹음을 시작/중지하세요.")

audio_bytes = audio_recorder(
    text="녹음 시작/중지",
    recording_color="#e84c3d",
    neutral_color="#6aa84f",
    icon_name="microphone",
    icon_size="2x",
)

# 새로운 음성이 녹음된 경우 처리
if audio_bytes and audio_bytes != st.session_state.last_audio:
    st.session_state.last_audio = audio_bytes

    # 사용자 음성 메시지 추가
    st.session_state.messages.append(
        {
            "role": "user",
            "type": "audio",
            "content": audio_bytes,
            "text": "[녹음된 음성 메시지]",
        }
    )

    # -----------------------------------------------------------------
    # Gemini API 연동 시 st.session_state.get("GEMINI_API")를 사용하시면 됩니다.
    # -----------------------------------------------------------------
    ai_dummy_response = "음성을 수신했습니다! (Gemini API 연결 시 답변이 생성됩니다.)"
    st.session_state.messages.append(
        {"role": "assistant", "type": "text", "content": ai_dummy_response}
    )

    st.rerun()

st.markdown("---")

# 2) 대화 기록 채팅 영역
st.subheader("2. 대화 기록")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["type"] == "audio":
            st.write(msg.get("text", "음성 메시지"))
            st.audio(msg["content"], format="audio/wav")
        else:
            st.write(msg["content"])