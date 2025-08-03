# ==============================================================================
# app.py - Streamlit 메인 애플리케이션
# ==============================================================================
# 이 파일은 전체 웹 애플리케이션의 시작점(entry point)입니다.
# Streamlit을 사용하여 사용자 인터페이스(UI)를 구성하고, 각 탭(페이지)을
# 관리하며, 사용자 입력에 따라 데이터를 필터링하고 시각화하는 역할을 합니다.
#
# [주요 흐름]
# 1. **페이지 설정 및 초기화:** 웹페이지의 기본 설정(제목, 레이아웃)을 지정하고,
#    데이터베이스 연결을 확인하며, 세션 상태(찜 목록 등)를 초기화합니다.
# 2. **사이드바 필터:** 사용자가 데이터를 필터링할 수 있는 컨트롤(날짜, 텍스트,
#    지역, 축종 선택 등)을 사이드바에 배치합니다.
# 3. **데이터 필터링:** 사이드바에서 사용자가 선택한 조건에 따라
#    DB에서 로드한 전체 데이터 중 필요한 부분만 필터링합니다.
# 4. **핵심 지표(KPI) 표시:** 필터링된 결과를 바탕으로 주요 수치(보호소 수,
#    보호 동물 수 등)를 계산하여 화면 상단에 표시합니다.
# 5. **탭 구성 및 화면 전환:** 사용자가 선택한 탭에 따라 `map_view`, `stats_view`,
#    `detail_view`, `favorites_view` 모듈의 `show()` 함수를 호출하여
#    해당하는 화면을 동적으로 보여줍니다.
# ==============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
from pathlib import Path

# 각 탭(페이지)에 해당하는 화면 구성 모듈들을 임포트합니다.
from tabs import map_view, stats_view, detail_view, favorites_view, prediction_view, correlation_view

# 데이터 로딩 및 관리를 위한 함수들을 임포트합니다.
from data_manager import init_db, load_data, get_sido_list, get_sigungu_list, get_kind_list

import streamlit.web.server.component_request_handler as crh

_original_get = crh.ComponentRequestHandler.get

def safe_get(self, abspath):
    try:
        return _original_get(self, abspath)
    except FileNotFoundError:
        return None  # None 경로 접근 시 조용히 무시

crh.ComponentRequestHandler.get = safe_get

# --- 이미지 Base64 인코딩 함수 ---
def get_image_as_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

# --- 1. 페이지 설정 및 초기화 ---
# 웹 브라우저 탭에 표시될 제목과 페이지 전체의 레이아웃을 설정합니다.
st.set_page_config(page_title="입양 대기 동물 분석", layout="wide")

# 현재 활성화된 탭의 인덱스를 세션 상태에 저장하여, 다른 상호작용 후에도 탭이 유지되도록 합니다.
if "active_tab_idx" not in st.session_state:
    st.session_state.active_tab_idx = 0

# --- 1. 페이지 설정 및 초기화 ---
logo_path = "data/HelloHome_ICON_투명.png"
logo_base64 = get_image_as_base64(logo_path)

st.markdown(f"""
<div style="text-align: center; padding: 2rem 0 2.5rem 0;">
    <div style='display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;'>
        {f'<img src="data:image/png;base64,{logo_base64}" style="height: 4.1rem; margin-right: 15px;">' if logo_base64 else ''}
        <h1 style='color: #212529; font-weight: 800; font-size: 4.1rem; margin: 0;'>Hello Home</h1>
    </div>
    <p style='color: #495057; font-size: 1.25rem; margin: 0;'>
        전국 보호소의 유기동물 정보를 확인하고, 따뜻한 가족이 되어주세요.
    </p>
</div>
""", unsafe_allow_html=True)

