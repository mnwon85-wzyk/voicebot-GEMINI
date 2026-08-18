import base64  # 바이너리 데이터(음원 파일)를 텍스트 데이터 형태(Base64)로 변환하는 모듈을 불러옵니다.
import os  # 파일 존재 여부 확인, 파일 삭제 등 운영체제 기능 이용을 위한 os 모듈을 불러옵니다.
import streamlit as st  # 웹 애플리케이션 UI를 제작하기 위한 Streamlit 라이브러리를 st라는 이름으로 불러옵니다.
from audio_recorder_streamlit import (
    audio_recorder,
)  # Streamlit에서 마이크 녹음 기능을 제공하는 라이브러리를 불러옵니다.
import google.generativeai as genai  # Google의 Gemini AI API를 다루기 위한 공식 라이브러리를 불러옵니다.

# --- 1. 페이지 설정 ---
st.set_page_config(  # Streamlit 웹 페이지의 기본 환경을 설정하는 함수입니다.
    page_title="오늘은 뭐가 궁금해?",  # 브라우저 탭에 표시될 웹 페이지의 제목을 설정합니다.
    page_icon="🎙️",  # 브라우저 탭에 표시될 아이콘을 설정합니다.
    layout="wide",  # 웹 페이지 화면 레이아웃을 넓은 화면(wide) 모드로 설정합니다.
)


# --- 2. 백그라운드 API 키 자동 로드 함수 ---
def get_gemini_api_key():  # API 키를 백그라운드에서 안전하게 찾아오는 함수를 정의합니다.
    """Secrets 또는 api_key.txt에서 Gemini API 키를 불러옵니다."""
    try:  # 에러가 발생할 가능성이 있는 코드를 시작합니다.
        if (
            "GEMINI_API" in st.secrets
        ):  # Streamlit Cloud의 Secrets에 GEMINI_API 키가 등록되어 있는지 확인합니다.
            return st.secrets[
                "GEMINI_API"
            ]  # Secrets에 저장된 API 키를 반환합니다.
    except Exception:  # Secrets 접근 중 에러가 발생하면 무시하고 진행합니다.
        pass  # 아무 작업도 하지 않고 넘어갑니다.

    if os.path.exists(
        "api_key.txt"
    ):  # 로컬 컴퓨터 폴더에 'api_key.txt' 파일이 존재하는지 확인합니다.
        try:  # 파일 읽기 작업을 시작합니다.
            with open(
                "api_key.txt", "r", encoding="utf-8"
            ) as f:  # api_key.txt 파일을 읽기 모드(r)로 열어옵니다.
                for line in f:  # 파일의 각 줄을 하나씩 읽어옵니다.
                    if (
                        "GEMINI_API" in line and "=" in line
                    ):  # 줄에 'GEMINI_API'와 '=' 문자가 들어있는지 확인합니다.
                        return line.split("=", 1)[1].strip()  # '=' 뒤의 API 키 값만 추출하여 공백을 제거하고 반환합니다.
                    elif (
                        not line.startswith("#") and line.strip()
                    ):  # 주석(#)이 아니고 빈 줄이 아니라면
                        return line.strip()  # 해당 줄 전체를 API 키로 보고 반환합니다.
        except Exception:  # 파일 읽기 도중 에러가 발생하면 무시합니다.
            pass  # 아무 작업도 하지 않고 넘어갑니다.
    return ""  # API 키를 찾지 못한 경우 빈 문자열을 반환합니다.


# 세션 상태(Session State) 초기화
if (
    "last_audio" not in st.session_state
):  # 세션에 'last_audio'(마지막 녹음 데이터)가 없으면 초기화합니다.
    st.session_state.last_audio = (
        None  # 마지막 녹음 오디오 바이트 값을 None으로 초기화합니다.
    )

if (
    "last_response_text" not in st.session_state
):  # 세션에 'last_response_text'(마지막 AI 답변)가 없으면 초기화합니다.
    st.session_state.last_response_text = (
        ""  # 마지막 AI 답변 텍스트를 빈 문자열로 초기화합니다.
    )

if (
    "last_response_model" not in st.session_state
):  # 세션에 'last_response_model'(마지막 답변에 쓰인 모델명)이 없으면 초기화합니다.
    st.session_state.last_response_model = (
        ""  # 마지막 답변에 사용된 모델명을 빈 문자열로 초기화합니다.
    )

