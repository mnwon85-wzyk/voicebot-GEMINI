import base64
from datetime import datetime
import os
import streamlit as st
from audio_recorder_streamlit import audio_recorder
import google.generativeai as genai
from gtts import gTTS

# --- 페이지 설정 ---
st.set_page_config(
    page_title="뭐가궁금한데? 나의 개인 음성 비서", page_icon="🎙️", layout="wide"
)


# --- 백그라운드 API 키 자동 로드 함수 ---
def get_gemini_api_key():
    """Secrets 또는 api_key.txt에서 Gemini API 키를 자동으로 불러옵니다."""
    try:
        if "GEMINI_API" in st.secrets:
            return st.secrets["GEMINI_API"]
    except Exception:
        pass

    if os.path.exists("api_key.txt"):
        try:
            with open("api_key.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if "GEMINI_API" in line and "=" in line:
                        return line.split("=", 1)[1].strip()
                    elif not line.startswith("#") and line.strip():
                        return line.strip()
        except Exception:
            pass
    return ""


# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "chat" not in st.session_state:
    st.session_state["chat"] = []

if "last_audio" not in st.session_state:
    st.session_state.last_audio = None


# --- gTTS 자동 재생 처리 함수 ---
def play_audio_autoplay(file_path):
    """오디오 파일을 HTML5 autoplay 태그를 통해 자동 재생합니다."""
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.components.v1.html(md, height=0)


# --- Gemini 음성 분석, 답변 및 gTTS 음성 생성 함수 ---
def askGeminiWithAudio(audio_bytes, model_name, gemini_api_key):
    """
    1. 녹음된 음성을 input.mp3로 저장 후 Gemini 분석
    2. Gemini의 답변을 gTTS를 사용해 response.mp3 파일로 변환
    3. 세션 저장 및 자동 재생
    """
    # 1. 사용자 입력 음성 저장
    input_filename = "input.mp3"
    with open(input_filename, "wb") as f:
        f.write(audio_bytes)

    # 2. Gemini API 호출
    genai.configure(api_key=gemini_api_key)
    audio_file = genai.upload_file(path=input_filename)

    model = genai.GenerativeModel(model_name)
    prompt = "사용자가 녹음한 음성을 들려드립니다. 음성 내용을 파악하고 한국어로 친절하고 명확하게 답변해 주세요."

    response = model.generate_content([audio_file, prompt])
    answer_text = response.text

    # 업로드 임시 파일 정리
    try:
        genai.delete_file(audio_file.name)
    except Exception:
        pass

    # 3. gTTS를 활용한 답변 음성 파일 생성 (response.mp3)
    tts = gTTS(text=answer_text, lang="ko")
    response_filename = "response.mp3"
    tts.save(response_filename)

    # 4. session_state 기록 저장
    now_str = datetime.now().strftime("%H:%M")

    st.session_state["messages"].append(
        {"role": "user", "content": "[음성 질문 입력됨]"}
    )
    st.session_state["messages"].append(
        {"role": "assistant", "content": answer_text}
    )

    st.session_state["chat"].append(("user", now_str, "🎙️ [음성 질문]"))
    st.session_state["chat"].append(("assistant", now_str, answer_text))

    return answer_text


# --- 메인 실행 함수 ---
def main():
    # 백그라운드 API 키 불러오기
    gemini_api_key = get_gemini_api_key()

    # ----------------------------------------------------
    # @ 기본 설명 영역
    # ----------------------------------------------------
    st.title("🎙️ Gemini AI 멀티모달 음성 비서")
    st.markdown(
        "음성을 질문하면 **Gemini**가 분석하여 답변을 생성하고, **gTTS**를 통해 음성으로 답변을 자동 재생합니다."
    )
    st.markdown("---")

    # ----------------------------------------------------
    # @ 옵션 선택 영역 (사이드바) - API Key 입력창 완전 제거
    # ----------------------------------------------------
    with st.sidebar:
        st.header("⚙️ 옵션 선택")

        # Gemini 모델 선택 라디오 버튼
        selected_model = st.radio(
            "Gemini 모델 선택",
            options=[
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-2.0-flash",
            ],
            index=0,
            help="• gemini-1.5-flash: 빠른 응답 속도\n• gemini-1.5-pro: 복잡한 추론 능력\n• gemini-2.0-flash: 최신 고성능 모델",
        )

        st.markdown("---")

        # 대화 초기화 버튼
        if st.button("🔄 대화 내용 초기화", use_container_width=True):
            st.session_state["messages"] = []
            st.session_state["chat"] = []
            st.session_state.last_audio = None
            if os.path.exists("response.mp3"):
                os.remove("response.mp3")
            st.rerun()

    # ----------------------------------------------------
    # @ 기능 구현 영역
    # ----------------------------------------------------
    st.subheader("1. 음성 녹음 및 질문하기")
    st.write("마이크 버튼을 클릭하여 질문을 녹음하세요.")

    # 음성 녹음
    audio_bytes = audio_recorder(
        text="클릭하여 녹음하기",
        recording_color="#e84c3d",
        neutral_color="#6aa84f",
        icon_name="microphone",
        icon_size="2x",
    )

    # 새로운 음성 입력 처리
    if audio_bytes and audio_bytes != st.session_state.last_audio:
        st.session_state.last_audio = audio_bytes

        if not gemini_api_key:
            st.error(
                "⚠️ 백그라운드 API Key를 찾을 수 없습니다. `api_key.txt` 파일 또는 Streamlit Secrets를 확인하세요."
            )
        else:
            with st.spinner("Gemini가 음성을 분석하고 답변 음성을 생성하는 중입니다..."):
                askGeminiWithAudio(
                    audio_bytes, selected_model, gemini_api_key
                )
            st.rerun()

    # 녹음된 질문 및 답변 음성 다시 듣기
    if st.session_state.last_audio:
        col1, col2 = st.columns(2)

        # 질문 다시 듣기
        if os.path.exists("input.mp3"):
            with col1:
                st.write("🔻 **내 질문 다시 듣기**")
                with open("input.mp3", "rb") as f:
                    st.audio(f.read(), format="audio/mp3")

        # 답변 음성 플레이어 및 자동 재생
        if os.path.exists("response.mp3"):
            with col2:
                st.write("🔊 **AI 답변 음성**")
                with open("response.mp3", "rb") as f:
                    st.audio(f.read(), format="audio/mp3")

            # HTML5 오디오 태그를 이용한 자동 재생 동작
            play_audio_autoplay("response.mp3")

    st.markdown("---")

    # 2. 대화 기록 영역 (sender, time, message 튜플 출력)
    st.subheader("2. 대화 기록")

    for sender, time_str, message in st.session_state["chat"]:
        with st.chat_message(sender):
            st.write(f"**[{time_str}]** {message}")


if __name__ == "__main__":
    main()