# --- 2. Modern UI Style Injection ---
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
    
    /* --- General & Body --- */
    .stApp {
        background-color: #FAF8F0; /* Warm Ivory Background */
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* --- Main Content Area --- */
    .block-container {
        padding: 2rem 3rem 3rem 3rem !important;
    }

    /* --- Sidebar --- */
    [data-testid="stSidebar"] {
        background-color: #F5F1E9; /* Soft Beige Sidebar */
        border-right: 1px solid #E0DBCF;
    }
    [data-testid="stSidebar"] h2 {
        color: #B58A60; /* Warm Brown Accent */
        font-weight: 700;
    }
    [data-testid="stExpander"] summary {
        font-weight: 600;
        color: #B58A60;
    }
    
    /* --- MultiSelect (축종 선택) & General Input Accent --- */
    span[data-baseweb="tag"] {
        background-color: #B58A60 !important;
        color: #FFFFFF !important;
        border-radius: 0.75rem;
    }
    /* This targets the native radio button dot/check */
    input[type="radio"] {
        accent-color: #B58A60 !important;
    }

    /* --- KPI Cards --- */
    .kpi-card {
        background-color: #FFFFFF;
        padding: 1.75rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06);
        text-align: center;
        transition: all 0.3s ease-in-out;
        border-bottom: 4px solid #B58A60;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 25px rgba(0, 0, 0, 0.1);
    }
    .kpi-card .icon { font-size: 2.8rem; line-height: 1; margin-bottom: 0.75rem; }
    .kpi-card .title { font-size: 1.05rem; font-weight: 500; color: #6C757D; margin-bottom: 0.5rem; }
    .kpi-card .number { font-size: 2.2rem; font-weight: 700; color: #343A40; }

    /* --- Tab Navigation (stRadio) --- */
    div[role="radiogroup"] {
        display: flex;
        justify-content: center;
        margin: 2.5rem 0 2rem 0;
        gap: 1rem;
    }
    div[role="radiogroup"] > label {
        display: inline-block;
        padding: 0.75rem 1.75rem;
        background: #FFFFFF;
        color: #495057;
        border-radius: 30px;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 1px solid #DEE2E6;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        font-weight: 600;
    }
    /* Tab Hover */
    div[role="radiogroup"] > label:hover {
        background-color: #F5F1E9;
        border-color: #B58A60;
        color: #B58A60;
    }
    /* Selected tab style */
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #F5F1E9; /* Soft Beige, same as hover */
        color: #B58A60; /* Warm Brown Text */
        border: 2px solid #B58A60; /* Thicker Warm Brown Border */
        box-shadow: 0 5px 15px rgba(181, 138, 96, 0.4);
        padding: calc(0.75rem - 1px) calc(1.75rem - 1px); /* Adjust padding to keep size consistent */
    }
    /* Hide the actual radio button and its focus ring */
    div[role="radiogroup"] input[type="radio"] {
        display: none; /* This is the key to the button look */
    }
    /* Custom focus ring to override browser default (which can be red/blue) */
    div[role="radiogroup"] label:focus-within {
        outline: none;
        box-shadow: 0 0 0 2px #F5F1E9, 0 0 0 4px #B58A60;
    }
    
    /* --- Footer --- */
    .footer {
        text-align: center;
        margin-top: 4rem;
        color: #868E96;
        font-size: 0.9rem;
    }
    .footer a {
        color: #B58A60;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# 데이터베이스 연결을 확인하고, 테이블이 존재하는지 검사합니다.
init_db()

# `st.session_state`를 사용하여 사용자의 세션 동안 유지되어야 할 데이터를 관리합니다.
# 'favorites'는 사용자가 찜한 동물의 목록을 저장하며, 앱이 재실행되어도 유지됩니다.
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

# --- 2. 사이드바 필터 ---
# 화면 왼쪽에 고정되는 사이드바에 필터링 UI 요소들을 배치합니다.
st.sidebar.header("🔍 검색 및 필터")

# 날짜 필터 (expander로 묶기)
with st.sidebar.expander("🗓️ 공고일 기준 검색", expanded=True):
    start_date = st.date_input("시작일", datetime.now() - timedelta(days=30))
    end_date = st.date_input("종료일", datetime.now())

# 축종 필터
with st.sidebar.expander("🐾 축종 선택", expanded=True):
    species_filter = st.multiselect(
        "축종 선택",
        options=["개", "고양이", "기타"],
        default=["개", "고양이", "기타"]
    )

# 지역 필터
sido_list = get_sido_list()
sido_names = ["전체"] + [s['name'] for s in sido_list]

with st.sidebar.expander("📍 지역 선택", expanded=True):
    selected_sido_name = st.selectbox("시도 선택", sido_names)
    if selected_sido_name != "전체":
        selected_sido_code = next((s['code'] for s in sido_list if s['name'] == selected_sido_name), None)
        if selected_sido_code:
            sigungu_list = get_sigungu_list(selected_sido_code)
            sigungu_names = ["전체"] + [s['name'] for s in sigungu_list]
            selected_sigungu_name = st.selectbox("시군구 선택", sigungu_names)
    else:
        selected_sigungu_name = "전체"


# --- 3. 데이터 필터링 로직 ---
@st.cache_data
def get_filtered_data(start_date, end_date, sido, sigungu, species):
    """
    사용자 입력(필터)에 따라 동물 및 보호소 데이터를 필터링하는 함수입니다.
    
    Args:
        start_date (date): 조회 시작일
        end_date (date): 조회 종료일
        sido (str): 선택된 시/도 이름
        sigungu (str): 선택된 시/군/구 이름
        species (list): 선택된 축종 목록

    Returns:
        tuple: 필터링된 동물 데이터, 보호소 데이터, 그리고 KPI 값들
    """
    animals = load_data("animals")
    shelters = load_data("shelters")

    if animals.empty or shelters.empty:
        return pd.DataFrame(), pd.DataFrame(), 0, 0, 0, 0

    # 1. 날짜 필터링 (공고일 기준)
    animals['notice_date'] = pd.to_datetime(animals['notice_date'])
    mask = (animals['notice_date'].dt.date >= start_date) & (animals['notice_date'].dt.date <= end_date)
    filtered_animals = animals[mask]

    # 축종 필터
    if species:
        filtered_animals = filtered_animals[filtered_animals['upkind_name'].isin(species)]

    # 필터링된 동물 목록을 기반으로, 해당 동물들이 있는 보호소 목록을 구합니다.
    shelter_names_with_animals = filtered_animals['shelter_name'].unique()
    filtered_shelters = shelters[shelters['shelter_name'].isin(shelter_names_with_animals)]

    # 4. 지역 필터링 (보호소 주소 기준)
    addr_col = "care_addr" if "care_addr" in filtered_shelters.columns else "careAddr"
    if sido != "전체":
        filtered_shelters = filtered_shelters[filtered_shelters[addr_col].str.startswith(sido, na=False)]
    if sigungu != "전체":
        full_region_name = f"{sido} {sigungu}"
        filtered_shelters = filtered_shelters[filtered_shelters[addr_col].str.startswith(full_region_name, na=False)]

    # 최종적으로 필터링된 보호소에 소속된 동물들만 다시 추립니다.
    final_animal_shelters = filtered_shelters['shelter_name'].unique()
    final_animals = filtered_animals[filtered_animals['shelter_name'].isin(final_animal_shelters)]

    # KPI 계산
    shelter_count = filtered_shelters['shelter_name'].nunique()
    animal_count = len(final_animals)
    long_term_count = int(filtered_shelters['long_term'].sum())
    adopted_count = int(filtered_shelters['adopted'].sum())

    return final_animals, filtered_shelters, shelter_count, animal_count, long_term_count, adopted_count

# --- 데이터 로딩 및 스피너 표시 ---
with st.spinner("🐾 데이터를 열심히 불러오고 있어요... 잠시만 기다려주세요!"):
    final_animals, filtered_shelters, shelter_count, animal_count, long_term_count, adopted_count = get_filtered_data(
        start_date, end_date, selected_sido_name, selected_sigungu_name, species_filter
    )

# --- 데이터가 없을 경우 처리 ---
if final_animals.empty:
    st.info("🐾 해당 조건에 맞는 동물이 없습니다. 필터 조건을 변경해 보세요!", icon="ℹ️")
else:
    # --- 4. KPI 카드 ---
    st.write("""<div style="height: 1.5rem;"></div>""", unsafe_allow_html=True) # Spacer
    kpi_cols = st.columns(4)
    kpi_data = [
        ("🏠", "보호소 수", shelter_count),
        ("🐾", "보호 동물 수", animal_count),
        ("⏳", "장기 보호 동물", long_term_count),
        ("❤️", "입양 완료", adopted_count)
    ]

    for col, (icon, title, number) in zip(kpi_cols, kpi_data):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="icon">{icon}</div>
                <div class="title">{title}</div>
                <div class="number">{number}</div>
            </div>
            """, unsafe_allow_html=True)
    st.write("""<div style="height: 1rem;"></div>""", unsafe_allow_html=True) # Spacer

    # --- 5. 탭 구성 ---
    tab_labels = ["📍 지도 & 분석", "📊 통계 차트", "🔍 상관관계 분석", "📋 보호소 상세 현황", "🔮 예측", f"❤️ 찜한 동물 ({len(st.session_state.favorites)})" ]

    def on_tab_change():
        st.session_state.active_tab_idx = tab_labels.index(st.session_state.tab_selection)

    st.radio(
        "탭 선택",
        tab_labels,
        index=st.session_state.active_tab_idx,
        key="tab_selection",
        horizontal=True,
        on_change=on_tab_change,
        label_visibility="collapsed"
    )

    active_tab_idx = st.session_state.get('active_tab_idx', 0)
    if active_tab_idx == 0:
        map_view.show(filtered_shelters, final_animals, tab_labels)
    elif active_tab_idx == 1:
        stats_view.show(final_animals, filtered_shelters)
    elif active_tab_idx == 2:
        correlation_view.show(final_animals, filtered_shelters)
    elif active_tab_idx == 3:
        detail_view.show(filtered_shelters)
    elif active_tab_idx == 4:
        prediction_view.show()
    elif active_tab_idx == 5:
        favorites_view.show()

# --- 6. Footer ---
st.markdown("""
<hr style="margin-top: 3rem; border-top: 1px solid #E9ECEF;">
<div class="footer">
    Data provided by <a href="https://www.data.go.kr/" target="_blank">공공데이터포털</a> | Designed by Gemini
</div>
""", unsafe_allow_html=True)