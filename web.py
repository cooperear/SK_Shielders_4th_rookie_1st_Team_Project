import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="입양 대기 동물 분석", layout="wide")

st.title("🐾 전국 입양 대기 동물 현황 (Demo)")

# ---- 1. Mock Data (보호소 단위 + 이미지) ----
mock_data = pd.DataFrame({
    "shelter_name": ["서울 보호소", "부산 보호소", "대구 보호소", "인천 보호소"],
    "region": ["서울", "부산", "대구", "인천"],
    "lat": [37.5665, 35.1796, 35.8714, 37.4563],
    "lon": [126.9780, 129.0756, 128.6014, 126.7052],
    "species": ["개", "고양이", "개", "고양이"],
    "count": [12, 8, 5, 6],
    "long_term": [3, 2, 1, 2],
    "adopted": [9, 6, 4, 4],
    "image_url": [
        "https://cdn.pixabay.com/photo/2017/02/20/18/03/dog-2083492_960_720.jpg",
        "https://cdn.pixabay.com/photo/2016/02/19/10/00/cat-1209813_960_720.jpg",
        "https://cdn.pixabay.com/photo/2014/12/10/21/01/dog-563282_960_720.jpg",
        "https://cdn.pixabay.com/photo/2016/02/19/10/00/cat-1209813_960_720.jpg"
    ]
})

# ---- 2. 동물 상세 Mock Data (보호소별 동물) ----
animal_data = pd.DataFrame([
    {"shelter_name": "서울 보호소", "animal_name": "초코", "species": "개", "age": "2살",
     "image_url": "https://cdn.pixabay.com/photo/2017/02/20/18/03/dog-2083492_960_720.jpg"},
    {"shelter_name": "서울 보호소", "animal_name": "하양이", "species": "고양이", "age": "1살",
     "image_url": "https://cdn.pixabay.com/photo/2016/02/19/10/00/cat-1209813_960_720.jpg"},
    {"shelter_name": "부산 보호소", "animal_name": "콩이", "species": "개", "age": "3살",
     "image_url": "https://cdn.pixabay.com/photo/2014/12/10/21/01/dog-563282_960_720.jpg"}
])

# ---- 3. Session State 초기화 ----
if "selected_shelter" not in st.session_state:
    st.session_state.selected_shelter = None
if "active_tab" not in st.session_state:  # 현재 탭 상태 저장
    st.session_state.active_tab = "map"

# ---- 4. 사이드바 필터 ----
st.sidebar.header("🔍 필터")
region_filter = st.sidebar.selectbox("지역 선택", ["전체"] + list(mock_data['region'].unique()))
species_filter = st.sidebar.multiselect("품종 선택", list(mock_data['species'].unique()))

filtered = mock_data.copy()
if region_filter != "전체":
    filtered = filtered[filtered["region"] == region_filter]
if species_filter:
    filtered = filtered[filtered["species"].isin(species_filter)]

# ---- 5. KPI 카드 ----
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("보호소 수", len(filtered['shelter_name'].unique()))
col_b.metric("보호 동물 수", int(filtered['count'].sum()))
col_c.metric("장기 보호 동물 수", int(filtered['long_term'].sum()))
col_d.metric("입양 완료 수", int(filtered['adopted'].sum()))

# ---- 6. 탭 구성 (라디오 버튼 기반) ----
tab_labels = ["📍 지도 & 분석", "📊 통계 차트", "📋 보호소 상세 현황"]

active_tab = st.radio(
    "탭 선택",
    tab_labels,
    index=tab_labels.index("📋 보호소 상세 현황") if st.session_state.active_tab == "detail" else 0,
    horizontal=True,
    label_visibility="collapsed"
)
st.session_state.active_tab = "detail" if active_tab == "📋 보호소 상세 현황" else "map"

# ===========================
# TAB 1: 지도
# ===========================
if active_tab == "📍 지도 & 분석":
    st.subheader("📍 보호소 지도")

    # 지도는 한번만 그리도록 최적화
    map_placeholder = st.empty()
    with map_placeholder:
        m = folium.Map(location=[36.5, 127.5], zoom_start=7)
        for _, row in filtered.iterrows():
            popup_html = f"""
            <b>{row['shelter_name']}</b><br>
            <img src='{row['image_url']}' width='150'><br>
            지역: {row['region']}<br>
            품종: {row['species']}<br>
            보호 중: {row['count']} 마리<br>
            장기 보호: {row['long_term']} 마리<br>
            입양 완료: {row['adopted']} 마리
            """
            folium.Marker(
                [row['lat'], row['lon']],
                popup=popup_html,
                tooltip=row['shelter_name'],
                icon=folium.Icon(color="blue", icon="paw", prefix='fa')
            ).add_to(m)

        # 지도 이벤트 감지
        map_event = st_folium(m, width=1000, height=600)

        if map_event.get("last_object_clicked_tooltip"):
            st.session_state.selected_shelter = map_event["last_object_clicked_tooltip"]
            st.session_state.active_tab = "detail"  # 상세 탭으로 전환
            st.rerun()  # 전체 새로고침 대신 한번만 전환

# ===========================
# TAB 2: 차트
# ===========================
elif active_tab == "📊 통계 차트":
    st.subheader("📊 품종별 보호 동물 수")
    if not filtered.empty:
        species_chart = filtered.groupby("species")["count"].sum().reset_index()
        fig = px.bar(
            species_chart,
            x="species",
            y="count",
            color="species",
            text="count",
            template="plotly_white"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("표시할 데이터가 없습니다.")

    st.subheader("📊 지역별 장기 보호 동물 비율")
    if not filtered.empty:
        long_term_chart = filtered.groupby("region")["long_term"].sum().reset_index()
        fig2 = px.pie(
            long_term_chart,
            values="long_term",
            names="region",
            title="",
            template="plotly_white"
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("표시할 데이터가 없습니다.")

# ===========================
# TAB 3: 보호소 상세 정보
# ===========================
elif active_tab == "📋 보호소 상세 현황":
    if st.session_state.selected_shelter:
        selected = st.session_state.selected_shelter
        st.subheader(f"🏠 {selected} 상세 정보")

        animals = animal_data[animal_data["shelter_name"] == selected]

        if len(animals) > 0:
            for _, animal in animals.iterrows():
                cols = st.columns([1, 2])
                cols[0].image(animal["image_url"], width=180)
                cols[1].markdown(f"""
                    **이름:** {animal["animal_name"]}  
                    **품종:** {animal["species"]}  
                    **나이:** {animal["age"]}
                """)
                st.markdown("---")
        else:
            st.warning("등록된 동물 정보가 없습니다.")
    else:
        st.info("지도의 보호소를 클릭하면 상세 정보를 볼 수 있습니다.")

    # 보호소 전체 데이터 다운로드
    st.download_button(
        label="📥 CSV 다운로드",
        data=filtered.to_csv(index=False).encode('utf-8-sig'),
        file_name="shelter_data.csv",
        mime="text/csv"
    )
