from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor

from veriler import EMISSION_FACTORS_TR

MODEL_DIR = Path("modeller")
MODEL_PATH = MODEL_DIR / "xgb_aylik_model.joblib"
FEATURES_PATH = MODEL_DIR / "xgb_aylik_features.joblib"
DATASET_PATH = Path("data/turkiye_emisyon_temiz.csv")

TRANSPORT_COLUMNS = ["dolmus_km", "otobus_km", "metro_km", "otomobil_km", "ucak_km"]
LAG_COUNT = 4


def _transport_co2(row: pd.Series) -> float:
    """Sadece ulaşım kalemlerinden CO2 kg cinsinden hesaplar."""
    return (
        row["dolmus_km"] * EMISSION_FACTORS_TR["dolmus_kg_per_km"]
        + row["otobus_km"] * EMISSION_FACTORS_TR["otobus_kg_per_km"]
        + row["metro_km"] * EMISSION_FACTORS_TR["metro_kg_per_km"]
        + row["otomobil_km"] * EMISSION_FACTORS_TR["otomobil_kg_per_km"]
        + row["ucak_km"] * EMISSION_FACTORS_TR["ucak_kg_per_km"]
    )


def hazirla_turkiye_emisyon_verisi(n_kullanici=120, hafta_sayisi=20, seed=42):
    """
    Türkiye'nin gerçek emisyon verilerini kullanarak sentetik veri seti hazırlar.
    Bu fonksiyon eski haftalık referans modele dayanan legacy bir üretim akışıdır.
    Güncel aylık eğitim akışı `train_turkiye_model()` fonksiyonunda yer almaktadır.
    """
    print("🇹🇷 TÜRKİYE GERÇEK EMİSYON VERİLERİYLE SENTETİK SETİ HAZIRLANIYOR...")

    # Türkiye emisyon verisini yükle
    df_turkey = pd.read_csv("data/turkiye_emisyon_temiz.csv")
    print(f"📊 Türkiye emisyon verisi yüklendi: {len(df_turkey)} kayıt")

    # Kullanıcı bazında sentetik verisi oluştur
    rng = np.random.default_rng(seed)

    sentetik_veriler = []

    for user_id in range(1, n_kullanici + 1):
        # Her kullanıcı için rastgele hafta verisi oluştur
        user_data = []

        for hafta in range(1, hafta_sayisi + 1):
            # Haftayı rastgele seç (1970-2024 aralığından)
            hafta_index = rng.randint(0, len(df_turkey) - 1)
            selected_year = df_turkey.iloc[hafta_index]['Category']

            # Türkiye ortalamasına göre ulaşım verileri hesapla
            # Haftalık ulaşım mesafesi (Türkiye ortalaması)
            haftalik_ulasim_km = (df_turkey.iloc[hafta_index]['Transport'] / 85_000_000) * 1000 / 52  # Kişi başına düşen haftalık

            # Ulaşım dağılımını rastgele belirle
            dolmus_orani = rng.uniform(0.25, 0.45)  # %25-45 dolmuş
            otobus_orani = rng.uniform(0.30, 0.50)  # %30-50 otobüs
            metro_orani = rng.uniform(0.15, 0.25)  # %15-25 metro
            otomobil_orani = rng.uniform(0.05, 0.20)  # %5-20 otomobil
            ucak_orani = rng.uniform(0.01, 0.05)   # %1-5 uçak

            # Ulaşım mesafelerini hesapla
            dolmus_km = haftalik_ulasim_km * dolmus_orani
            otobus_km = haftalik_ulasim_km * otobus_orani
            metro_km = haftalik_ulasim_km * metro_orani
            otomobil_km = haftalik_ulasim_km * otomobil_orani
            ucak_km = haftalik_ulasim_km * ucak_orani

            # Haftalık CO2 emisyonunu hesapla
            haftalik_co2_kg = (
                dolmus_km * 0.138 +  # Türkiye'ye özgü dolmuş
                otobus_km * 0.089 +  # Standart otobüs
                metro_km * 0.035 +   # Elektrikli metro
                otomobil_km * 0.192 +  # Standart otomobil
                ucak_km * 0.255      # Türk Hava Yolları
            )

            user_data.append({
                'user_id': user_id,
                'hafta': hafta,
                'yil': selected_year,
                'dolmus_km': round(dolmus_km, 1),
                'otobus_km': round(otobus_km, 1),
                'metro_km': round(metro_km, 1),
                'otomobil_km': round(otomobil_km, 1),
                'ucak_km': round(ucak_km, 1),
                'haftalik_co2_kg': round(haftalik_co2_kg, 2)
            })

        sentetik_veriler.extend(user_data)

    # DataFrame'e çevir
    df_sentetik = pd.DataFrame(sentetik_veriler)
    print(f"📊 {len(df_sentetik)} kullanıcı için {len(df_sentetik)} haftalık veri oluşturuldu")
    print(f"📅 Yıl aralığı: {df_sentetik['yil'].min()}-{df_sentetik['yil'].max()}")
    print(f"🚌 Ortalama haftalık ulaşım: {df_sentetik[['dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km']].sum(axis=1).mean():.1f} km")
    print(f"📈 Ortalama haftalık CO2: {df_sentetik['haftalik_co2_kg'].mean():.2f} kg")

    df_sentetik["haftalik_co2_kg"] = df_sentetik.apply(_transport_co2, axis=1).round(3)
    return df_sentetik


