import streamlit as st
import folium
from streamlit_folium import st_folium

def show(filtered_data):
    st.subheader("📍 보호소 지도")

    if filtered_data.empty:
        st.warning("표시할 데이터가 없습니다.")
        return

    # 지도 초기 위치 설정
    map_center = [filtered_data['lat'].mean(), filtered_data['lon'].mean()]
    m = folium.Map(location=map_center, zoom_start=7)

    for _, row in filtered_data.iterrows():
        popup_html = f"""
        <b>{row['shelter_name']}</b><br>
        <img src='{row['image_url']}' width='150'><br>
        지역: {row['region']}<br>
        주요 품종: {row['species']}<br>
        보호 중: {row['count']} 마리
        """
        folium.Marker(
            [row['lat'], row['lon']],
            popup=popup_html,
            tooltip=row['shelter_name'],
            icon=folium.Icon(color="blue", icon="paw", prefix='fa')
        ).add_to(m)

    # 지도 표시 및 이벤트 처리
    map_event = st_folium(m, width='100%', height=500)

    # 마커 클릭 시 세션에 보호소 이름 저장 및 탭 전환 신호 보내기
    if map_event and map_event.get("last_object_clicked_tooltip"):
        clicked_shelter = map_event["last_object_clicked_tooltip"]
        # 불필요한 재실행을 막기 위해, 상태가 변경될 때만 업데이트
        if st.session_state.get("selected_shelter") != clicked_shelter:
            st.session_state.selected_shelter = clicked_shelter
            st.session_state.active_tab = "📋 보호소 상세 현황" # 탭 전환 신호
            st.rerun() # app.py가 변경된 상태를 즉시 반영하도록 재실행
