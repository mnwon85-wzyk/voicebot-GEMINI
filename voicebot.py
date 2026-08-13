import base64
from datetime import datetime
import os
import streamlit as st
from audio_recorder_streamlit import audio_recorder
import google.generativeai as genai

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="뭐가궁금한데? 나의 개인 음성 비서", page_icon="🎙️", layout="wide"
)


# --- 2. 백그라운드 API 키 자동 로드 ---
def get_gemini_api_key():
    """Secrets 또는 api_key.txt에서 Gemini API 키를 불러옵니다."""
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

if "last_response_text" not in st.session_state:
    st.session_state.last_response_text = ""


# --- 3. 외부 라이브러리 없는 브라우저 TTS(음성 읽기) 재생 함수 ---
def speak_text(text):
    """브라우저 내장 Web Speech API를 활용하여 텍스트를 음성으로 읽어줍니다."""
    # 큰따옴표/줄바꿈 문자 이스케이프 처리
    clean_text = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
        .replace("\r", "")
    )
    js_code = f"""
        <script>
            window.speechSynthesis.cancel(); // 기존 음성 재생 중단
            var msg = new SpeechSynthesisUtterance("{clean_text}");
            msg.lang = 'ko-KR';
            msg.rate = 1.0;
            window.speechSynthesis.speak(msg);
        </script>
    """
    st.components.v1.html(js_code, height=0)


# --- 4. Gemini 답변 생성 함수 ---
def askGeminiWithAudio(audio_bytes, model_name, gemini_api_key):
    """
    1. 오디오 바이트 데이터를 input.mp3 파일로 직접 저장
    2. Gemini 멀티모달 API에 오디오 파일 전송 후 답변 생성
    3. 결과를 st.session_state['messages'] 및 st.session_state['chat']에 저장
    """
    # 1. 오디오 입력 파일 저장
    mp3_filename = "input.mp3"
    with open(mp3_filename, "wb") as f:
        f.write(audio_bytes)

    # 2. Gemini API 호출
    genai.configure(api_key=gemini_api_key)
    audio_file = genai.upload_file(path=mp3_filename)

    model = genai.GenerativeModel(model_name)
    prompt = "사용자가 녹음한 음성을 들려드립니다. 음성 내용을 파악하고 한국어로 친절하고 명확하게 답변해 주세요."

    response = model.generate_content([audio_file, prompt])
    answer_text = response.text

    # 업로드 파일 삭제 (구글 서버 임시 파일 정리)
    try:
        genai.delete_file(audio_file.name)
    except Exception:
        pass

    # 3. session_state 저장
    now_str = datetime.now().strftime("%H:%M")

    st.session_state["messages"].append(
        {"role": "user", "content": "[음성 질문 입력됨]"}
    )
    st.session_state["messages"].append(
        {"role": "assistant", "content": answer_text}
    )

    st.session_state["chat"].append(("user", now_str, "🎙️ [음성 질문]"))
    st.session_state["chat"].append(("assistant", now_str, answer_text))

    # 음성 재생용 최신 답변 저장
    st.session_state.last_response_text = answer_text

    return answer_text


# --- 5. 메인 UI 및 실행 ---
def main():
    gemini_api_key = get_gemini_api_key()

    # 기본 설명 영역
    st.title("🎙️ 뭐가궁금한데? 나의 개인 음성 비서")
    st.markdown(
        "음성 질문을 입력받아 **Gemini**가 분석하여 답변을 생성하고, **브라우저 음성 엔진**을 통해 음성으로 답변을 읽어드립니다."
    )
    st.markdown("---")

    # 옵션 선택 영역 (사이드바)
    with st.sidebar:
        st.header("⚙️ 옵션 선택")

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

        if st.button("🔄 대화 내용 초기화", use_container_width=True):
            st.session_state["messages"] = []
            st.session_state["chat"] = []
            st.session_state.last_audio = None
            st.session_state.last_response_text = ""
            st.rerun()

    # 기능 구현 영역
    st.subheader("1. 음성 녹음 및 질문하기")
    st.write("마이크 버튼을 클릭하여 질문을 녹음하세요.")

    audio_bytes = audio_recorder(
        text="클릭하여 녹음하기",
        recording_color="#e84c3d",
        neutral_color="#6aa84f",
        icon_name="microphone",
        icon_size="2x",
    )

    # 새로운 음성 녹음 수신 시
    if audio_bytes and audio_bytes != st.session_state.last_audio:
        st.session_state.last_audio = audio_bytes

        if not gemini_api_key:
            st.error(
                "⚠️ API Key를 찾을 수 없습니다. `api_key.txt` 파일이나 Secrets를 확인해 주세요."
            )
        else:
            with st.spinner("Gemini가 음성을 분석하고 답변을 생성하는 중입니다..."):
                askGeminiWithAudio(
                    audio_bytes, selected_model, gemini_api_key
                )
            st.rerun()

    # 녹음 질문 듣기 및 답변 음성 읽기
    if st.session_state.last_audio:
        col1, col2 = st.columns(2)

        if os.path.exists("input.mp3"):
            with col1:
                st.write("🔻 **내 질문 다시 듣기**")
                with open("input.mp3", "rb") as f:
                    st.audio(f.read(), format="audio/mp3")

        if st.session_state.last_response_text:
            with col2:
                st.write("🔊 **AI 답변 다시 듣기**")
                if st.button("▶️ 답변 다시 읽어주기"):
                    speak_text(st.session_state.last_response_text)

            # 답변 완료 시 자동으로 음성 재생
            speak_text(st.session_state.last_response_text)

    st.markdown("---")

    # 대화 기록 영역
    st.subheader("2. 대화 기록")

    for sender, time_str, message in st.session_state["chat"]:
        with st.chat_message(sender):
            st.write(f"**[{time_str}]** {message}")


if __name__ == "__main__":
    main()