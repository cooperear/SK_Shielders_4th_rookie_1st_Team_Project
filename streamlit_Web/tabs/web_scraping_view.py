import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from utils import get_db_config
import math
import json
import seaborn as sns
import platform
import matplotlib.pyplot as plt

# --- 한글 폰트 설정 ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')  # Windows
elif platform.system() == 'Darwin':
    plt.rc('font', family='AppleGothic')   # Mac
else:
    plt.rc('font', family='NanumGothic')   # Linux (Colab 등)

plt.rcParams['axes.unicode_minus'] = False  # 마이너스 깨짐 방지

# --- 데이터 로딩 (캐싱 적용) ---
@st.cache_data
def load_data(table_name):
    """
    지정된 테이블에서 데이터를 가져옵니다. 캐싱으로 속도 최적화.
    """
    db_config = get_db_config()
    engine = create_engine(
        f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['database']}?charset=utf8mb4"
    )
    return pd.read_sql(f"SELECT * FROM {table_name}", engine)


def filter_data(data, search_name, selected_tag):
    """
    이름 검색 + 태그 필터링
    """
    if search_name:
        data = data[data["이름"].str.contains(search_name, case=False, na=False)]

    if selected_tag and selected_tag != "전체":
        def has_tag(tag_str):
            try:
                tags = json.loads(tag_str) if isinstance(tag_str, str) else []
                return selected_tag in tags
            except:
                return False

        data = data[data["태그"].apply(has_tag)]

    return data

def render_cards(data, page, per_page=10):
    """
    한 페이지씩 카드 렌더링 (정보 없음 표시 추가)
    """
    start = (page - 1) * per_page
    end = start + per_page
    paginated = data.iloc[start:end]

    for _, row in paginated.iterrows():
        # 이미지
        st.image(row.get("이미지") if row.get("이미지") else "https://via.placeholder.com/200", width=200)

        # 이름 + 성별
        이름 = row.get('이름', '정보 없음')
        성별 = row.get('성별', '정보 없음')
        st.subheader(f"{이름} ({성별})")

        # 출생, 몸무게
        출생 = row.get('출생시기', '정보 없음') if row.get('출생시기') else '정보 없음'
        몸무게 = row.get('몸무게', '정보 없음') if row.get('몸무게') else '정보 없음'
        st.markdown(f"**출생:** {출생}   |   **몸무게:** {몸무게}")

        # 임보 상태 (태그)
        임보상태 = row.get("태그", "정보 없음")
        try:
            if isinstance(임보상태, str):
                임보상태 = ", ".join(json.loads(임보상태))
        except:
            pass
        st.markdown(f"**임보 상태:** {임보상태 if 임보상태 else '정보 없음'}")

        # 임보 조건
        임보조건 = row.get("임보 조건", "")
        try:
            if isinstance(임보조건, str):
                임보조건 = json.loads(임보조건)
        except:
            pass

        st.markdown("### 🏠 임보 조건")
        if 임보조건 and isinstance(임보조건, dict):
            지역 = 임보조건.get('지역', '정보 없음') or '정보 없음'
            기간 = 임보조건.get('임보 기간', '정보 없음') or '정보 없음'
            st.markdown(f"- 지역: {지역}")
            st.markdown(f"- 임보 기간: {기간}")
        else:
            st.markdown("- 정보 없음")

        # 성격 및 특징
        특징 = row.get("성격 및 특징", "")
        st.markdown("### 🐾 성격 및 특징")
        if 특징:
            for line in 특징.split("\n"):
                if line.strip():
                    st.markdown(f"- {line.strip()}")
        else:
            st.markdown("- 정보 없음")

        # 구조 이력
        히스토리 = row.get("히스토리", "")
        try:
            if isinstance(히스토리, str):
                히스토리 = json.loads(히스토리)
        except:
            pass
        st.markdown("### 📜 구조 이력")
        if 히스토리 and isinstance(히스토리, dict):
            for date, event in 히스토리.items():
                st.markdown(f"- {date}: {event if event else '정보 없음'}")
        else:
            st.markdown("- 정보 없음")

        # 건강 정보
        건강 = row.get("건강 정보", "")
        try:
            if isinstance(건강, str):
                건강 = json.loads(건강)
        except:
            pass
        st.markdown("### 🩺 건강 정보")
        if 건강 and isinstance(건강, dict):
            st.markdown(f"- 접종 현황: {건강.get('접종 현황', '정보 없음') or '정보 없음'}")
            st.markdown(f"- 검사 현황: {건강.get('검사 현황', '정보 없음') or '정보 없음'}")
            st.markdown(f"- 병력 사항: {건강.get('병력 사항', '정보 없음') or '정보 없음'}")
            st.markdown(f"- 기타 사항: {건강.get('기타 사항', '정보 없음') or '정보 없음'}")
        else:
            st.markdown("- 정보 없음")

        # 공고 날짜
        공고날짜 = row.get("공고날짜", "정보 없음") or "정보 없음"
        st.markdown(f"### 📅 공고 날짜: {공고날짜}")

        # 사이트 링크
        if row.get("사이트링크"):
            st.markdown(f"[🔗 입양 정보 보러가기]({row.get('사이트링크')})")
        else:
            st.markdown("🔗 입양 정보 보러가기: 정보 없음")

        st.divider()


