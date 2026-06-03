import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Türkiye emisyon verisini analiz et
def analyze_turkey_emissions():
    print("🇹🇷 TÜRKİYE EMİSYON VERİSİ ANALİZİ")
    print("=" * 50)
    
    # Veriyi yükle
    df = pd.read_csv("data/turkiye_emisyon.csv")
    
    # Sütunları temizle
    df.columns = df.columns.str.replace('"', '').str.strip()
    df['Category'] = pd.to_numeric(df['Category'])
    
    print(f"📊 Veri aralığı: {df['Category'].min()} - {df['Category'].max()}")
    print(f"📊 Toplam yıl sayısı: {len(df)}")
    
    # Son 10 yılın analizi
    recent_years = df.tail(10)
    print(f"\n📈 SON 10 YIL EMİSYON TRENDLERİ:")
    print(recent_years[['Category', 'Transport', 'Power Industry', 'Buildings']].to_string(index=False))
    
    # Sektörel büyüme oranları
    print(f"\n📈 YILLIK BÜYÜME ORANLARI (%):")
    for sector in ['Transport', 'Power Industry', 'Buildings']:
        growth_rate = ((df[sector].iloc[-1] / df[sector].iloc[0]) ** (1/(len(df)-1)) - 1) * 100
        print(f"  {sector}: {growth_rate:.2f}%")
    
    # 2024 verileri
    latest_data = df.iloc[-1]
    transport_2024 = latest_data['Transport']
    power_2024 = latest_data['Power Industry'] 
    buildings_2024 = latest_data['Buildings']
    total_2024 = transport_2024 + power_2024 + buildings_2024
    
    print(f"\n📊 2024 YILI EMİSYONLARI (ton CO2):")
    print(f"  Transport: {transport_2024:,.0f}")
    print(f"  Power Industry: {power_2024:,.0f}")
    print(f"  Buildings: {buildings_2024:,.0f}")
    print(f"  Toplam: {total_2024:,.0f}")
    
    return {
        'transport_2024': transport_2024,
        'power_2024': power_2024,
        'buildings_2024': buildings_2024,
        'total_2024': total_2024,
        'df': df
    }

if __name__ == "__main__":
    analysis = analyze_turkey_emissions()
