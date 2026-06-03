"""
MLP + XGBoost Hibrit Model Eğitimi
Türkiye'nin gerçek emisyon verileriyle hibrit model oluşturur
"""

from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
import shap

MODEL_DIR = Path("modeller")
HYBRID_MODEL_PATH = MODEL_DIR / "hibrit_model.joblib"
XGB_MODEL_PATH = MODEL_DIR / "xgb_haftalik_model.joblib"
MLP_MODEL_PATH = MODEL_DIR / "mlp_model.joblib"
SCALER_PATH = MODEL_DIR / "hybrid_scaler.joblib"
FEATURES_PATH = MODEL_DIR / "hybrid_features.joblib"
DATASET_PATH = Path("data/turkiye_emisyon_temiz.csv")

TRANSPORT_COLUMNS = ["dolmus_km", "otobus_km", "metro_km", "otomobil_km", "ucak_km"]
LAG_COUNT = 4


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ek özellikler üretir: toplam ulaşım, lag istatistikleri ve trend."""
    df = df.copy()
    transport_cols = ["dolmus_km", "otobus_km", "metro_km", "otomobil_km", "ucak_km"]
    df["transport_total_km"] = df[transport_cols].sum(axis=1)
    df["lag_mean_co2"] = df[["lag_1_co2", "lag_2_co2", "lag_3_co2", "lag_4_co2"]].mean(axis=1)
    df["lag_std_co2"] = df[["lag_1_co2", "lag_2_co2", "lag_3_co2", "lag_4_co2"]].std(axis=1).fillna(0.0)
    df["lag_trend"] = df["lag_1_co2"] - df["lag_4_co2"]
    return df


def hazirla_turkiye_verisi() -> pd.DataFrame:
    """Türkiye'nin gerçek emisyon verisiyle doğrudan model eğitim verisi hazırlar."""
    print("🇹🇷 GERÇEK TÜRKİYE EMİSYON VERİSİYLE HİBRİT MODEL EĞİTİMİ...")

    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Gerçek veri dosyası bulunamadı: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    print(f"📊 Gerçek veri: {len(df)} kayıt, sütunlar: {list(df.columns)}")

    expected = [
        'user_id', 'hafta', 'dolmus_km', 'otobus_km', 'metro_km',
        'otomobil_km', 'ucak_km', 'haftalik_co2_kg', 'sehir_kodu',
        'arac_sahibi', 'lag_1_co2', 'lag_2_co2', 'lag_3_co2',
        'lag_4_co2', 'target_next_week_co2'
    ]
    missing = [col for col in expected if col not in df.columns]
    if missing:
        raise ValueError(f"Gerçek veri kümesinde eksik sütunlar var: {missing}")

    return df[expected].copy()