def show():
    st.title("🏵️ PIMFYVIRUS")

    # -----------------------
    # 카드형 상태 설명
    # -----------------------
    card_style = """
        <div style="
            background-color:{bg};
            padding:15px;
            border-radius:12px;
            text-align:center;
            color:white;
            height:100px;
        ">
            <h4 style="margin-bottom:6px;">{title}</h4>
            <p style="font-size:13px; line-height:1.4; margin:0;">{desc}</p>
        </div>
    """

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### 🟥 임보가능")
        st.caption("임보와 입양 둘 다\n문의가 가능해요")

    with col2:
        st.markdown("### 🟧 임보중")
        st.caption("임보가 시작되어\n입양 문의만 가능해요")

    with col3:
        st.markdown("### 🟠 입양전제")
        st.caption("큰 문제가 없다면\n입양으로 전환돼요")

    with col4:
        st.markdown("### 🟤 릴레이임보")
        st.caption("현 임보처에서 곧\n임보가 종료돼요")

    st.markdown("---")

    # -----------------------
    # 최상위 탭: 입양 정보 / 시각화
    # -----------------------
    main_tab1, main_tab2 = st.tabs(["📋 입양 정보", "📊 시각화"])

    # =======================
    # 1) 입양 정보 탭 (기존)
    # =======================
    with main_tab1:
        tab1, tab2 = st.tabs(["🐱 고양이", "🐶 강아지"])

        # --- 고양이 탭 ---
        with tab1:
            cats = load_data("web_cats")
            if cats.empty:
                st.info("데이터가 없습니다.")
            else:
                st.sidebar.subheader("🐱 고양이 검색 / 필터")
                search_name = st.sidebar.text_input("이름으로 검색", key="cat_search")
                tag_options = ["전체", "임보가능", "입양전제", "임보중", "일반임보"]
                selected_tag = st.sidebar.selectbox("태그 필터", tag_options, key="cat_tag")

                filtered = filter_data(cats, search_name, selected_tag)
                if filtered.empty:
                    st.warning("검색 결과가 없습니다.")
                else:
                    total_pages = math.ceil(len(filtered) / 10)
                    page = st.selectbox(
                        "🐱 고양이 페이지 선택",
                        options=list(range(1, total_pages + 1)),
                        index=0,
                        key="cats_page"
                    )
                    render_cards(filtered, page)

        # --- 강아지 탭 ---
        with tab2:
            dogs = load_data("web_dogs")
            if dogs.empty:
                st.info("데이터가 없습니다.")
            else:
                st.sidebar.subheader("🐶 강아지 검색 / 필터")
                search_name = st.sidebar.text_input("이름으로 검색", key="dog_search")
                tag_options = ["전체", "임보가능", "입양전제", "임보중", "일반임보"]
                selected_tag = st.sidebar.selectbox("태그 필터", tag_options, key="dog_tag")

                filtered = filter_data(dogs, search_name, selected_tag)
                if filtered.empty:
                    st.warning("검색 결과가 없습니다.")
                else:
                    total_pages = math.ceil(len(filtered) / 10)
                    page = st.selectbox(
                        "🐶 강아지 페이지 선택",
                        options=list(range(1, total_pages + 1)),
                        index=0,
                        key="dogs_page"
                    )
                    render_cards(filtered, page)

    # =======================
    # 2) 시각화 탭
    # =======================
    with main_tab2:
        viz_tab1, viz_tab2 = st.tabs(["🐱 고양이", "🐶 강아지"])

        # --- 고양이 시각화 ---
        with viz_tab1:
            cats = load_data("web_cats")
            if cats.empty:
                st.info("고양이 데이터가 없습니다.")
            else:
                def classify_status(tag_str):
                    tag_list = json.loads(tag_str) if isinstance(tag_str, str) else []
                    if '공고종료' in tag_list:
                        return '공고종료'
                    elif '입양완료' in tag_list:
                        return '입양완료'
                    elif '임보중' in tag_list:
                        return '임보중'
                    else:
                        return '임보가능'

                cats['현재 상태'] = cats['태그'].apply(classify_status)
                status_order = cats['현재 상태'].value_counts().sort_values(ascending=False).index.tolist()

                # 컬럼 나누기
                col1, col2 = st.columns(2)

                with col1:
                    fig, ax = plt.subplots(figsize=(4, 3))  # 크기 줄임
                    sns.countplot(data=cats, x='현재 상태', order=status_order, palette='pastel', ax=ax)
                    ax.set_title('임보 고양이 분포', fontsize=12)
                    st.pyplot(fig)

                with col2:
                    status_counts = cats['현재 상태'].value_counts()
                    fig2, ax2 = plt.subplots(figsize=(4, 3))  # 크기 줄임
                    ax2.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%', startangle=140)
                    ax2.set_title('임보 고양이 비율', fontsize=12)
                    st.pyplot(fig2)

        # --- 강아지 시각화 ---
    with viz_tab2:
        dogs = load_data("web_dogs")
        if dogs.empty:
            st.info("강아지 데이터가 없습니다.")
        else:
            def classify_status(tag_str):
                tag_list = json.loads(tag_str) if isinstance(tag_str, str) else []
                if '공고종료' in tag_list:
                    return '공고종료'
                elif '입양완료' in tag_list:
                    return '입양완료'
                elif '임보중' in tag_list:
                    return '임보중'
                else:
                    return '임보가능'

            dogs['현재 상태'] = dogs['태그'].apply(classify_status)
            status_order = dogs['현재 상태'].value_counts().sort_values(ascending=False).index.tolist()

            # 컬럼 나누기
            col1, col2 = st.columns(2)

            # 막대 그래프
            with col1:
                fig3, ax3 = plt.subplots(figsize=(4, 3))  # 사이즈 축소
                sns.countplot(data=dogs, x='현재 상태', order=status_order, palette='pastel', ax=ax3)
                ax3.set_title('임보 강아지 분포', fontsize=12)
                st.pyplot(fig3)

            # 파이 차트
            with col2:
                status_counts = dogs['현재 상태'].value_counts()
                fig4, ax4 = plt.subplots(figsize=(4, 3))  # 사이즈 축소
                ax4.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%', startangle=140)
                ax4.set_title('임보 강아지 비율', fontsize=12)
                st.pyplot(fig4)