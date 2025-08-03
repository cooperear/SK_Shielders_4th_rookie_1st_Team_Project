# ==============================================================================
# detail_view.py - 보호소 상세 현황 탭
# ==============================================================================
# 이 파일은 사용자가 지도에서 특정 보호소를 선택했을 때, 해당 보호소의
# 상세 정보와 현재 보호 중인 동물들의 목록을 보여주는 화면을 구성합니다.
#
# [주요 기능]
# 1. **선택된 보호소 확인:** `st.session_state`에 저장된 `selected_shelter` 값을
#    가져와 현재 어떤 보호소가 선택되었는지 확인합니다.
# 2. **동물 상세 정보 조회:** `data_manager.get_animal_details` 함수를 호출하여
#    선택된 보호소에 소속된 동물들의 데이터를 DB에서 가져옵니다.
# 3. **동물 목록 표시:** 조회된 동물 데이터를 반복하면서 각 동물의 사진, 이름,
#    나이, 특징 등의 정보를 `st.columns`를 활용하여 깔끔하게 표시합니다.
# 4. **찜하기 기능:** 각 동물 정보 옆에 '찜하기/찜 취소' 버튼을 추가합니다.
#    - 사용자가 버튼을 누르면 `st.session_state.favorites` 목록에 해당 동물의
#      고유 ID(`desertion_no`)를 추가하거나 제거합니다.
#    - 상태 변경 후 `st.rerun()`을 호출하여 화면을 즉시 새로고침하고 변경사항을
#      반영합니다.
# 5. **데이터 다운로드:** 현재 필터링된 조건에 맞는 보호소 목록 전체를
#    CSV 파일로 다운로드할 수 있는 버튼을 제공합니다.
# ==============================================================================

import streamlit as st
from data_manager import get_animal_details
import pandas as pd

def show(filtered_shelters):
    """
    '보호소 상세 현황' 탭의 전체 UI를 그리고 로직을 처리하는 메인 함수입니다.

    Args:
        filtered_shelters (pd.DataFrame): app.py에서 필터링된 보호소 데이터.
    """
    st.subheader("📋 보호소 상세 현황")

    selected_shelter_name = st.session_state.get("selected_shelter", None)

    if selected_shelter_name:
        st.markdown(f"### 🏠 {selected_shelter_name}")

        animal_details = get_animal_details(selected_shelter_name)

        if not animal_details.empty:
            # 전화번호는 보통 보호소 전체에 동일하므로, 첫 번째 동물의 정보에서 가져옵니다.
            shelter_tel = animal_details.iloc[0].get('care_tel', '전화번호 정보 없음')
            st.markdown(f"**📞 연락처:** {shelter_tel}")
            st.markdown("---")

            for _, animal in animal_details.iterrows():
                cols = st.columns([1, 3])
                with cols[0]:
                    display_name = (
                        animal.get('kind_name') if pd.notna(animal.get('kind_name')) else animal.get('notice_no', '이름 없음')
                    )
                    if "image_url" in animal and pd.notna(animal["image_url"]):
                        st.image(animal["image_url"], width=150, caption=display_name)
                    else:
                        st.image("https://via.placeholder.com/150?text=사진+없음", width=150, caption=display_name)
                with cols[1]:
                    if 'desertion_no' in animal and pd.notna(animal['desertion_no']):
                        is_favorited = animal['desertion_no'] in st.session_state.favorites
                        button_text = "❤️ 찜 취소" if is_favorited else "🤍 찜하기"
                        if st.button(button_text, key=f"fav_add_{animal['desertion_no']}"):
                            if is_favorited:
                                st.session_state.favorites.remove(animal['desertion_no'])
                            else:
                                st.session_state.favorites.append(animal['desertion_no'])
                            st.rerun()
                    else:
                        st.info("찜하기 기능을 사용할 수 없습니다 (유기번호 없음).")

                    age_info = animal.get('age', '정보 없음')
                    weight_info = animal.get('weight', None)
                    if pd.notna(weight_info) and weight_info != '정보 없음':
                        st.markdown(f"**{display_name}** ({age_info}, {weight_info})")
                    else:
                        st.markdown(f"**{display_name}** ({age_info})")

                    sex_info = animal.get('sex', None)
                    if sex_info == 'F':
                        sex_display = "♀️ 성별: 암컷"
                    elif sex_info == 'M':
                        sex_display = "♂️ 성별: 수컷"
                    else:
                        sex_display = "성별: 정보 없음"
                    st.markdown(f"**{sex_display}**")

                    st.markdown(f"**🐾 정보:** {animal.get('special_mark', '정보 없음')}")

                    happen_place = animal.get('happen_place', None)
                    if pd.notna(happen_place) and happen_place != '정보 없음':
                        st.markdown(f"**📍 발견 장소:** {happen_place}")
                
                st.markdown("---")
        else:
            st.warning("이 보호소에 등록된 동물 정보가 없습니다.")

    else:
        st.info("지도에서 보호소 마커를 클릭하여 상세 정보를 확인하세요.")

    st.markdown("---")
    if selected_shelter_name and not animal_details.empty:
        st.download_button(
            label="📥 선택된 보호소 동물 목록 다운로드 (CSV)",
            data=animal_details.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"{selected_shelter_name}_animals.csv",
            mime="text/csv"
        )