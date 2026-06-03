import pandas as pd
import numpy as np
from pathlib import Path

def temizle_veri_seti(input_path, output_path):
    """
    Mevcut veri setini temizler ve iyileştirir
    """
    print("🔧 Veri temizleme başlatılıyor...")
    
    # Veriyi yükle
    df = pd.read_csv(input_path)
    original_size = len(df)
    
    # 1. Aykırı değerleri temizle (IQR method)
    print("📊 Aykırı değerler temizleniyor...")
    for col in ['dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km']:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Aykırı değerleri upper bound ile sınırla (kaldırma)
        df[col] = df[col].clip(lower_bound, upper_bound)
    
    # 2. Uçak verilerini daha gerçekçi yap
    print("✈️ Uçak verileri düzenleniyor...")
    df['ucak_km'] = df['ucak_km'].clip(upper=500)  # Maksimum 500km/hafta
    
    # 3. CO2 hesaplamalarını yeniden yap
    print("🌱 CO2 hesaplamaları güncelleniyor...")
    from veriler import EMISSION_FACTORS_TR
    
    df['calculated_co2'] = (
        df["dolmus_km"] * EMISSION_FACTORS_TR["dolmus_kg_per_km"] +
        df["otobus_km"] * EMISSION_FACTORS_TR["otobus_kg_per_km"] +
        df["metro_km"] * EMISSION_FACTORS_TR["metro_kg_per_km"] +
        df["otomobil_km"] * EMISSION_FACTORS_TR["otomobil_kg_per_km"] +
        df["ucak_km"] * EMISSION_FACTORS_TR["ucak_kg_per_km"]
    )
    
    # 4. Küçük farklılıkları düzelt
    df['haftalik_co2_kg'] = df['calculated_co2']
    df = df.drop('calculated_co2', axis=1)
    
    # 5. Veri ekle (daha fazla çeşitlilik için)
    print("📈 Ek veri noktaları ekleniyor...")
    additional_data = []
    
    # Mevcut verilere dayalı yeni örnekler oluştur
    for _ in range(300):  # 300 yeni kayıt
        random_row = df.sample(1).iloc[0]
        new_row = random_row.copy()
        
        # Küçük varyasyonlar ekle
        new_row['user_id'] = df['user_id'].max() + 1
        new_row['hafta'] = np.random.randint(1, 21)
        
        for col in ['dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km']:
            variation = np.random.uniform(0.8, 1.2)  # ±20% varyasyon
            new_row[col] = max(0, new_row[col] * variation)
        
        # CO2'yi yeniden hesapla
        new_row['haftalik_co2_kg'] = (
            new_row["dolmus_km"] * EMISSION_FACTORS_TR["dolmus_kg_per_km"] +
            new_row["otobus_km"] * EMISSION_FACTORS_TR["otobus_kg_per_km"] +
            new_row["metro_km"] * EMISSION_FACTORS_TR["metro_kg_per_km"] +
            new_row["otomobil_km"] * EMISSION_FACTORS_TR["otomobil_kg_per_km"] +
            new_row["ucak_km"] * EMISSION_FACTORS_TR["ucak_kg_per_km"]
        )
        
        additional_data.append(new_row)
    
    # Yeni verileri ekle
    df_extended = pd.concat([df, pd.DataFrame(additional_data)], ignore_index=True)
    
    # Temizlenmiş veriyi kaydet
    df_extended.to_csv(output_path, index=False)
    
    print(f"✅ Veri temizleme tamamlandı!")
    print(f"📊 Orijinal boyut: {original_size}")
    print(f"📊 Yeni boyut: {len(df_extended)}")
    print(f"📈 Artış: {len(df_extended) - original_size} yeni kayıt")
    
    return df_extended

if __name__ == "__main__":
    # Varsayılan olarak proje veri klasöründeki Türkiye emisyon verisini kullan
    input_path = "data/turkiye_emisyon.csv"
    output_path = "data/turkiye_emisyon_temiz.csv"

    temizlenmis_veri = temizle_veri_seti(input_path, output_path)
