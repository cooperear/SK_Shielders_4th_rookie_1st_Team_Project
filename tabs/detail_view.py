import streamlit as st
from data_manager import get_animal_details

def show(filtered_data):
    st.subheader("📋 보호소 상세 현황")

    # 세션 상태에서 선택된 보호소 가져오기
    selected_shelter = st.session_state.get("selected_shelter", None)

    if selected_shelter:
        st.markdown(f"### 🏠 {selected_shelter}")

        # 선택된 보호소의 동물 정보 가져오기
        animal_details = get_animal_details(selected_shelter)

        if not animal_details.empty:
            for _, animal in animal_details.iterrows():
                cols = st.columns([1, 3])
                with cols[0]:
                    st.image(animal["image_url"], width=150, caption=animal['animal_name'])
                with cols[1]:
                    # 찜하기 버튼 로직
                    is_favorited = animal['animal_name'] in st.session_state.favorites
                    button_text = "❤️ 찜 취소" if is_favorited else "🤍 찜하기"
                    if st.button(button_text, key=f"fav_add_{animal['animal_name']}"):
                        if is_favorited:
                            st.session_state.favorites.remove(animal['animal_name'])
                        else:
                            st.session_state.favorites.append(animal['animal_name'])
                        st.rerun()

                    st.markdown(f"**{animal['animal_name']}** ({animal['species']}, {animal['age']})")
                    
                    # 성격 및 스토리 표시
                    st.markdown(f"**💖 성격:** {animal.get('personality', '정보 없음')}")
                    st.markdown(f"**🐾 발견 이야기:** {animal.get('story', '정보 없음')}")
                st.markdown("---")
        else:
            st.warning("이 보호소에 등록된 동물 정보가 없습니다.")

    else:
        st.info("지도에서 보호소 마커를 클릭하여 상세 정보를 확인하세요.")

    # --- 데이터 다운로드 ---
    st.markdown("---")
    st.download_button(
        label="📥 현재 필터링된 보호소 목록 다운로드 (CSV)",
        data=filtered_data.to_csv(index=False).encode('utf-8-sig'),
        file_name="filtered_shelter_data.csv",
        mime="text/csv"
    )