def ogrenme_tablosu_hazirla(ham_df: pd.DataFrame):
    """Geçmiş zaman dilimlerinden geleceğe yönelik CO2 tahmini için supervised tablo üretir."""
    df = ham_df.sort_values(["user_id", "hafta"]).copy()
    df["sehir_kodu"] = df["sehir"].astype("category").cat.codes

    for lag in range(1, LAG_COUNT + 1):
        df[f"lag_{lag}_co2"] = df.groupby("user_id")["haftalik_co2_kg"].shift(lag)

    df["target_next_week_co2"] = df.groupby("user_id")["haftalik_co2_kg"].shift(-1)
    df = df.dropna().reset_index(drop=True)

    feature_cols = (
        ["hafta", "sehir_kodu", "arac_sahibi"]
        + TRANSPORT_COLUMNS
        + [f"lag_{lag}_co2" for lag in range(1, LAG_COUNT + 1)]
    )
    return df, feature_cols


def modeli_egit_ve_kaydet():
    ham_df = hazirla_referans_tr_ulasim_verisi(n_kullanici=120, hafta_sayisi=20, seed=42)
    ogrenme_df, feature_cols = ogrenme_tablosu_hazirla(ham_df)

    # LEGACY: Bu bölüm eski haftalık referans verisiyle model eğitimi için kalmıştır.
    train_df = ogrenme_df[ogrenme_df["hafta"] <= 16]
    test_df = ogrenme_df[ogrenme_df["hafta"] > 16]

    x_train = train_df[feature_cols]
    y_train = train_df["target_next_week_co2"]
    x_test = test_df[feature_cols]
    y_test = test_df["target_next_week_co2"]

    model = XGBRegressor(
        n_estimators=180,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.90,
        colsample_bytree=0.90,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(x_train, y_train)

    pred = model.predict(x_test)
    mae = mean_absolute_error(y_test, pred)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    ham_df.to_csv(DATASET_PATH, index=False)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(feature_cols, FEATURES_PATH)

    print(f"Sentetik veri kaydedildi: {DATASET_PATH.resolve()}")
    print(f"Model kaydedildi: {MODEL_PATH.resolve()}")
    print(f"Ozellik listesi kaydedildi: {FEATURES_PATH.resolve()}")
    print(f"Test MAE (kgCO2/hafta): {mae:.3f}")


def train_turkiye_model():
    """Türkiye'nin gerçek emisyon verileriyle model eğit"""
    print("🇹🇷 TÜRKİYE GERÇEK EMİSYON VERİLERİYLE MODEL EĞİTİMİ...")
    
    # Türkiye emisyon verisini yükle
    df_turkey = pd.read_csv("data/turkiye_emisyon.csv")
    print(f"📊 Türkiye emisyon verisi: {len(df_turkey)} kayıt")
    
    # Power Industry verilerini kullanarak elektrik katsayısı hesapla
    latest_power = df_turkey[df_turkey['Category'] == df_turkey['Category'].max()]['Power Industry'].iloc[0]
    turkey_population = 85_000_000
    turkey_electricity_consumption = 300_000_000_000  # kWh/yıl
    
    # Elektrik katsayısı (kg CO2/kWh)
    electricity_factor = (latest_power * 1000) / turkey_electricity_consumption
    print(f"⚡ Elektrik katsayısı: {electricity_factor:.6f} kg CO2/kWh")
    
    # Transport verilerini kullanarak ulaşım katsayıları
    latest_transport = df_turkey[df_turkey['Category'] == df_turkey['Category'].max()]['Transport'].iloc[0]
    
    # Haftalık ulaşım emisyonu (kg CO2/hafta)
    weekly_transport_emission = latest_transport / 52
    
    # Haftalık ulaşım mesafesi (km/hafta) - Türkiye ortalamasına göre
    weekly_transport_km = (weekly_transport_emission / electricity_factor) / 4  # Ortalama 4 ulaşım modu
    
    # Ulaşım katsayıları
    dolmus_factor = electricity_factor * 0.138  # %20 artış
    otobus_factor = electricity_factor * 0.089
    metro_factor = electricity_factor * 0.035
    otomobil_factor = electricity_factor * 0.192
    ucak_factor = electricity_factor * 0.255
    
    print(f"🚌 Ulaşım katsayıları:")
    print(f"  Dolmuş: {dolmus_factor:.6f} kg CO2/km")
    print(f"  Otobüs: {otobus_factor:.6f} kg CO2/km")
    print(f"  Metro: {metro_factor:.6f} kg CO2/km")
    print(f"  Otomobil: {otomobil_factor:.6f} kg CO2/km")
    print(f"  Uçak: {ucak_factor:.6f} kg CO2/km")
    
    # Kullanıcı bazında sentetik verisi oluştur (AYLIK)
    sentetik_veriler = []

    # Tek bir RNG kullan ve tekrarları kontrol et
    rng = np.random.default_rng(42)

    # Aylık ölçeğe çevirme katsayısı
    WEEKS_PER_MONTH = 4.345
    monthly_transport_km = weekly_transport_km * WEEKS_PER_MONTH

    for user_id in range(1, 301):  # 300 kullanıcı
        user_data = []

        # Bu kullanıcı için bir "Ana Profil (Baseline)" oluştur (aylık ortalama km)
        dolmus_base = monthly_transport_km * rng.uniform(0.25, 0.45)
        otobus_base = monthly_transport_km * rng.uniform(0.30, 0.50)
        metro_base = monthly_transport_km * rng.uniform(0.15, 0.25)
        otomobil_base = monthly_transport_km * rng.uniform(0.05, 0.20)
        ucak_base = rng.uniform(0, 50)

        for ay in range(1, 31):  # 30 ay
            # Aylık değerleri baseline üzerine %3-%6 arası küçük sapma ile oluştur
            def apply_pct_noise(base):
                pct = rng.uniform(0.03, 0.06)
                if rng.random() < 0.5:
                    pct = -pct
                val = base * (1.0 + pct)
                return max(0, int(round(val)))

            dolmus_km = apply_pct_noise(dolmus_base)
            otobus_km = apply_pct_noise(otobus_base)
            metro_km = apply_pct_noise(metro_base)
            otomobil_km = apply_pct_noise(otomobil_base)
            ucak_km = apply_pct_noise(ucak_base)

            # Aylık CO2 emisyonu (makro katsayıları değiştirmiyoruz)
            aylik_co2_kg = round(
                dolmus_km * dolmus_factor +
                otobus_km * otobus_factor +
                metro_km * metro_factor +
                otomobil_km * otomobil_factor +
                ucak_km * ucak_factor
            , 2)

            user_data.append({
                'user_id': user_id,
                'ay': ay,
                'dolmus_km': max(0, dolmus_km),
                'otobus_km': max(0, otobus_km),
                'metro_km': max(0, metro_km),
                'otomobil_km': max(0, otomobil_km),
                'ucak_km': max(0, ucak_km),
                'aylik_co2_kg': aylik_co2_kg
            })

        sentetik_veriler.extend(user_data)
    
    # DataFrame'e çevir
    df_sentetik = pd.DataFrame(sentetik_veriler)
    print(f"📊 {len(df_sentetik)} aylık kayıt oluşturuldu")
    print(f"📅 Ay aralığı: 1-30")
    print(f"🚌 Ortalama aylık ulaşım: {df_sentetik[['dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km']].sum(axis=1).mean():.1f} km")
    print(f"📈 Ortalama aylık CO2: {df_sentetik['aylik_co2_kg'].mean():.2f} kg")
    
    # Özellikler ve hedef değişken
    df_sentetik['sehir_kodu'] = 34  # İstanbul kodu
    df_sentetik['arac_sahibi'] = 1  # Araç sahibi
    df_sentetik['lag_1_co2'] = df_sentetik.groupby('user_id')['aylik_co2_kg'].shift(1)
    df_sentetik['lag_2_co2'] = df_sentetik.groupby('user_id')['aylik_co2_kg'].shift(2)
    df_sentetik['lag_3_co2'] = df_sentetik.groupby('user_id')['aylik_co2_kg'].shift(3)
    df_sentetik['lag_4_co2'] = df_sentetik.groupby('user_id')['aylik_co2_kg'].shift(4)
    df_sentetik['target_next_month_co2'] = df_sentetik.groupby('user_id')['aylik_co2_kg'].shift(-1)
    
    # Veriyi kaydet
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df_sentetik.to_csv(DATASET_PATH, index=False)
    print(f"✅ Sentetik verisi kaydedildi: {DATASET_PATH.resolve()}")
    
    # Model eğitimi
    feature_cols = [
        'ay', 'sehir_kodu', 'arac_sahibi',
        'dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km',
        'lag_1_co2', 'lag_2_co2', 'lag_3_co2', 'lag_4_co2'
    ]

    # Son 3 ay test, geri kalani eğitim
    train_df = df_sentetik[df_sentetik['ay'] <= 17]
    test_df = df_sentetik[df_sentetik['ay'] > 17]

    # NaN değerleri temizle
    train_df = train_df.dropna(subset=['target_next_month_co2'])
    test_df = test_df.dropna(subset=['target_next_month_co2'])

    x_train = train_df[feature_cols]
    y_train = train_df['target_next_month_co2']
    x_test = test_df[feature_cols]
    y_test = test_df['target_next_month_co2']
    
    model = XGBRegressor(
        n_estimators=180,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.90,
        colsample_bytree=0.90,
        objective='reg:squarederror',
        random_state=42,
    )
    
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    mae = mean_absolute_error(y_test, pred)
    
    joblib.dump(model, MODEL_PATH)
    joblib.dump(feature_cols, FEATURES_PATH)
    
    print(f"✅ Model eğitildi: {MODEL_PATH.resolve()}")
    print(f"✅ Özellikler kaydedildi: {FEATURES_PATH.resolve()}")
    print(f"📈 Test MAE: {mae:.3f} kg CO2/ay")
    
    return model

if __name__ == "__main__":
    train_turkiye_model()