if (
    "last_error" not in st.session_state
):  # 세션에 'last_error'(마지막 오류 메시지)가 없으면 초기화합니다.
    st.session_state.last_error = (
        ""  # rerun 이후에도 사라지지 않고 화면에 남아있을 오류 메시지를 빈 문자열로 초기화합니다.
    )

if (
    "user_api_key" not in st.session_state
):  # 세션에 'user_api_key'(화면에서 직접 입력한 키)가 없으면 초기화합니다.
    st.session_state.user_api_key = (
        ""  # 사용자가 화면에서 직접 입력한 API 키를 빈 문자열로 초기화합니다.
    )


# --- 3. 외부 라이브러리 없는 브라우저 TTS(음성 읽기) 재생 함수 ---
def speak_text(
    text,
):  # 웹 브라우저 내장 음성 엔진을 통해 텍스트를 읽어주는 함수를 정의합니다.
    """브라우저 내장 Web Speech API를 활용하여 텍스트를 음성으로 읽어줍니다."""
    clean_text = (  # 자바스크립트 코드 에러를 방지하기 위해 텍스트 내부 문자를 정돈합니다.
        text.replace("\\", "\\\\")  # 백슬래시 문자를 이스케이프 처리합니다.
        .replace('"', '\\"')  # 큰따옴표 앞에 백슬래시를 붙여 이스케이프 처리합니다.
        .replace("\n", " ")  # 줄바꿈 문자를 공백 한 칸으로 바꿉니다.
        .replace("\r", "")  # 복귀 문자를 제거합니다.
    )
    js_code = f""" 
        <script>
            window.speechSynthesis.cancel(); // 현재 재생 중인 기존 음성을 중단합니다.
            var msg = new SpeechSynthesisUtterance("{clean_text}"); // 읽을 텍스트 객체를 생성합니다.
            msg.lang = 'ko-KR'; // 음성 언어를 한국어로 설정합니다.
            msg.rate = 1.0; // 읽기 속도를 기본 속도(1.0)로 설정합니다.
            window.speechSynthesis.speak(msg); // 브라우저 음성 엔진에 실행을 명령합니다.
        </script>
    """  # 웹 브라우저에서 실행될 자바스크립트 코드 문자열을 작성합니다.
    st.components.v1.html(
        js_code, height=0
    )  # 자바스크립트 코드를 Streamlit 화면 백그라운드에서 실행시킵니다.


# --- 4. Gemini 답변 생성 함수 ---
def askGeminiWithAudio(
    audio_bytes, model_name, gemini_api_key
):  # 녹음된 음성을 Gemini에 전달해 답변을 받는 함수를 정의합니다.
    # 1. 오디오 입력 파일 저장
    mp3_filename = "input.mp3"  # 저장할 오디오 파일의 이름을 지정합니다.
    with open(
        mp3_filename, "wb"
    ) as f:  # input.mp3 파일을 바이너리 쓰기 모드(wb)로 열어옵니다.
        f.write(
            audio_bytes
        )  # 마이크로 녹음된 오디오 바이트 데이터를 파일에 직접 기록합니다.

    # 2. Gemini API 호출
    genai.configure(
        api_key=gemini_api_key
    )  # 가져온 API 키로 Gemini 라이브러리 환경을 설정합니다.
    audio_file = genai.upload_file(
        path=mp3_filename
    )  # 저장된 input.mp3 파일은 Google Gemini 서버로 업로드합니다.

    model = genai.GenerativeModel(
        model_name
    )  # 화면에서 선택된 모델(예: gemini-1.5-flash) 객체를 생성합니다.
    prompt = "사용자가 녹음한 음성을 들려드립니다. 음성 내용을 파악하고 한국어로 친절하고 명확하게 답변해 주세요."  # AI에게 줄 안내 지침(프롬프트)입니다.

    response = model.generate_content(
        [audio_file, prompt]
    )  # 업로드한 음성 파일과 프롬프트를 함께 Gemini 모델에 전달하여 답변을 생성합니다.
    answer_text = response.text  # 생성된 답변 텍스트만 추출합니다.

    # 업로드 파일 삭제 (구글 서버 임시 파일 정리)
    try:  # 정리 작업을 진행합니다.
        genai.delete_file(
            audio_file.name
        )  # Gemini 서버에 임시 업로드했던 오디오 파일을 삭제합니다.
    except Exception:  # 삭제 실패 시 에러가 나도 무시합니다.
        pass  # 넘어가기

    # 3. session_state 기록 저장 (2번 답변 영역에서 바로 보여줄 최신 답변만 저장)
    st.session_state.last_response_text = (
        answer_text  # 최신 답변 텍스트를 자동 음성 재생용 변수에 등록합니다.
    )
    st.session_state.last_response_model = (
        model_name  # 방금 답변에 사용된 모델명을 기록해 화면에 표시할 수 있게 합니다.
    )
    st.session_state.last_error = (
        ""  # 정상적으로 답변을 받았으므로 이전 오류 기록을 지웁니다.
    )

    return answer_text  # 생성된 답변 텍스트를 반환합니다.


