"""
Türkiye emisyon veri işleyici
data/turkiye_emisyon.csv dosyasını okur ve temizler
Yılları X ekseni, emisyonları Y ekseni olarak ayarlar
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

def load_turkey_emissions():
    """
    Türkiye emisyon verisini yükle ve temizle
    Sadece Category, Transport, Power Industry, Total CO2/cap sütunları
    """
    print("📊 TÜRKİYE EMİSYON VERİSİ YÜKLENİYOR...")
    
    # Veriyi yükle
    file_path = Path("data/turkiye_emisyon.csv")
    if not file_path.exists():
        print(f"❌ Dosya bulunamadı: {file_path}")
        return None
    
    df = pd.read_csv(file_path)
    
    # Sütunları temizle
    df.columns = df.columns.str.replace('"', '').str.strip()
    
    # İstenilen sütunları seç
    required_columns = ['Category', 'Transport', 'Power Industry', 'Total CO2/cap']
    available_columns = df.columns.tolist()
    
    print(f"📋 Mevcut sütunlar: {available_columns}")
    print(f"🎯 İstenilen sütunlar: {required_columns}")
    
    # Eksik sütunları kontrol et
    missing_columns = [col for col in required_columns if col not in available_columns]
    if missing_columns:
        print(f"⚠️ Eksik sütunlar: {missing_columns}")
        return None
    
    df_clean = df[required_columns].copy()
    
    # Category sütununu sayısal hale getir
    df_clean['Category'] = pd.to_numeric(df_clean['Category'], errors='coerce')
    
    # Eksik değerleri temizle
    print("\n🧹 VERİ TEMİZLENİYOR...")
    
    # Null değerleri kontrol et
    null_counts = df_clean.isnull().sum()
    if null_counts.any():
        print(f"⚠️ Null değerler bulundu:")
        for col, count in null_counts.items():
            if count > 0:
                print(f"  {col}: {count} adet")
    
    # Negatif değerleri kontrol et
    negative_counts = (df_clean[required_columns[1:]] < 0).sum()
    if negative_counts.any():
        print(f"⚠️ Negatif değerler bulundu:")
        for col, count in negative_counts.items():
            if count > 0:
                print(f"  {col}: {count} adet")
    
    # Veri tiplerini kontrol et
    print(f"\n📊 VERİ TİPLERİ:")
    for col in df_clean.columns:
        if col != 'Category':
            dtype = df_clean[col].dtype
            print(f"  {col}: {dtype}")
    
    # Temizlenmiş veriyi döndür
    df_clean = df_clean.dropna()
    df_clean = df_clean[df_clean['Category'] >= 1970]  # 1970'ten sonrası
    
    print(f"\n✅ Veri temizlendi: {len(df_clean)} kayıt")
    print(f"📅 Tarih aralığı: {df_clean['Category'].min()} - {df_clean['Category'].max()}")
    
    return df_clean

def prepare_data_for_visualization(df):
    """
    Veriyi görselleştirme için hazırla
    X ekseni: Yıllar, Y ekseni: Emisyonlar
    """
    print("\n📈 GÖRSELLEŞTİRME İÇİN VERİ HAZIRLANIYOR...")
    
    # Yılları X ekseni olarak ayarla
    years = df['Category'].values
    transport_emissions = df['Transport'].values
    power_emissions = df['Power Industry'].values
    total_emissions = df['Total CO2/cap'].values
    
    # Veri setleri oluştur
    data_sets = {
        'years': years,
        'transport': transport_emissions,
        'power': power_emissions,
        'total': total_emissions
    }
    
    print(f"📊 Hazırlanan veriler:")
    print(f"  Yıllar: {len(years)} adet")
    print(f"  Transport emisyonları: {len(transport_emissions)} adet")
    print(f"  Power Industry emisyonları: {len(power_emissions)} adet")
    print(f"  Toplam emisyonlar: {len(total_emissions)} adet")
    
    return data_sets

def calculate_emission_trends(df):
    """
    Emisyon trendlerini hesapla
    """
    print("\n📈 EMİSYON TRENDLERİ HESAPLANIYOR...")
    
    # Yıllık büyüme oranları
    trends = {}
    
    for sector in ['Transport', 'Power Industry', 'Total CO2/cap']:
        if sector in df.columns:
            # Yıllık değişim oranları
            annual_growth = df[sector].pct_change().fillna(0) * 100
            
            # Ortalama yıllık büyüme
            avg_growth = annual_growth.mean()
            
            # Son 10 yıllık ortalama büyüme
            recent_growth = annual_growth.tail(10).mean()
            
            trends[sector] = {
                'avg_annual_growth': avg_growth,
                'recent_10y_growth': recent_growth,
                'total_growth_since_1970': ((df[sector].iloc[-1] / df[sector].iloc[0]) - 1) * 100
            }
            
            print(f"📊 {sector}:")
            print(f"  Ortalama yıllık büyüme: {avg_growth:.2f}%")
            print(f"  Son 10 yıllık ortalama: {recent_growth:.2f}%")
            print(f"  1970'ten bu yana toplam büyüme: {trends[sector]['total_growth_since_1970']:.2f}%")
    
    return trends

def create_emission_summary(df):
    """
    Emisyon özetini oluştur
    """
    print("\n📋 EMİSYON ÖZETİ OLUŞTURULUYOR...")
    
    summary = {}
    
    # En son yılın verileri
    latest_year = df['Category'].max()
    latest_data = df[df['Category'] == latest_year].iloc[0]
    
    summary['latest_year'] = latest_year
    summary['transport_2024'] = latest_data['Transport']
    summary['power_2024'] = latest_data['Power Industry']
    summary['total_per_capita_2024'] = latest_data['Total CO2/cap']
    
    # Tarihsel ortalamalar
    summary['avg_transport'] = df['Transport'].mean()
    summary['avg_power'] = df['Power Industry'].mean()
    summary['avg_total_per_capita'] = df['Total CO2/cap'].mean()
    
    # Maksimum ve minimum değerler
    summary['max_transport'] = df['Transport'].max()
    summary['min_transport'] = df['Transport'].min()
    summary['max_power'] = df['Power Industry'].max()
    summary['min_power'] = df['Power Industry'].min()
    
    print(f"📊 ÖZET BİLGİLERİ:")
    print(f"  Son yıl ({latest_year}):")
    print(f"    Transport: {latest_data['Transport']:,.0f} ton CO2")
    print(f"    Power Industry: {latest_data['Power Industry']:,.0f} ton CO2")
    print(f"    Kişi başına toplam: {latest_data['Total CO2/cap']:.2f} ton CO2")
    
    print(f"  Tarihsel ortalamalar:")
    print(f"    Transport: {summary['avg_transport']:,.0f} ton CO2")
    print(f"    Power Industry: {summary['avg_power']:,.0f} ton CO2")
    print(f"    Kişi başına: {summary['avg_total_per_capita']:.2f} ton CO2")
    
    return summary

def save_processed_data(df, output_path="data/turkiye_emisyon_temiz.csv"):
    """
    Temizlenmiş veriyi kaydet
    """
    print(f"\n💾 TEMİZLENMİŞ VERİ KAYDEDİLİYOR: {output_path}")
    
    # Çıktı klasörünü oluştur
    Path(output_path).parent.mkdir(exist_ok=True)
    
    # Veriyi kaydet
    df.to_csv(output_path, index=False)
    print(f"✅ Veri başarıyla kaydedildi!")
    
    return output_path

def visualize_emissions(data_sets, save_plots=True):
    """
    Emisyonları görselleştir
    """
    print("\n📊 EMİSYONLAR GÖRSELLEŞTİRİLİYOR...")
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. Transport emisyonları
    ax1.plot(data_sets['years'], data_sets['transport'], 'b-', linewidth=2)
    ax1.set_title('Türkiye Transport Emisyonları (1970-2024)', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Yıl', fontsize=12)
    ax1.set_ylabel('Emisyon (ton CO2)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. Power Industry emisyonları
    ax2.plot(data_sets['years'], data_sets['power'], 'r-', linewidth=2)
    ax2.set_title('Türkiye Power Industry Emisyonları (1970-2024)', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Yıl', fontsize=12)
    ax2.set_ylabel('Emisyon (ton CO2)', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    # 3. Toplam emisyonlar (kişi başına)
    ax3.plot(data_sets['years'], data_sets['total'], 'g-', linewidth=2)
    ax3.set_title('Türkiye Kişi Başına Toplam CO2 Emisyonları (1970-2024)', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Yıl', fontsize=12)
    ax3.set_ylabel('Emisyon (ton CO2/kapita)', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.tick_params(axis='x', rotation=45)
    
    # 4. Karşılaştırmalı grafik
    ax4.plot(data_sets['years'], data_sets['transport'], 'b-', label='Transport', linewidth=2)
    ax4.plot(data_sets['years'], data_sets['power'], 'r-', label='Power Industry', linewidth=2)
    ax4.set_title('Türkiye Emisyon Karşılaştırması (1970-2024)', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Yıl', fontsize=12)
    ax4.set_ylabel('Emisyon (ton CO2)', fontsize=12)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    if save_plots:
        plot_path = "data/turkiye_emisyon_grafikleri.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"📊 Grafikler kaydedildi: {plot_path}")
    
    plt.show()
    
    return fig

def main():
    """
    Ana fonksiyon
    """
    print("🇹🇷 TÜRKİYE EMİSYON VERİ İŞLEMECİSİ")
    print("=" * 60)
    
    # 1. Veriyi yükle ve temizle
    df = load_turkey_emissions()
    if df is None:
        print("❌ Veri yüklenemedi!")
        return
    
    # 2. Temizlenmiş veriyi kaydet
    save_processed_data(df)
    
    # 3. Görselleştirme için veri hazırla
    data_sets = prepare_data_for_visualization(df)
    
    # 4. Emisyon trendlerini hesapla
    trends = calculate_emission_trends(df)
    
    # 5. Emisyon özeti oluştur
    summary = create_emission_summary(df)
    
    # 6. Görselleştir
    try:
        fig = visualize_emissions(data_sets)
        print("📊 Görselleştirme tamamlandı!")
    except Exception as e:
        print(f"⚠️ Görselleştirme hatası: {e}")
    
    print(f"\n✅ VERİ İŞLEME TAMAMLANDI!")
    print(f"📊 Toplam {len(df)} kayıt işlendi")
    print(f"📅 Tarih aralığı: {df['Category'].min()}-{df['Category'].max()}")
    
    return df, trends, summary

if __name__ == "__main__":
    df, trends, summary = main()
