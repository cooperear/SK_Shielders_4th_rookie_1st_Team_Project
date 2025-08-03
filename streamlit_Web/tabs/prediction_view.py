import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# lstm_improved.py가 있는 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lstm_model'))
from lstm_improved import AnimalShelterPredictorImproved as AnimalShelterPredictor

# --- 캐싱 적용 ---
@st.cache_resource
def load_predictor():
    """ 
    앱 실행 시 단 한 번만 모델과 데이터를 로드하고 전처리합니다.
    결과(predictor 객체)는 메모리에 저장되어 즉시 재사용됩니다.
    """
    model_path = 'lstm_model/lstm_model_animal_shelter_improved.h5'
    data_path = 'data/data20230731_20250730.csv'
    
    predictor = AnimalShelterPredictor(model_save_path=model_path)
    
    # 데이터 전처리 및 모델 로드를 한 번에 수행
    if not predictor.preprocess_data(file_path=data_path):
        st.error("캐싱 중 데이터 전처리에 실패했습니다.")
        return None
    if not predictor.load_model_for_prediction():
        st.error("캐싱 중 모델 로드에 실패했습니다.")
        return None
        
    return predictor

def show():
    st.header("🔮 미래 유기동물 발생 예측")
    st.write("기준 날짜를 선택하면, 해당 날짜로부터 다음 30일 동안 표시할 범위만큼 유기동물 발생 가능성이 높은 지역을 예측합니다.")

    # 캐시된 predictor 객체 로드
    predictor = load_predictor()

    if predictor is None:
        st.error("예측 모델을 불러오는 데 실패했습니다. 관리자에게 문의하세요.")
        return

    # 날짜 입력
    predict_date = st.date_input(
        "예측 기준일",
        datetime.now(),
        key="predict_date"
    )

    # 결과 개수 선택 UI (드롭다운 메뉴로 변경)
    display_option = st.selectbox(
        "표시할 결과 범위",
        options=['상위 5개', '상위 10개', '상위 20개', '전체 보기'],
        index=0, # 기본값 '상위 5개'
        help="표시할 예측 결과의 범위를 선택하세요."
    )

    # 예측 버튼
    if st.button("예측 실행", key="predict_button"):
        start_date_str = predict_date.strftime('%Y-%m-%d')
        end_date = predict_date + timedelta(days=30)
        end_date_str = end_date.strftime('%Y-%m-%d')

        with st.spinner("LSTM 모델을 이용하여 예측 중입니다..."):
            try:
                predictions = predictor.predict_all_orgnms_next_month(
                    start_date_str=start_date_str, 
                    end_date_str=end_date_str
                )

                if predictions:
                    # 선택 옵션에 따라 보여줄 결과 개수 결정
                    if display_option == '상위 5개':
                        top_n = 5
                    elif display_option == '상위 10개':
                        top_n = 10
                    elif display_option == '상위 20개':
                        top_n = 20
                    else: # '전체 보기'
                        top_n = len(predictions)
                    
                    display_text = f"{display_option} ({top_n}개)" if display_option == '전체 보기' else display_option

                    st.success(f"**{start_date_str} ~ {end_date_str}** 기간의 유기동물 발생 예측 {display_text} 결과입니다.")
                    
                    # 사용자가 선택한 만큼 결과 선택하여 표시
                    pred_df = pd.DataFrame(predictions[:top_n])
                    pred_df.rename(columns={
                        'org_name': '지역',
                        'predicted_probability_percent': '평균 발생 확률 (%)'
                    }, inplace=True)
                    pred_df['순위'] = range(1, len(pred_df) + 1)
                    pred_df = pred_df[['순위', '지역', '평균 발생 확률 (%)']]
                    
                    st.table(pred_df.style.format({'평균 발생 확률 (%)': '{:.2f}%'}))
                else:
                    st.warning("예측 결과를 생성하지 못했습니다. 입력 데이터나 모델을 확인해주세요.")

            except Exception as e:
                st.error(f"예측 중 오류가 발생했습니다: {e}")