# --- 5. 히어로 섹션 렌더링 함수 (수정구슬 컨셉) ---
def render_hero():  # 점성술사의 수정구슬 컨셉으로 화면 중앙에 표시되는 히어로 영역을 그리는 함수를 정의합니다.
    """수정구슬 이미지를 중심으로 한 점성술 테마의 센터 정렬 히어로 섹션을 출력합니다."""
    st.markdown(  # 히어로 영역에 필요한 CSS와 HTML을 하나의 마크다운 블록으로 작성합니다.
        """
        <style>
        .hero-wrap {  /* 히어로 전체를 감싸는 컨테이너 스타일입니다. */
            text-align: center;  /* 내부 요소를 가로 중앙 정렬합니다. */
            padding: 48px 20px 36px 20px;  /* 위/좌우/아래 여백을 지정합니다. */
        }
        .hero-orb {  /* 수정구슬 이모지를 감싸는 원형 배경 스타일입니다. */
            width: 140px;  /* 구슬 배경의 가로 크기입니다. */
            height: 140px;  /* 구슬 배경의 세로 크기입니다. */
            margin: 0 auto 18px auto;  /* 가로 중앙 정렬 및 아래쪽 간격입니다. */
            border-radius: 50%;  /* 완전한 원 형태로 만듭니다. */
            display: flex;  /* 내부 이모지를 정중앙에 배치하기 위해 flex를 사용합니다. */
            align-items: center;  /* 세로 중앙 정렬입니다. */
            justify-content: center;  /* 가로 중앙 정렬입니다. */
            background: radial-gradient(circle at 35% 30%, rgba(210,190,255,0.55), rgba(88,52,148,0.35) 55%, rgba(30,10,60,0.25) 100%);  /* 신비로운 보라빛 광채를 표현하는 방사형 그라데이션입니다. */
            box-shadow: 0 0 45px rgba(147,112,219,0.55), inset 0 0 25px rgba(255,255,255,0.25);  /* 은은한 발광 효과입니다. */
            animation: hero-float 3.2s ease-in-out infinite;  /* 구슬이 위아래로 부드럽게 떠다니는 애니메이션입니다. */
        }
        .hero-orb span {  /* 구슬 안의 이모지 크기를 지정합니다. */
            font-size: 64px;  /* 수정구슬 이모지 크기입니다. */
            filter: drop-shadow(0 0 18px rgba(216,196,255,0.8));  /* 이모지 주변에도 은은한 광채를 줍니다. */
        }
        @keyframes hero-float {  /* 구슬 떠오름 애니메이션 키프레임을 정의합니다. */
            0%, 100% { transform: translateY(0px); }  /* 시작과 끝 위치입니다. */
            50% { transform: translateY(-12px); }  /* 중간 지점에서 위로 떠오릅니다. */
        }
        .hero-title {  /* 메인 타이틀 텍스트 스타일입니다. */
            font-size: 34px;  /* 큰 글씨 크기로 시선을 끕니다. */
            font-weight: 800;  /* 굵은 글씨체입니다. */
            margin: 0;  /* 기본 여백을 제거합니다. */
            background: linear-gradient(135deg, #d8c4ff 0%, #9b6ddb 45%, #4b2e83 100%);  /* 신비로운 보라 계열 그라데이션 텍스트입니다. */
            -webkit-background-clip: text;  /* 텍스트에만 그라데이션을 적용합니다(웹킷 계열). */
            background-clip: text;  /* 텍스트에만 그라데이션을 적용합니다. */
            -webkit-text-fill-color: transparent;  /* 원래 글자색을 투명하게 만들어 그라데이션이 보이게 합니다. */
            color: #b28ce0;  /* 그라데이션 미지원 브라우저를 위한 대체 색상입니다. */
        }
        .hero-subtitle {  /* 부제목 텍스트 스타일입니다. */
            margin-top: 10px;  /* 타이틀과의 간격입니다. */
            font-size: 16px;  /* 부제목 글씨 크기입니다. */
            color: rgba(200,180,230,0.85);  /* 은은한 보라빛 회색조 텍스트 색상입니다. */
            letter-spacing: 0.3px;  /* 살짝 넓은 자간으로 신비로운 느낌을 더합니다. */
        }
        .hero-stars {  /* 별 장식 텍스트 스타일입니다. */
            margin-top: 6px;  /* 부제목과의 간격입니다. */
            font-size: 13px;  /* 작은 별 장식 크기입니다. */
            letter-spacing: 6px;  /* 별들 사이 간격을 넓게 줍니다. */
            color: rgba(216,196,255,0.6);  /* 옅은 보랏빛 색상입니다. */
        }
        </style>
        <div class="hero-wrap">
            <div class="hero-orb"><span>🔮</span></div>
            <p class="hero-title">뭐가 궁금한데?</p>
            <p class="hero-subtitle">수정구슬에게 물어보듯, 목소리로 질문하면 답을 들려드립니다</p>
            <p class="hero-stars">✦ ✧ ✦</p>
        </div>
        """,
        unsafe_allow_html=True,  # HTML/CSS를 그대로 렌더링하도록 허용합니다.
    )


