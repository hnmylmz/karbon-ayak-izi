import pandas as pd
import numpy as np
from pathlib import Path

# Veri setini yükle (temizlenmiş Türkiye verisi)
data_path = Path("data/turkiye_emisyon_temiz.csv")
df = pd.read_csv(data_path)

print("=== VERİ SETİ ANALİZİ ===")
print(f"Toplam kayıt sayısı: {len(df)}")
print(f"Kullanıcı sayısı: {df['user_id'].nunique()}")
print(f"Hafta sayısı: {df['hafta'].nunique()}")
print(f"Şehirler: {df['sehir'].unique()}")

print("\n=== TEMEL İSTATİSTİKLER ===")
print(df[['dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km', 'haftalik_co2_kg']].describe())

print("\n=== EKSİK VERİ KONTROLÜ ===")
print(df.isnull().sum())

print("\n=== AYKIRI DEĞER KONTROLÜ ===")
for col in ['dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km']:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
    print(f"{col}: {len(outliers)} aykırı değer")

print("\n=== VERİ KALİTESİ DEĞERLENDİRMESİ ===")
# Negatif değer kontrolü
negative_values = (df[['dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km']] < 0).any(axis=1).sum()
print(f"Negatif değer sayısı: {negative_values}")

# Mantıksal tutarsızlıklar
zero_transport_but_co2 = df[(df[['dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km']].sum(axis=1) == 0) & (df['haftalik_co2_kg'] > 0)].shape[0]
print(f"Sıfır ulaşım ama CO2 var: {zero_transport_but_co2}")

print("\n=== ŞEHİR BAZLI DAĞILIM ===")
sehir_stats = df.groupby('sehir')['haftalik_co2_kg'].agg(['mean', 'count', 'std'])
print(sehir_stats)

print("\n=== ZAMAN SERİSİ KONTROLÜ ===")
# Her kullanıcının veri sürekliliği
user_week_counts = df.groupby('user_id')['hafta'].count()
incomplete_users = user_week_counts[user_week_counts < 20].count()
print(f"20 haftadan az verisi olan kullanıcı: {incomplete_users}")

print("\n=== ÖNERİLER ===")
if negative_values == 0 and zero_transport_but_co2 == 0:
    print("✅ Veri seti temiz görünüyor")
else:
    print("⚠️ Veri temizleme gerekebilir")

if len(df) >= 2000:
    print("✅ Yeterli veri miktarı")
else:
    print("⚠️ Daha fazla veri gerekli")
