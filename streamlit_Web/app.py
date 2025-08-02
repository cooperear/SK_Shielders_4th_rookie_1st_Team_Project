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

# 각 탭(페이지)에 해당하는 화면 구성 모듈들을 임포트합니다.
from tabs import map_view, stats_view, detail_view, favorites_view

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

# --- 1. 페이지 설정 및 초기화 ---
# 웹 브라우저 탭에 표시될 제목과 페이지 전체의 레이아웃을 설정합니다.
st.set_page_config(page_title="입양 대기 동물 분석", layout="wide")

# 현재 활성화된 탭의 인덱스를 세션 상태에 저장하여, 다른 상호작용 후에도 탭이 유지되도록 합니다.
if "active_tab_idx" not in st.session_state:
    st.session_state.active_tab_idx = 0

# 데이터베이스 연결을 확인하고, 테이블이 존재하는지 검사합니다.
init_db()

# `st.session_state`를 사용하여 사용자의 세션 동안 유지되어야 할 데이터를 관리합니다.
# 'favorites'는 사용자가 찜한 동물의 목록을 저장하며, 앱이 재실행되어도 유지됩니다.
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

# 웹페이지의 메인 타이틀을 설정합니다.
st.title("🐾 전국 입양 대기 동물 현황")

# --- 2. 사이드바 필터 ---
# 화면 왼쪽에 고정되는 사이드바에 필터링 UI 요소들을 배치합니다.
st.sidebar.header("🔍 검색 및 필터")

# 날짜 필터: 사용자가 공고일 기준으로 데이터를 조회할 기간을 선택합니다.
st.sidebar.markdown("### 🗓️ 공고일 기준 검색")
start_date = st.sidebar.date_input("시작일", datetime.now() - timedelta(days=30)) # 기본값: 30일 전
end_date = st.sidebar.date_input("종료일", datetime.now()) # 기본값: 오늘

st.sidebar.markdown("---") # 구분선

# 축종 필터 (개/고양이/기타)
species_filter = st.sidebar.multiselect(
    "축종 선택",
    options=["개", "고양이", "기타"],
    default=["개", "고양이", "기타"],
    help="분석할 축종을 선택하세요."
)

st.sidebar.markdown("---")

# 지역 및 품종 필터: 드롭다운 메뉴(selectbox)와 다중 선택(multiselect)을 사용합니다.
sido_list = get_sido_list() # DB에서 시/도 목록을 가져옵니다.
sido_names = ["전체"] + [s['name'] for s in sido_list]
selected_sido_name = st.sidebar.selectbox("시도 선택", sido_names)

# 시/도 선택에 따라 동적으로 시/군/구 목록을 업데이트합니다.
selected_sigungu_name = "전체"
if selected_sido_name != "전체":
    # 선택된 시/도 이름에 해당하는 코드를 찾습니다.
    selected_sido_code = next((s['code'] for s in sido_list if s['name'] == selected_sido_name), None)
    if selected_sido_code:
        sigungu_list = get_sigungu_list(selected_sido_code) # 해당 시/도의 시/군/구 목록을 가져옵니다.
        sigungu_names = ["전체"] + [s['name'] for s in sigungu_list]
        selected_sigungu_name = st.sidebar.selectbox("시군구 선택", sigungu_names)
else:
    # 시/도가 '전체'일 경우, 시/군/구 선택은 비활성화됩니다.
    st.sidebar.selectbox("시군구 선택", ["전체"], disabled=True)


# --- 3. 데이터 필터링 로직 ---
def get_filtered_data(start_date, end_date, sido, sigungu, species):
    """
    사용자 입력(필터)에 따라 동물 및 보호소 데이터를 필터링하는 함수입니다.
    
    Args:
        start_date (date): 조회 시작일
        end_date (date): 조회 종료일
        sido (str): 선택된 시/도 이름
        sigungu (str): 선택된 시/군/구 이름
        species (list): 선택된 축종 목록
        query (str): 검색어

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
    if species:  # species_filter 값이 선택된 경우
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

    # KPI 계산: 필터링된 결과를 바탕으로 주요 지표를 계산합니다.
    shelter_count = filtered_shelters['shelter_name'].nunique()
    animal_count = len(final_animals)
    long_term_count = int(filtered_shelters['long_term'].sum())
    adopted_count = int(filtered_shelters['adopted'].sum())

    return final_animals, filtered_shelters, shelter_count, animal_count, long_term_count, adopted_count

# 위에서 정의한 함수를 호출하여 필터링된 데이터를 가져옵니다.
final_animals, filtered_shelters, shelter_count, animal_count, long_term_count, adopted_count = get_filtered_data(
    start_date, end_date, selected_sido_name, selected_sigungu_name, species_filter
)

# --- 4. KPI 카드 ---
# 계산된 주요 지표들을 `st.metric`을 사용하여 시각적으로 강조하여 보여줍니다.
col1, col2, col3, col4 = st.columns(4) # 4개의 컬럼으로 레이아웃을 나눕니다.
with col1:
    st.markdown(f"""
    <div style='background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center'>
        <div style='font-size:24px;'>🏠</div>
        <div style='font-size:18px; font-weight:bold;'>보호소 수</div>
        <div style='font-size:28px; color:#4CAF50;'>{shelter_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style='background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center'>
        <div style='font-size:24px;'>🐾</div>
        <div style='font-size:18px; font-weight:bold;'>보호 동물 수</div>
        <div style='font-size:28px; color:#2196F3;'>{animal_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div style='background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center'>
        <div style='font-size:24px;'>⏳</div>
        <div style='font-size:18px; font-weight:bold;'>장기 보호 동물 수</div>
        <div style='font-size:28px; color:#FF9800;'>{long_term_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div style='background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center'>
        <div style='font-size:24px;'>❤️</div>
        <div style='font-size:18px; font-weight:bold;'>입양 완료 수</div>
        <div style='font-size:28px; color:#E91E63;'>{adopted_count}</div>
    </div>
    """, unsafe_allow_html=True)


# --- 5. 탭 구성 ---
# `st.radio`를 사용하여 탭 메뉴를 만들고, 수평으로 표시합니다.
# 찜한 동물의 수를 탭 레이블에 동적으로 표시하여 사용자 편의성을 높입니다.
tab_labels = ["📍 지도 & 분석", "📊 통계 차트", "📋 보호소 상세 현황", f"❤️ 찜한 동물 ({len(st.session_state.favorites)})" ]

# 사용자가 탭을 선택하면 `active_tab_idx`가 업데이트됩니다.
active_tab_selection = st.radio(
    "탭 선택",
    tab_labels,
    index=st.session_state.active_tab_idx,
    key="tab_selection",
    horizontal=True,
    label_visibility="collapsed"
)

# 선택된 탭이 변경되었는지 확인하고, 세션 상태를 업데이트합니다.
if active_tab_selection != tab_labels[st.session_state.active_tab_idx]:
    st.session_state.active_tab_idx = tab_labels.index(active_tab_selection)
    st.rerun()

# `active_tab_idx` 값에 따라 해당 탭의 `show()` 함수를 호출하여 화면을 렌더링합니다.
if st.session_state.active_tab_idx == 0:
    map_view.show(filtered_shelters, final_animals, tab_labels)
elif st.session_state.active_tab_idx == 1:
    stats_view.show(filtered_shelters)
elif st.session_state.active_tab_idx == 2:
    detail_view.show(filtered_shelters)
elif st.session_state.active_tab_idx == 3:
    favorites_view.show()