# --- 6. 사이드바 API 키 입력 위젯 ---
def render_api_key_input(env_api_key):  # 화면에서 직접 API 키를 입력받는 위젯을 정의합니다.
    """Secrets/파일에 키가 없을 때 사용자가 직접 API 키를 입력할 수 있는 입력창을 사이드바에 표시합니다."""
    st.subheader("🔑 API 키 설정")  # 사이드바 내 API 키 섹션 제목입니다.

    if env_api_key:  # Secrets나 api_key.txt에서 이미 키를 찾은 경우
        st.success("서버에 저장된 API 키를 사용 중입니다.")  # 별도 입력 없이 바로 서비스 가능함을 안내합니다.
        with st.expander("다른 키로 바꿔서 쓰기"):  # 원하면 다른 키로 덮어쓸 수 있는 접이식 영역입니다.
            typed_key = st.text_input(  # 사용자가 직접 입력할 수 있는 텍스트 입력창입니다.
                "Gemini API 키",  # 입력창 라벨입니다.
                value=st.session_state.user_api_key,  # 기존에 입력해둔 값을 유지합니다.
                type="password",  # 화면에 키 값이 그대로 노출되지 않도록 마스킹합니다.
                placeholder="AIza로 시작하는 키를 붙여넣으세요",  # 입력 힌트입니다.
                key="api_key_input_box_1",  # 위젯 고유 키입니다.
            )
            st.session_state.user_api_key = typed_key  # 입력값을 세션에 저장합니다.
    else:  # Secrets/파일 어디에도 키가 없는 경우
        st.warning("등록된 API 키가 없습니다. 아래에 직접 입력하면 바로 음성 서비스를 이용할 수 있어요.")  # 안내 메시지입니다.
        typed_key = st.text_input(  # 사용자가 직접 입력할 수 있는 텍스트 입력창입니다.
            "Gemini API 키",  # 입력창 라벨입니다.
            value=st.session_state.user_api_key,  # 기존에 입력해둔 값을 유지합니다.
            type="password",  # 화면에 키 값이 그대로 노출되지 않도록 마스킹합니다.
            placeholder="AIza로 시작하는 키를 붙여넣으세요",  # 입력 힌트입니다.
            key="api_key_input_box_2",  # 위젯 고유 키입니다.
        )
        st.session_state.user_api_key = typed_key  # 입력값을 세션에 저장합니다.
        st.caption(  # 키 발급 방법과 저장 여부를 안내하는 작은 설명 문구입니다.
            "키는 이 브라우저 세션에서만 임시로 사용되며 서버 파일에 저장되지 않습니다. "
            "키가 없다면 [Google AI Studio](https://aistudio.google.com/apikey)에서 무료로 발급받을 수 있어요."
        )

    if st.session_state.user_api_key:  # 사용자가 직접 입력한 키가 있는 경우
        st.info("직접 입력한 키가 우선 적용됩니다.")  # 우선순위 안내 문구입니다.


