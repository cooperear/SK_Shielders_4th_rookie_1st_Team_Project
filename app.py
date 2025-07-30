import streamlit as st
from tabs import map_view, stats_view, detail_view, favorites_view
from data_manager import init_db, get_filtered_data

# --- 1. 페이지 설정 및 초기화 ---
st.set_page_config(page_title="입양 대기 동물 분석", layout="wide")

# DB 초기화 (최초 실행 시 테이블 생성 및 데이터 삽입)
init_db()

# 세션 상태 초기화 (찜 목록)
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

st.title("🐾 전국 입양 대기 동물 현황")

# --- 2. 사이드바 필터 ---
st.sidebar.header("🔍 검색 및 필터")

search_query = st.sidebar.text_input(
    "동물 이름으로 검색",
    placeholder="예: 초코, 하양이",
    help="검색어와 일치하는 이름을 가진 동물이 있는 보호소를 찾습니다."
)

st.sidebar.markdown("---")

region_filter = st.sidebar.selectbox(
    "지역 선택",
    options=["전체"] + ["서울", "부산", "대구", "인천"],
    help="분석할 지역을 선택하세요."
)

species_filter = st.sidebar.multiselect(
    "품종 선택",
    options=["개", "고양이"],
    help="분석할 품종을 선택하세요. 여러 개 선택할 수 있습니다."
)

# 필터링된 데이터 가져오기
filtered_data = get_filtered_data(region_filter, species_filter, search_query)

# --- 3. KPI 카드 ---
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("보호소 수", filtered_data['shelter_name'].nunique())
col_b.metric("보호 동물 수", int(filtered_data['count'].sum()))
col_c.metric("장기 보호 동물 수", int(filtered_data['long_term'].sum()))
col_d.metric("입양 완료 수", int(filtered_data['adopted'].sum()))


# --- 4. 탭 구성 ---
tab_labels = ["📍 지도 & 분석", "📊 통계 차트", "📋 보호소 상세 현황", f"❤️ 찜한 동물 ({len(st.session_state.favorites)})" ]

# st.session_state를 사용하여 탭 인덱스 관리
if "active_tab_idx" not in st.session_state:
    st.session_state.active_tab_idx = 0 # 기본값은 첫 번째 탭

# map_view에서 보낸 신호(active_tab)를 받아 인덱스 업데이트
if "active_tab" in st.session_state:
    try:
        st.session_state.active_tab_idx = tab_labels.index(st.session_state.active_tab)
    except ValueError:
        st.session_state.active_tab_idx = 0
    del st.session_state.active_tab # 신호 처리 후 삭제

# st.radio를 사용하여 탭 UI 생성
active_tab = st.radio(
    "탭 선택",
    tab_labels,
    index=st.session_state.active_tab_idx,
    key="tab_selection",
    horizontal=True,
)

# 선택된 탭에 따라 해당 모듈의 함수 호출
if active_tab.startswith("📍 지도 & 분석"):
    map_view.show(filtered_data)
elif active_tab.startswith("📊 통계 차트"):
    stats_view.show(filtered_data)
elif active_tab.startswith("📋 보호소 상세 현황"):
    detail_view.show(filtered_data)
elif active_tab.startswith("❤️ 찜한 동물"):
    favorites_view.show()
