import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from datetime import datetime, timedelta
import os

class AnimalShelterPredictor:
    def __init__(self, model_save_path='lstm_animal_shelter_model.h5', sequence_length=7):
        """
        유기 동물 발생 예측 모델 초기화.

        Args:
            model_save_path (str): 학습된 모델을 저장하거나 불러올 경로.
            sequence_length (int): LSTM 모델에 입력할 시퀀스 길이 (몇 일치 과거 데이터를 볼 것인지).
        """
        self.model_save_path = model_save_path
        self.sequence_length = sequence_length
        self.model = None
        self.label_encoder = LabelEncoder()
        self.scaler_org = MinMaxScaler()
        self.merged_df = None # 전처리된 데이터 저장
        self.all_org_encoded = None # 모든 인코딩된 orgNm 값 저장

    def _load_data(self, file_path):
        """
        JSON 파일에서 데이터를 로드합니다.
        """
        try:
            df = pd.read_json(file_path)
            return df
        except FileNotFoundError:
            print(f"Error: {file_path} 파일을 찾을 수 없습니다. 파일 경로를 확인해주세요.")
            return None

    def preprocess_data(self, file_path='data.json'):
        """
        데이터를 로드하고 LSTM 모델 학습에 적합한 형태로 전처리합니다.
        'is_happened' (발생 여부) 및 'orgNm_scaled' (스케일링된 지역명) 피처를 생성합니다.
        """
        df = self._load_data(file_path)
        if df is None:
            return False

        df['happenDt'] = pd.to_datetime(df['happenDt'], format='%Y%m%d')

        # 'orgNm'을 숫자로 인코딩
        df['orgNm_encoded'] = self.label_encoder.fit_transform(df['orgNm'])
        self.all_org_encoded = df['orgNm_encoded'].unique()

        # 모든 가능한 날짜-orgNm 조합 생성
        min_date = df['happenDt'].min()
        max_date = df['happenDt'].max()
        date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        all_combinations = pd.MultiIndex.from_product([date_range, self.all_org_encoded], 
                                                      names=['happenDt', 'orgNm_encoded']).to_frame(index=False)

        # 기존 발생 데이터와 병합하여 발생 여부(is_happened) 컬럼 생성
        df_happen = df[['happenDt', 'orgNm_encoded']].copy()
        df_happen['is_happened'] = 1

        self.merged_df = pd.merge(all_combinations, df_happen, on=['happenDt', 'orgNm_encoded'], how='left')
        self.merged_df['is_happened'].fillna(0, inplace=True) # 발생하지 않은 경우 0으로 채움
        self.merged_df = self.merged_df.sort_values(by=['happenDt', 'orgNm_encoded']).reset_index(drop=True)

        # orgNm_encoded를 스케일링
        self.merged_df['orgNm_scaled'] = self.scaler_org.fit_transform(self.merged_df['orgNm_encoded'].values.reshape(-1, 1))

        print("데이터 전처리 완료. 병합된 데이터 미리보기:")
        print(self.merged_df.head())
        print(f"총 데이터 포인트: {len(self.merged_df)}")
        return True

    def _create_sequences(self):
        """
        전처리된 데이터에서 LSTM 모델 학습을 위한 시퀀스 데이터를 생성합니다.
        """
        X, y = [], []
        for org_id in self.merged_df['orgNm_encoded'].unique():
            org_data = self.merged_df[self.merged_df['orgNm_encoded'] == org_id].sort_values(by='happenDt')
            if len(org_data) < self.sequence_length + 1:
                continue
            
            # 'is_happened'와 'orgNm_scaled'를 피처로 사용
            features = org_data[['is_happened', 'orgNm_scaled']].values
            
            for i in range(len(features) - self.sequence_length):
                X.append(features[i:(i + self.sequence_length)])
                y.append(features[i + self.sequence_length, 0])

        return np.array(X), np.array(y)

    def train_or_load_model(self):
        """
        모델을 학습하거나 저장된 모델을 불러옵니다.
        """
        X, y = self._create_sequences()
        
        if X.size == 0:
            print("시퀀스 데이터가 충분하지 않아 모델 학습/로드 불가.")
            self.model = None
            return

        # 학습/검증 데이터 분리
        # y의 0과 1 비율을 유지하기 위해 stratify 사용
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        # 모델 파일이 이미 존재하는지 확인
        if os.path.exists(self.model_save_path):
            print(f"\n기존 모델 '{self.model_save_path}'을(를) 불러옵니다.")
            self.model = load_model(self.model_save_path)
            # 모델 불러온 후에는 컴파일이 필요하지 않지만, metrics를 확인하려면 compile 호출 가능
            self.model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
            loss, accuracy = self.model.evaluate(X_test, y_test, verbose=0)
            print(f"불러온 모델의 테스트 세트 손실: {loss:.4f}, 정확도: {accuracy:.4f}")
        else:
            print("\n새로운 LSTM 모델을 학습합니다.")
            self.model = Sequential([
                LSTM(50, activation='relu', input_shape=(X_train.shape[1], X_train.shape[2]), return_sequences=True),
                Dropout(0.3),
                LSTM(25, activation='relu'),
                Dropout(0.3),
                Dense(1, activation='sigmoid') # 이진 분류 (발생/미발생)
            ])

            self.model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

            # 얼리 스토핑 설정
            early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

            print("모델 학습 시작...")
            history = self.model.fit(
                X_train, y_train,
                epochs=50,
                batch_size=32,
                validation_split=0.1, # 학습 데이터 중 일부를 검증용으로 사용
                callbacks=[early_stopping],
                verbose=1
            )
            print("모델 학습 완료.")

            # 모델 평가
            loss, accuracy = self.model.evaluate(X_test, y_test, verbose=0)
            print(f"\n테스트 세트 손실: {loss:.4f}, 정확도: {accuracy:.4f}")

            # 모델 저장
            self.model.save(self.model_save_path)
            print(f"학습된 모델이 '{self.model_save_path}'에 저장되었습니다.")

    def predict_top_n_orgnms_next_week(self, start_date_str="2025-08-01", end_date_str="2025-08-07", top_n=5):
        """
        다음 주 전체 기간 동안 유기 동물 발생 가능성이 가장 높은 상위 N개 지역을 예측합니다.
        
        Args:
            start_date_str (str): 예측 시작 날짜 (YYYY-MM-DD 형식).
            end_date_str (str): 예측 종료 날짜 (YYYY-MM-DD 형식).
            top_n (int): 발생 가능성이 가장 높은 지역을 선정할 개수.
        """
        if self.model is None:
            print("모델이 로드되거나 학습되지 않았습니다. 먼저 'train_or_load_model'을 실행하세요.")
            return

        prediction_start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        prediction_end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        org_nm_likelihoods = {} # {orgNm: 총 예측 확률}

        # 각 orgNm에 대해 다음 주 발생 여부 예측
        for org_id in self.all_org_encoded:
            org_name = self.label_encoder.inverse_transform([org_id])[0]
            
            # 해당 orgNm의 가장 최근 SEQUENCE_LENGTH 일치 데이터 가져오기
            recent_org_data = self.merged_df[self.merged_df['orgNm_encoded'] == org_id].sort_values(by='happenDt').tail(self.sequence_length)
            
            # 시퀀스 길이가 부족하면 예측에서 제외
            if len(recent_org_data) < self.sequence_length:
                continue

            # is_happened와 orgNm_scaled를 피처로 사용
            last_sequence_features = recent_org_data[['is_happened', 'orgNm_scaled']].values
            
            current_sequence = last_sequence_features
            total_probability_for_org = 0.0
            
            # 다음 주 각 날짜에 대해 예측
            for day_offset in range((prediction_end_date - prediction_start_date).days + 1):
                # predict_date = prediction_start_date + timedelta(days=day_offset) # 이 변수는 여기서는 직접 사용하지 않음
                
                # 예측 입력 형태 맞추기 (batch_size, sequence_length, features)
                input_sequence = current_sequence.reshape(1, self.sequence_length, 2) # 2는 피처 수 (is_happened, orgNm_scaled)
                
                # 예측 수행 (확률 값 얻기)
                prediction_prob = self.model.predict(input_sequence, verbose=0)[0][0]
                total_probability_for_org += prediction_prob # 예측 확률 누적

                # 예측된 결과를 다음 시퀀스에 포함 (실제 발생 여부 대신 예측된 확률 기반의 0 또는 1 사용)
                is_happened_predicted = 1 if prediction_prob > 0.5 else 0
                scaled_org_id_val = self.scaler_org.transform(np.array([[org_id]]))[0,0]
                next_step_features = np.array([[is_happened_predicted, scaled_org_id_val]])
                
                # 시퀀스 업데이트: 가장 오래된 데이터 제거, 새로운 예측 결과 추가
                current_sequence = np.vstack([current_sequence[1:], next_step_features])

            org_nm_likelihoods[org_name] = total_probability_for_org

        # 예측 확률을 기준으로 지역 정렬
        sorted_org_nms = sorted(org_nm_likelihoods.items(), key=lambda item: item[1], reverse=True)

        print(f"\n--- 다음 주 ({prediction_start_date.strftime('%Y-%m-%d')} ~ {prediction_end_date.strftime('%Y-%m-%d')}) 유기 동물 발생 가능성이 높은 상위 {top_n}개 지역 ---")
        if not sorted_org_nms:
            print("예측된 유기 동물 발생 지역이 없습니다.")
        else:
            for i, (org, likelihood) in enumerate(sorted_org_nms[:top_n]):
                print(f"{i+1}. {org} (총 예측 확률: {((likelihood/7)*100):.4f}%)")
                

        print("\n**참고:** 이 예측은 제공된 데이터의 패턴에 기반한 것이며, 실제 발생과는 차이가 있을 수 있습니다.")
        print("데이터의 양, 특성, 그리고 외부 요인이 고려되지 않았으므로, 예측의 정확도는 제한적일 수 있습니다.")





# --- 사용 예시 ---
if __name__ == "__main__":
    predictor = AnimalShelterPredictor(model_save_path='lstm_animal_shelter_model.h5', sequence_length=7)
    
    # 1. 데이터 전처리


    if predictor.preprocess_data(file_path='data20250531_20250730.json'):
        # 2. 모델 학습 또는 로드
        predictor.train_or_load_model()
        
        # 3. 다음 주 가장 발생할 수 있는 지역 5곳 예상 (일주일 단위)
        # 현재 날짜 기준 다음주 예측 (2025년 8월 1일 ~ 8월 7일)
        predictor.predict_top_n_orgnms_next_week(start_date_str="2025-08-01", end_date_str="2025-08-07", top_n=5)


    else:
        print("데이터 전처리 실패로 예측을 수행할 수 없습니다.")
