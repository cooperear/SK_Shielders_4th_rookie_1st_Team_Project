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
import json 

class AnimalShelterPredictor:
    def __init__(self, model_save_path='lstm_animal_shelter_model.h5', sequence_length=7):
        self.model_save_path = model_save_path
        self.sequence_length = sequence_length
        self.model = None
        self.label_encoder = LabelEncoder()
        self.scaler_org = MinMaxScaler()
        self.merged_df = None 
        self.all_org_encoded = None 

    def _load_data(self, file_path):
        try:
            df = pd.read_json(file_path)
            return df
        except FileNotFoundError:
            print(f"Error: {file_path} 파일을 찾을 수 없습니다. 파일 경로를 확인해주세요.")
            return None

    def preprocess_data(self, file_path='data.json'):
        df = self._load_data(file_path)
        if df is None:
            return False

        df['happenDt'] = pd.to_datetime(df['happenDt'], format='%Y%m%d')

        df['orgNm_encoded'] = self.label_encoder.fit_transform(df['orgNm'])
        self.all_org_encoded = df['orgNm_encoded'].unique()

        min_date = df['happenDt'].min()
        max_date = df['happenDt'].max()
        date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        all_combinations = pd.MultiIndex.from_product([date_range, self.all_org_encoded], 
                                                        names=['happenDt', 'orgNm_encoded']).to_frame(index=False)

        df_happen = df[['happenDt', 'orgNm_encoded']].copy()
        df_happen['is_happened'] = 1

        self.merged_df = pd.merge(all_combinations, df_happen, on=['happenDt', 'orgNm_encoded'], how='left')
        self.merged_df['is_happened'].fillna(0, inplace=True) 
        self.merged_df = self.merged_df.sort_values(by=['happenDt', 'orgNm_encoded']).reset_index(drop=True)

        self.merged_df['orgNm_scaled'] = self.scaler_org.fit_transform(self.merged_df['orgNm_encoded'].values.reshape(-1, 1))

        print("데이터 전처리 완료. 병합된 데이터 미리보기:")
        print(self.merged_df.head())
        print(f"총 데이터 포인트: {len(self.merged_df)}")
        return True

    def _create_sequences(self):
        X, y = [], []
        for org_id in self.merged_df['orgNm_encoded'].unique():
            org_data = self.merged_df[self.merged_df['orgNm_encoded'] == org_id].sort_values(by='happenDt')
            if len(org_data) < self.sequence_length + 1:
                continue
            
            features = org_data[['is_happened', 'orgNm_scaled']].values
            
            for i in range(len(features) - self.sequence_length):
                X.append(features[i:(i + self.sequence_length)])
                y.append(features[i + self.sequence_length, 0])

        if not X:
            print("경고: 생성된 시퀀스 데이터가 없습니다. 데이터 전처리 또는 sequence_length 설정을 확인하세요.")
        return np.array(X), np.array(y)

    def train_or_load_model(self):
        X, y = self._create_sequences()
        
        if X.size == 0 or y.size == 0: 
            print("시퀀스 데이터가 충분하지 않아 모델 학습/로드 불가.")
            self.model = None
            return

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        if os.path.exists(self.model_save_path):
            print(f"\n기존 모델 '{self.model_save_path}'을(를) 불러옵니다.")
            self.model = load_model(self.model_save_path)
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
                Dense(1, activation='sigmoid') 
            ])

            self.model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

            early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

            print("모델 학습 시작...")
            history = self.model.fit(
                X_train, y_train,
                epochs=50,
                batch_size=32,
                validation_split=0.1, 
                callbacks=[early_stopping],
                verbose=1
            )
            print("모델 학습 완료.")

            loss, accuracy = self.model.evaluate(X_test, y_test, verbose=0)
            print(f"\n테스트 세트 손실: {loss:.4f}, 정확도: {accuracy:.4f}")

            self.model.save(self.model_save_path)
            print(f"학습된 모델이 '{self.model_save_path}'에 저장되었습니다.")

    def predict_top_n_orgnms_next_week(self, start_date_str="2025-08-01", end_date_str="2025-08-07", top_n=5):
        if self.model is None:
            print("모델이 로드되거나 학습되지 않았습니다. 먼저 'train_or_load_model'을 실행하세요.")
            return

        if self.merged_df is None or self.all_org_encoded is None:
            print("데이터 전처리가 완료되지 않았습니다. 먼저 'preprocess_data'를 실행하세요.")
            return

        prediction_start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        prediction_end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        org_nm_likelihoods = {} 
        
        for org_id in self.all_org_encoded:
            org_name = self.label_encoder.inverse_transform([org_id])[0]
            
            recent_org_data = self.merged_df[self.merged_df['orgNm_encoded'] == org_id].sort_values(by='happenDt').tail(self.sequence_length)
            
            if len(recent_org_data) < self.sequence_length:
                continue

            last_sequence_features = recent_org_data[['is_happened', 'orgNm_scaled']].values
            
            current_sequence = last_sequence_features
            total_probability_for_org = 0.0
            num_prediction_days = (prediction_end_date - prediction_start_date).days + 1
            
            for day_offset in range(num_prediction_days):
                input_sequence = current_sequence.reshape(1, self.sequence_length, 2) 
                
                prediction_prob = self.model.predict(input_sequence, verbose=0)[0][0]
                total_probability_for_org += prediction_prob 

                is_happened_predicted = 1 if prediction_prob > 0.5 else 0
                scaled_org_id_val = self.scaler_org.transform(np.array([[org_id]]))[0,0]
                next_step_features = np.array([[is_happened_predicted, scaled_org_id_val]])
                
                current_sequence = np.vstack([current_sequence[1:], next_step_features])

            org_nm_likelihoods[org_name] = total_probability_for_org

        sorted_org_nms = sorted(org_nm_likelihoods.items(), key=lambda item: item[1], reverse=True)

        print(f"\n--- 다음 주 ({prediction_start_date.strftime('%Y-%m-%d')} ~ {prediction_end_date.strftime('%Y-%m-%d')}) 유기 동물 발생 가능성이 높은 상위 {top_n}개 지역 ---")
        
        predictions_to_save = []

        if not sorted_org_nms:
            print("예측된 유기 동물 발생 지역이 없습니다.")
        else:
            for i, (org, likelihood) in enumerate(sorted_org_nms[:top_n]):
                average_probability_percent = round((likelihood / num_prediction_days) * 100, 4) 
                
                print(f"{i+1}. {org} (총 예측 확률: {average_probability_percent:.4f}%)")
                
                predictions_to_save.append({
                    "rank": i + 1,
                    "org_name": org,
                    # numpy.float32를 Python float으로 명시적 변환
                    "predicted_probability_percent": float(average_probability_percent) 
                })
                
        output_filename = "predict_1_week.json"
        if predictions_to_save: 
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    # default=float을 추가하여 float32를 float으로 변환하도록 json.dump에 지시
                    json.dump(predictions_to_save, f, ensure_ascii=False, indent=4)
                print(f"\n예측 결과가 '{output_filename}' 파일에 성공적으로 저장되었습니다.")
            except Exception as e:
                print(f"\n예측 결과를 파일에 저장하는 중 오류가 발생했습니다: {e}")
        else:
            print(f"\n저장할 예측 결과가 없습니다. '{output_filename}' 파일이 생성되지 않았습니다.")

        print("\n**참고:** 이 예측은 제공된 데이터의 패턴에 기반한 것이며, 실제 발생과는 차이가 있을 수 있습니다.")
        print("데이터의 양, 특성, 그리고 외부 요인이 고려되지 않았으므로, 예측의 정확도는 제한적일 수 있습니다.")
        

from datetime import datetime
path_model =f'lstm_animal_shelter_{datetime.now().strftime("%Y%m%d_%H%M%S")}_model.h5'

# --- 사용 예시 ---
if __name__ == "__main__":
    predictor = AnimalShelterPredictor(model_save_path=path_model, sequence_length=7) # 지금시간을 기준으로 h5 학습데이터 파일을 만듦
    
    # 1. 데이터 전처리


    if predictor.preprocess_data(file_path='data20250531_20250730.json'):
        # 2. 모델 학습 또는 로드
        predictor.train_or_load_model()
        
        # 3. 다음 주 가장 발생할 수 있는 지역 5곳 예상 (일주일 단위)
        # 현재 날짜 기준 다음주 예측 (2025년 8월 1일 ~ 8월 7일)
        predictor.predict_top_n_orgnms_next_week(start_date_str="2025-08-01", end_date_str="2025-08-07", top_n=5)


    else:
        print("데이터 전처리 실패로 예측을 수행할 수 없습니다.")