# --- 7. 메인 UI 및 실행 ---
def main():  # 웹 앱의 화면 및 로직을 구성하는 메인 함수를 정의합니다.
    env_api_key = (
        get_gemini_api_key()
    )  # 백그라운드 함수를 호출해 Secrets/파일에 등록된 API 키를 받아옵니다.

    # 중앙 정렬된 수정구슬 컨셉 히어로 섹션 출력
    render_hero()  # 점성술 테마의 센터 정렬 히어로 섹션을 화면 상단에 그립니다.
    st.markdown("---")  # 구분선을 그립니다.

    # 사이드바 설정 영역
    with st.sidebar:  # 웹 앱의 왼쪽 사이드바 영역을 만듭니다.
        render_api_key_input(env_api_key)  # 화면에서 API 키를 입력/확인할 수 있는 위젯을 그립니다.

        st.markdown("---")  # 사이드바 내 구분선을 그립니다.
        st.header("⚙️ 옵션 선택")  # 사이드바의 헤더 제목을 설정합니다.

        selected_model = st.radio(  # 사용할 Gemini AI 모델을 선택하는 라디오 버튼을 출력합니다.
            "Gemini 모델 선택",  # 라디오 버튼의 라벨 제목입니다.
            options=[  # 선택할 수 있는 모델 항목 리스트입니다.
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-2.0-flash",
            ],
            index=0,  # 기본 선택 항목을 첫 번째(gemini-1.5-flash)로 지정합니다.
            help="• gemini-1.5-flash: 빠른 응답 속도\n• gemini-1.5-pro: 복잡한 추론 능력\n• gemini-2.0-flash: 최신 고성능 모델",  # 마우스를 올려두면 나오는 도움말 텍스트입니다.
        )

        st.markdown("---")  # 사이드바 내 구분선을 그립니다.

        if st.button(
            "🔄 답변 초기화", use_container_width=True
        ):  # 답변 초기화 버튼을 가로 전체 너비로 만듭니다.
            st.session_state.last_audio = (
                None  # 녹음 오디오 기록을 초기화합니다.
            )
            st.session_state.last_response_text = (
                ""  # 답변 텍스트 기록을 초기화합니다.
            )
            st.session_state.last_response_model = (
                ""  # 마지막 답변 모델 기록도 함께 초기화합니다.
            )
            st.session_state.last_error = (
                ""  # 오류 기록도 함께 초기화합니다.
            )
            st.rerun()  # Streamlit 앱을 새로고침하여 초기화된 상태를 적용합니다.

    # 화면에서 입력한 키가 있으면 그 값을 우선 사용하고, 없으면 Secrets/파일 값을 사용합니다.
    gemini_api_key = (
        st.session_state.user_api_key or env_api_key
    )  # 최종적으로 사용할 API 키를 결정합니다.

    # 화면 메인 기능 구역
    st.subheader("1. 음성 녹음 및 질문하기")  # 소제목 1을 출력합니다.
    st.write(
        "마이크 버튼을 클릭하여 질문을 녹음하세요."
    )  # 사용법 안내 문구를 출력합니다.
    st.caption(
        f"🔮 답변에 사용될 모델: `{selected_model}` (왼쪽 사이드바에서 변경 가능)"
    )  # 사이드바에서 고른 모델이 실제로 답변에 쓰인다는 것을 미리 알려줍니다.

    audio_bytes = audio_recorder(  # 화면에 음성 녹음 마이크 버튼 컴포넌트를 생성하고 녹음 결과를 받습니다.
        text="클릭하여 녹음하기",  # 버튼 옆에 표시될 문구입니다.
        recording_color="#e84c3d",  # 녹음 중일 때 빨간색으로 변경할 색상 코드입니다.
        neutral_color="#6aa84f",  # 대기 상태일 때 녹색 색상 코드입니다.
        icon_name="microphone",  # 아이콘 모양을 마이크로 설정합니다.
        icon_size="2x",  # 아이콘 크기를 2배 크게 설정합니다.
    )

    # 마이크로 새로운 음성이 녹음되었을 때 처리
    if (
        audio_bytes and audio_bytes != st.session_state.last_audio
    ):  # 새로운 녹음 음성 데이터가 들어왔는지 확인합니다.
        st.session_state.last_audio = (
            audio_bytes  # 현재 입력받은 오디오 데이터를 세션에 저장합니다.
        )
        st.session_state.last_error = (
            ""  # 새 녹음을 시작하므로 이전 오류 기록을 지웁니다.
        )

        if not gemini_api_key:  # 화면 입력/Secrets/파일 어디에도 키가 없는 경우 에러를 표시합니다.
            st.session_state.last_error = (
                "⚠️ API 키가 없습니다. 왼쪽 사이드바의 'API 키 설정'에 Gemini API 키를 입력해 주세요."
            )  # 오류를 세션에 저장해 rerun 이후에도 사라지지 않게 합니다.
        else:  # API 키가 정상적으로 존재하는 경우
            with st.spinner(
                "Gemini가 음성을 분석하고 답변을 생성하는 중입니다..."
            ):  # 로딩 애니메이션을 띄웁니다.
                try:  # Gemini 호출 중 발생할 수 있는 오류(예: 잘못된 키, 모델명, 네트워크)를 대비합니다.
                    askGeminiWithAudio(  # 음성 분석 및 답변 생성 함수를 실행합니다.
                        audio_bytes, selected_model, gemini_api_key
                    )
                except Exception as e:  # 키가 유효하지 않거나 호출이 실패한 경우
                    st.session_state.last_error = (  # 이전에는 st.error로만 띄우고 바로 st.rerun()이 지워버려 화면에 아무것도 안 보였던 부분입니다.
                        f"⚠️ 요청 처리 중 오류가 발생했습니다. API 키/모델명을 확인해 주세요. (원인: {e})"
                    )
            st.rerun()  # 화면을 새로고침하여 결과를 즉시 업데이트합니다(오류는 last_error에 저장되어 사라지지 않습니다).

    # 내 질문 다시 듣기 (보조 요소 - 접이식으로 축소)
    if st.session_state.last_audio and os.path.exists(
        "input.mp3"
    ):  # 녹음된 오디오와 파일이 모두 존재하는 경우
        with st.expander("🔻 내 질문 다시 듣기"):  # 클릭해야 펼쳐지는 보조 영역으로 뺍니다.
            with open("input.mp3", "rb") as f:  # 질문 파일을 읽어옵니다.
                st.audio(
                    f.read(), format="audio/mp3"
                )  # 화면에 질문 음성 오디오 플레이어를 생성합니다.

    # --- 2. Gemini 답변 영역 (사용자 음성 질문에 대한 실제 답변을 보여주는 핵심 섹션) ---
    st.markdown("---")  # 구분선을 그립니다.
    st.subheader("2. Gemini 답변")  # 정식으로 번호가 매겨진 답변 섹션 제목입니다.

    if st.session_state.get("last_error"):  # 직전 처리에서 오류가 발생한 경우 (이전에는 rerun이 이 메시지를 바로 지워버렸습니다)
        st.error(st.session_state.last_error)  # 오류 내용을 화면에 계속 표시합니다.
    elif st.session_state.last_response_text:  # 오류 없이 생성된 답변 텍스트가 있는 경우
        if st.session_state.get("last_response_model"):  # 답변에 쓰인 모델 정보가 있는 경우
            st.caption(
                f"🔮 사용 모델: `{st.session_state.last_response_model}`"
            )  # 어떤 모델이 답했는지 작은 글씨로 표시합니다.
        st.markdown(
            f"### 🔊 {st.session_state.last_response_text}"
        )  # 사용자 음성 질문에 대한 Gemini의 실제 답변 텍스트를 화면 중앙 흐름에 크게 표시합니다.
        if st.button("▶️ 답변 다시 읽어주기"):  # 수동 수신용 다시 읽기 버튼을 생성합니다.
            speak_text(
                st.session_state.last_response_text
            )  # 버튼 클릭 시 브라우저가 답변을 다시 읽어줍니다.
        speak_text(
            st.session_state.last_response_text
        )  # 답변 생성 완료 직후 자동으로 브라우저가 음성을 읽어주도록 실행합니다.
    else:  # 아직 질문을 녹음하지 않아 답변이 없는 경우
        st.info(
            "아직 답변이 없습니다. 위에서 마이크 버튼을 눌러 질문을 녹음하면 여기에 Gemini의 답변이 표시됩니다."
        )  # 답변이 비어있을 때 안내 문구를 보여줍니다.


if __name__ == "__main__":  # 파이썬 파일이 직접 실행될 때만 아래 영역을 수행합니다.
    main()  # 메인 함수를 실행합니다.