def hazirla_ogrenme_tablosu(ham_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Gecmis haftalardan gelecek hafta CO2 tahmini icin supervised tablo uretir"""
    df = ham_df.sort_values(["user_id", "hafta"]).copy()
    df = engineer_features(df)
    
    # NaN değerleri temizle
    df = df.dropna(subset=['target_next_week_co2'])
    
    # Lag değerlerindeki NaN değerleri temizle
    lag_cols = ['lag_1_co2', 'lag_2_co2', 'lag_3_co2', 'lag_4_co2']
    df = df.dropna(subset=lag_cols)
    
    feature_cols = [
        'user_id', 'hafta', 'sehir_kodu', 'arac_sahibi',
        'dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km',
        'transport_total_km', 'lag_mean_co2', 'lag_std_co2', 'lag_trend',
        'lag_1_co2', 'lag_2_co2', 'lag_3_co2', 'lag_4_co2'
    ]
    
    return df, feature_cols


class HibritModel:
    """Stacking Hibrit Model: XGBoost + MLP base learners + Ridge meta learner"""

    def __init__(self):
        self.xgb_model = None
        self.mlp_model = None
        self.meta_model = Ridge(alpha=1.0)
        self.scaler = StandardScaler()
        self.feature_cols = None
        self.feature_means = None

    def _build_oof_meta_features(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.Series,
        n_splits: int = 5,
    ) -> np.ndarray:
        """Out-of-fold tahminler üreterek meta-özellik tablosu oluşturur."""
        oof_preds = np.zeros((len(X), 2), dtype=np.float64)
        n_splits = min(n_splits, len(np.unique(groups)))
        group_kfold = GroupKFold(n_splits=n_splits)

        print("🔁 OOF meta-özellikler için GroupKFold çalışıyor...")
        for fold, (train_idx, valid_idx) in enumerate(group_kfold.split(X, y, groups=groups), start=1):
            print(f"   Fold {fold}/{group_kfold.n_splits} - train={len(train_idx)}, valid={len(valid_idx)}")
            X_train_fold = X.iloc[train_idx]
            y_train_fold = y.iloc[train_idx]
            X_valid_fold = X.iloc[valid_idx]

            xgb_fold = XGBRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.03,
                subsample=0.80,
                colsample_bytree=0.80,
                objective='reg:squarederror',
                random_state=42,
                n_jobs=-1,
                tree_method='hist',
                reg_alpha=0.1,
                reg_lambda=1.0,
            )
            xgb_fold.fit(X_train_fold, y_train_fold)

            scaler_fold = StandardScaler()
            X_train_scaled = scaler_fold.fit_transform(X_train_fold)
            mlp_fold = MLPRegressor(
                hidden_layer_sizes=(100, 50, 25),
                activation='relu',
                solver='adam',
                alpha=0.001,
                batch_size=32,
                learning_rate='adaptive',
                learning_rate_init=0.001,
                max_iter=500,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1,
                n_iter_no_change=20,
            )
            mlp_fold.fit(X_train_scaled, y_train_fold)

            oof_preds[valid_idx, 0] = xgb_fold.predict(X_valid_fold)
            oof_preds[valid_idx, 1] = mlp_fold.predict(scaler_fold.transform(X_valid_fold))

        return oof_preds

    def _fit_base_learners(self, X: pd.DataFrame, y: pd.Series) -> None:
        print("🤖 Temel XGBoost modeli eğitiliyor...")
        self.xgb_model = XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.03,
            subsample=0.80,
            colsample_bytree=0.80,
            objective='reg:squarederror',
            random_state=42,
            n_jobs=-1,
            tree_method='hist',
            reg_alpha=0.1,
            reg_lambda=1.0,
        )
        self.xgb_model.fit(X, y)

        print("🧠 Temel MLP modeli eğitiliyor...")
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.mlp_model = MLPRegressor(
            hidden_layer_sizes=(100, 50, 25),
            activation='relu',
            solver='adam',
            alpha=0.001,
            batch_size=32,
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=20,
        )
        self.mlp_model.fit(X_scaled, y)

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        groups: pd.Series,
    ) -> None:
        """Stacking modeli eğitir."""
        print("🚀 Stacking eğitim süreci başlıyor...")
        meta_X = self._build_oof_meta_features(X_train, y_train, groups)
        self.meta_model.fit(meta_X, y_train)
        print("✅ Meta-learner (Ridge) eğitildi")
        self._fit_base_learners(X_train, y_train)
        self.feature_means = X_train.mean().to_dict()
        print("✅ Tüm base learner modelleri yeniden tam veriyle eğitildi")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        xgb_pred = self.xgb_model.predict(X)
        X_scaled = self.scaler.transform(X)
        mlp_pred = self.mlp_model.predict(X_scaled)
        meta_X = np.column_stack([xgb_pred, mlp_pred])
        return self.meta_model.predict(meta_X)

    def explain_xgb(self, X: pd.DataFrame) -> np.ndarray:
        """XGBoost bileşeni için SHAP değerleri hesaplar."""
        if self.xgb_model is None:
            raise ValueError("XGB modeli yuklu degil.")

        explainer = shap.TreeExplainer(self.xgb_model)
        shap_vals = explainer.shap_values(X)
        return shap_vals

    def get_individual_predictions(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        xgb_pred = self.xgb_model.predict(X)
        X_scaled = self.scaler.transform(X)
        mlp_pred = self.mlp_model.predict(X_scaled)
        meta_X = np.column_stack([xgb_pred, mlp_pred])
        return {
            'xgb': xgb_pred,
            'mlp': mlp_pred,
            'meta': self.meta_model.predict(meta_X)
        }


def hibrit_model_egit():
    """Hibrit modeli eğit ve kaydet"""
    print("🚀 HİBRİT MODEL EĞİTİMİ BAŞLIYOR...")

    df_sentetik = hazirla_turkiye_verisi()
    ogrenme_df, feature_cols = hazirla_ogrenme_tablosu(df_sentetik)

    train_df = ogrenme_df[ogrenme_df['hafta'] <= 17].copy()
    test_df = ogrenme_df[ogrenme_df['hafta'] > 17].copy()

    x_train = train_df[feature_cols]
    y_train = train_df['target_next_week_co2']
    groups = train_df['user_id']
    x_test = test_df[feature_cols]
    y_test = test_df['target_next_week_co2']

    print(f"📊 Eğitim seti: {len(x_train)} örnek")
    print(f"📊 Test seti: {len(x_test)} örnek")

    hibrit_model = HibritModel()
    hibrit_model.feature_cols = feature_cols
    hibrit_model.fit(x_train, y_train, groups)

    y_pred_hybrid = hibrit_model.predict(x_test)
    individual_preds = hibrit_model.get_individual_predictions(x_test)

    mae_hybrid = mean_absolute_error(y_test, y_pred_hybrid)
    mse_hybrid = mean_squared_error(y_test, y_pred_hybrid)
    r2_hybrid = r2_score(y_test, y_pred_hybrid)

    mae_xgb = mean_absolute_error(y_test, individual_preds['xgb'])
    mae_mlp = mean_absolute_error(y_test, individual_preds['mlp'])

    print(f"\n📈 HİBRİT STACKING MODEL PERFORMANSI:")
    print(f"  MAE: {mae_hybrid:.3f} kg CO2/hafta")
    print(f"  MSE: {mse_hybrid:.3f}")
    print(f"  R²: {r2_hybrid:.4f}")

    print(f"\n📈 BİREYSEL BASE LEARNER PERFORMANSI:")
    print(f"  XGBoost MAE: {mae_xgb:.3f} kg CO2/hafta")
    print(f"  MLP MAE: {mae_mlp:.3f} kg CO2/hafta")
    if mae_xgb > 0:
        improvement_pct = (mae_xgb - mae_hybrid) / mae_xgb * 100
        print(f"  Önceki XGBoost ile karşılaştırma: %{improvement_pct:.2f} iyileşme")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(hibrit_model, HYBRID_MODEL_PATH)
    joblib.dump(feature_cols, FEATURES_PATH)
    joblib.dump(hibrit_model.scaler, SCALER_PATH)

    print(f"\n✅ Hibrit model kaydedildi: {HYBRID_MODEL_PATH.resolve()}")
    print(f"✅ Özellikler kaydedildi: {FEATURES_PATH.resolve()}")
    print(f"✅ Scaler kaydedildi: {SCALER_PATH.resolve()}")

    return hibrit_model, mae_hybrid, r2_hybrid


if __name__ == "__main__":
    hibrit_model, mae, r2 = hibrit_model_egit()
    print(f"\n🎉 HİBRİT STACKING MODEL EĞİTİMİ TAMAMLANDI!")
    print(f"📊 Final MAE: {mae:.3f} kg CO2/hafta")
    print(f"📊 Final R²: {r2:.4f}")
