import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from datetime import datetime
import os

class AnimalShelterPredictorImproved:
    def __init__(self, model_save_path='lstm_model_animal_shelter_improved.h5', sequence_length=7):
        self.model_save_path = model_save_path
        self.sequence_length = sequence_length
        self.model = None
        self.label_encoder = LabelEncoder()
        self.scaler = MinMaxScaler()
        self.merged_df = None
        self.all_org_encoded = None

    def _load_data(self, file_path):
        try:
            return pd.read_csv(file_path, encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding='cp949', low_memory=False)

    def preprocess_data(self, file_path='data.csv'):
        df = self._load_data(file_path)
        if df is None:
            return False

        df['happenDt'] = pd.to_datetime(df['happenDt'], format='%Y%m%d')
        df['orgNm_encoded'] = self.label_encoder.fit_transform(df['orgNm'])
        self.all_org_encoded = df['orgNm_encoded'].unique()

        # 날짜-보호소 조합 생성
        min_date = df['happenDt'].min()
        max_date = df['happenDt'].max()
        date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        all_combinations = pd.MultiIndex.from_product(
            [date_range, self.all_org_encoded], names=['happenDt', 'orgNm_encoded']
        ).to_frame(index=False)

        df_happen = df[['happenDt', 'orgNm_encoded']].copy()
        df_happen['is_happened'] = 1

        merged = pd.merge(all_combinations, df_happen, on=['happenDt', 'orgNm_encoded'], how='left')
        merged['is_happened'] = merged['is_happened'].fillna(0)

        # orgNm_encoded_original 컬럼 추가 (스케일링 전 값 저장)
        merged['orgNm_encoded_original'] = merged['orgNm_encoded']

        # 파생변수 추가
        merged['weekday'] = merged['happenDt'].dt.weekday
        merged['is_weekend'] = merged['weekday'].apply(lambda x: 1 if x >= 5 else 0)

        # rolling_sum_7 (보호소별 최근 7일간 발생 합계)
        merged['rolling_sum_7'] = merged.groupby('orgNm_encoded')['is_happened'].transform(
            lambda x: x.rolling(window=7, min_periods=1).sum()
        )

        # 스케일링
        merged[['orgNm_encoded', 'weekday', 'is_weekend', 'rolling_sum_7']] = self.scaler.fit_transform(
            merged[['orgNm_encoded', 'weekday', 'is_weekend', 'rolling_sum_7']]
        )

        self.merged_df = merged.sort_values(by=['happenDt', 'orgNm_encoded']).reset_index(drop=True)

        # 예측 시 빠른 접근을 위해 데이터를 org_id별로 미리 그룹화
        self._grouped_org_data = {
            org_id: self.merged_df[self.merged_df['orgNm_encoded_original'] == org_id].sort_values(by='happenDt')
            for org_id in self.all_org_encoded
        }

        print("데이터 전처리 완료. 미리보기:")
        print(self.merged_df.head())
        return True

    def _create_sequences(self):
        X, y = [], []
        feature_cols = ['is_happened', 'orgNm_encoded', 'weekday', 'is_weekend', 'rolling_sum_7']

        for org_id in self.merged_df['orgNm_encoded'].unique():
            org_data = self.merged_df[self.merged_df['orgNm_encoded'] == org_id].sort_values(by='happenDt')
            features = org_data[feature_cols].values

            for i in range(len(features) - self.sequence_length):
                X.append(features[i:(i + self.sequence_length)])
                y.append(features[i + self.sequence_length, 0])  # is_happened (다음날)

        return np.array(X), np.array(y)

    def load_model_for_prediction(self):
        """웹 예측을 위해 모델만 로드하는 최적화된 함수"""
        if os.path.exists(self.model_save_path):
            print(f"예측을 위해 기존 모델 '{self.model_save_path}'을(를) 불러옵니다.")
            self.model = load_model(self.model_save_path)
            return True
        else:
            print(f"오류: 모델 파일 '{self.model_save_path}'을(를) 찾을 수 없습니다.")
            return False

    def predict_all_orgnms_next_month(self, start_date_str="2025-08-01", end_date_str="2025-08-30", progress_callback=None):
        if self.model is None:
            print("모델이 로드되지 않았습니다. 먼저 train_or_load_model()을 실행하세요.")
            return []

        if self.merged_df is None or self.all_org_encoded is None:
            print("데이터 전처리가 완료되지 않았습니다. 먼저 preprocess_data()를 실행하세요.")
            return []

        from datetime import datetime
        import numpy as np

        prediction_start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        prediction_end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        num_prediction_days = (prediction_end_date - prediction_start_date).days + 1

        feature_cols = ['is_happened', 'orgNm_encoded', 'weekday', 'is_weekend', 'rolling_sum_7']
        org_nm_likelihoods = []
        all_sequences = []
        org_id_map = []
        org_name_map = {}

        # 1. 초기 시퀀스 수집
        for org_id in self.all_org_encoded:
            org_name = self.label_encoder.inverse_transform([int(org_id)])[0]
            recent_org_data = self._grouped_org_data.get(org_id)

            if recent_org_data is None or len(recent_org_data) < self.sequence_length:
                continue

            current_seq = recent_org_data[feature_cols].tail(self.sequence_length).values

            for _ in range(num_prediction_days):
                all_sequences.append(current_seq.copy())
                org_id_map.append(org_id)

            org_name_map[org_id] = org_name

        if not all_sequences:
            return []

        # 2. 예측
        X = np.stack(all_sequences, axis=0)  # (num_samples, seq_len, features)
        predictions = self.model.predict(X, verbose=0).flatten()

        # 3. 결과 누적
        org_id_to_total = {org_id: 0.0 for org_id in org_name_map}
        org_id_to_count = {org_id: 0 for org_id in org_name_map}

        for i, org_id in enumerate(org_id_map):
            org_id_to_total[org_id] += predictions[i]
            org_id_to_count[org_id] += 1
            if progress_callback:
                progress_callback(i / len(org_id_map))

        # 4. 평균 확률 계산
        for org_id in org_name_map:
            total = org_id_to_total[org_id]
            count = org_id_to_count[org_id]
            avg_prob_percent = round((total / count) * 100, 4) if count > 0 else 0.0
            org_nm_likelihoods.append({
                "org_name": org_name_map[org_id],
                "predicted_probability_percent": avg_prob_percent
            })

        # 5. 정렬
        sorted_org_nms = sorted(
            org_nm_likelihoods,
            key=lambda item: item["predicted_probability_percent"],
            reverse=True
        )

        return sorted_org_nms

if __name__ == "__main__":
    predictor = AnimalShelterPredictorImproved(
        model_save_path='lstm_model_animal_shelter_improved.h5',
        sequence_length=7
    )

    if predictor.preprocess_data(file_path='../data/data20230731_20250730.csv'):
        predictor.train_or_load_model()

        results = predictor.predict_all_orgnms_next_month(
            start_date_str="2025-08-01",
            end_date_str="2025-08-30"
        )

    else:
        print("데이터 전처리 실패!")