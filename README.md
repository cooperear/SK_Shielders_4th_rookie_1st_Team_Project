# 🐾 Hello Home: 유기동물 입양 정보 분석 및 예측 대시보드

![Project Logo](streamlit_Web/data/HelloHome_ICON_%ED%88%AC%EB%AA%85.png)

**Hello Home**은 전국 유기동물 보호소의 데이터를 실시간으로 분석하고, 입양률을 예측하여 예비 입양자들이 따뜻한 가족을 더 쉽게 만날 수 있도록 돕는 웹 애플리케이션입니다.

이 프로젝트는 SK쉴더스 루키즈 과정의 팀 프로젝트로, 데이터 수집부터 분석, 시각화, 예측 모델링, 그리고 웹 개발까지 전 과정을 다루고 있습니다.

## ✨ 주요 기능

1.  **🗺️ 인터랙티브 지도 & 상세 정보:** 전국 보호소의 위치를 지도에서 한눈에 확인하고, 각 보호소의 상세 정보(보호 동물 수, 입양률, 장기 보호 동물 수 등)를 조회할 수 있습니다.
2.  **📊 핵심 통계 대시보드:** 필터링된 데이터를 기반으로 유기동물의 주요 현황(축종, 품종, 나이대별 분포 및 입양률)과 시간/지역별 패턴을 분석하는 다양한 인터랙티브 차트를 제공합니다.
3.  **🔍 입양 영향 요인 분석:** 동물의 다양한 특성(나이, 성별, 중성화 여부, 색상 등)이 입양 성공 여부에 어떤 영향을 미치는지 심층적으로 분석하여 보여줍니다.
4.  **🔮 입양률 예측:** LSTM 모델을 활용하여 미래의 유기동물 발생 건수를 예측하고, 이를 통해 보호소 운영 및 입양 캠페인에 대한 인사이트를 제공합니다.
5.  **❤️ 찜 목록:** 마음에 드는 동물을 찜 목록에 추가하여 언제든지 다시 확인할 수 있습니다.

## 🛠️ 기술 스택

*   **언어:** Python
*   **데이터 분석 및 처리:** Pandas, NumPy
*   **웹 프레임워크:** Streamlit
*   **데이터 시각화:** Plotly Express
*   **머신러닝/딥러닝:** TensorFlow, Keras (LSTM)
*   **데이터베이스:** MySQL (MariaDB)
*   **데이터 수집:** Public Data Portal API, Kakao Maps API

## 📂 프로젝트 구조

```
team_project/
├── .gitignore              # Git 버전 관리에서 제외할 파일 목록
├── check_db_schema.py      # 데이터베이스 스키마 확인용 스크립트
├── README.md               # 프로젝트 설명서 (현재 파일)
├── config.ini.example      # (추천) API 키 및 DB 정보 설정 예시 파일
├── requirements.txt        # (추천) 프로젝트 필요 라이브러리 목록
│
└── streamlit_Web/
    ├── app.py              # 🌐 **메인 애플리케이션 실행 파일**
    ├── data_manager.py     # 🗄️ 데이터베이스 연결 및 데이터 로딩 관리
    ├── update_data.py      # 🔄 외부 API로부터 데이터 수집 및 DB 업데이트
    ├── utils.py            # 🛠️ 기타 유틸리티 함수
    │
    ├── data/               # 🖼️ 로고 이미지 등 정적 파일
    │   └── HelloHome_ICON_투명.png
    │
    ├── lstm_model/         # 🧠 LSTM 예측 모델 관련 파일
    │   ├── lstm_improved.py
    │   └── lstm_model_animal_shelter_improved.h5
    │
    └── tabs/               # 📑 각 탭(페이지)을 구성하는 모듈
        ├── map_view.py
        ├── stats_view.py
        ├── correlation_view.py
        ├── detail_view.py
        ├── prediction_view.py
        └── favorites_view.py
```

### 파일 설명

*   **`streamlit_Web/app.py`**: 웹 애플리케이션의 **시작점(Entry Point)**입니다. 전체적인 UI 레이아웃, 사이드바 필터, 탭 전환 등 핵심 로직을 담당합니다.
*   **`streamlit_Web/update_data.py`**: 공공데이터포털과 카카오 API를 통해 유기동물 및 보호소 데이터를 **수집(Extract), 가공(Transform), 데이터베이스에 적재(Load)**하는 ETL 파이프라인 스크립트입니다. **주기적으로 실행**하여 데이터를 최신 상태로 유지해야 합니다.
*   **`streamlit_Web/data_manager.py`**: 데이터베이스 연결(Connection Pool), 데이터 조회, 캐싱 등 데이터와 관련된 모든 작업을 관리하는 모듈입니다.
*   **`streamlit_Web/tabs/*.py`**: 각 탭에 표시될 화면을 구성하는 파일들입니다. 각 파일은 `show()` 함수를 통해 `app.py`에서 호출됩니다.
    *   `map_view.py`: 지도 및 보호소 분석 화면
    *   `stats_view.py`: 핵심 통계 대시보드 화면
    *   `correlation_view.py`: 입양 영향 요인 분석 화면
    *   `detail_view.py`: 보호소 상세 현황 테이블 화면
    *   `prediction_view.py`: LSTM 예측 결과 화면
    *   `favorites_view.py`: 찜한 동물 목록 화면
*   **`lstm_model/`**: LSTM 예측 모델과 관련 코드들이 저장된 디렉토리입니다.

## 🚀 시작하기

### 1. 사전 준비

*   Python 3.8 이상 설치
*   MySQL (또는 MariaDB) 데이터베이스 서버 설치 및 실행

### 2. 프로젝트 클론

```bash
git clone https://github.com/your-username/team_project.git
cd team_project
```

### 3. 라이브러리 설치

프로젝트에 필요한 라이브러리들을 설치합니다. (아래는 예상되는 라이브러리 목록이며, `requirements.txt` 파일을 생성하여 관리하는 것을 권장합니다.)

```bash
pip install streamlit pandas numpy plotly sqlalchemy mysql-connector-python tensorflow
```

### 4. 설정 파일 생성

`config.ini.example` 파일을 복사하여 `config.ini` 파일을 생성하고, 파일 내에 자신의 API 키와 데이터베이스 접속 정보를 입력합니다.

**`config.ini`**
```ini
[API]
service_key = YOUR_PUBLIC_DATA_API_KEY
kakao_rest_api_key = YOUR_KAKAO_REST_API_KEY

[DB]
host = localhost
port = 3306
user = your_db_user
password = your_db_password
database = shelter_db
```

### 5. 데이터베이스 업데이트

웹 애플리케이션을 실행하기 전에, 먼저 `update_data.py` 스크립트를 실행하여 데이터베이스에 최신 데이터를 채워야 합니다.

```bash
python streamlit_Web/update_data.py
```
> ⚠️ **주의:** 이 과정은 API 호출량에 따라 몇 분 정도 소요될 수 있습니다.

### 6. 웹 애플리케이션 실행

아래 명령어를 실행하여 Streamlit 웹 서버를 시작합니다.

```bash
streamlit run streamlit_Web/app.py
```

이제 웹 브라우저에서 `http://localhost:8501` 주소로 접속하여 **Hello Home** 대시보드를 확인할 수 있습니다!

---