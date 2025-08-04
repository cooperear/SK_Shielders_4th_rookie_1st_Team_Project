import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# -----------------------------
# lstm_improved.py 경로 설정
# -----------------------------
# 현재 prediction_view.py 파일 기준
current_dir = os.path.dirname(os.path.abspath(__file__))      # tabs/
streamlit_web_dir = os.path.dirname(current_dir)              # streamlit_Web/
lstm_model_path = os.path.join(streamlit_web_dir, 'lstm_model')

if lstm_model_path not in sys.path:
    sys.path.append(lstm_model_path)

from lstm_improved import AnimalShelterPredictorImproved as AnimalShelterPredictor

# -----------------------------
# 캐싱 적용
# -----------------------------
def load_predictor():
    """ 
    앱 실행 시 단 한 번만 모델과 데이터를 로드하고 전처리합니다.
    predictor 객체를 메모리에 저장해 즉시 재사용합니다.
    """
    # 절대 경로로 지정
    model_path = os.path.join(lstm_model_path, 'lstm_model_animal_shelter_improved.h5')
    data_path = os.path.join(streamlit_web_dir, 'data', 'data20230731_20250730.csv')

    predictor = AnimalShelterPredictor(model_save_path=model_path)

    # 데이터 전처리 및 모델 로드
    if not predictor.preprocess_data(file_path=data_path):
        st.error("캐싱 중 데이터 전처리에 실패했습니다.")
        return None
    if not predictor.load_model_for_prediction():
        st.error("캐싱 중 모델 로드에 실패했습니다.")
        return None
        
    return predictor

# -----------------------------
# 화면 표시
# -----------------------------
def show():
    st.header("🔮 미래 유기동물 발생 예측")
    st.write("기준 날짜를 선택하면, 해당 날짜로부터 선택한 예측 기간 동안 표시할 범위만큼 유기동물 발생 가능성이 높은 지역을 예측합니다.")

    # predictor 로드
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

    # 결과 개수 선택
    display_option = st.selectbox(
        "표시할 결과 범위",
        options=['상위 5개', '상위 10개', '상위 20개', '전체 보기'],
        index=0,
        help="표시할 예측 결과의 범위를 선택하세요."
    )

    # 예측 기간 선택
    period_option = st.selectbox(
        "예측 기간 선택",
        options=['7일', '14일', '30일'],
        index=2,
        help="예측할 기간을 선택하세요. 기간이 짧을수록 더 빨리 결과가 나옵니다."
    )

    # 예측 실행
    if st.button("예측 실행", key="predict_button"):
        start_date_str = predict_date.strftime('%Y-%m-%d')
        days = {'7일': 7, '14일': 14, '30일': 30}[period_option]
        end_date_str = (predict_date + timedelta(days=days)).strftime('%Y-%m-%d')

        progress = st.progress(0)
        status_text = st.empty()
        status_text.write("LSTM 모델을 이용하여 예측 중입니다...")

        try:
            predictions = predictor.predict_all_orgnms_next_month(
                start_date_str=start_date_str,
                end_date_str=end_date_str,
                progress_callback=lambda p: progress.progress(p)
            )
            progress.empty()
            status_text.empty()

            if predictions:
                # top_n 설정
                top_n = {
                    '상위 5개': 5,
                    '상위 10개': 10,
                    '상위 20개': 20,
                    '전체 보기': len(predictions)
                }[display_option]

                display_text = f"{display_option} ({top_n}개)" if display_option == '전체 보기' else display_option
                st.success(f"**{start_date_str} ~ {end_date_str}** 기간의 유기동물 발생 예측 {display_text} 결과입니다.")

                # 결과 데이터프레임 구성
                pred_df = pd.DataFrame(predictions[:top_n])
                pred_df.rename(columns={
                    'org_name': '지역',
                    'predicted_probability_percent': '평균 발생 확률 (%)'
                }, inplace=True)
                pred_df['순위'] = range(1, len(pred_df) + 1)

                # 예측 이유 추가
                pred_df['예측 이유'] = ["최근 발생 건수와 주말 효과 등 시계열 패턴 기반" for _ in range(len(pred_df))]

                # 컬럼 정렬
                pred_df = pred_df[['순위', '지역', '평균 발생 확률 (%)', '예측 이유']]

                st.table(pred_df.style.format({'평균 발생 확률 (%)': '{:.2f}%'}))

                import plotly.express as px
                plot_df = pred_df.head(top_n)  # top_n만 시각화
                fig = px.bar(
                    plot_df.sort_values("평균 발생 확률 (%)", ascending=True),
                    x="평균 발생 확률 (%)",
                    y="지역",
                    orientation='h',
                    text="평균 발생 확률 (%)",
                    color_discrete_sequence=["#f28b82"],
                    height=600 if top_n <= 20 else 30 * top_n
                )
                fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                fig.update_layout(title="유기동물 발생 예측 확률 (상위 지역)", margin=dict(l=120, r=30, t=60, b=30))

                st.plotly_chart(fig, use_container_width=True)

            else:
                st.warning("예측 결과를 생성하지 못했습니다. 입력 데이터나 모델을 확인해주세요.")

        except Exception as e:
            progress.empty()
            status_text.empty()
            st.error(f"예측 중 오류가 발생했습니다: {e}")
