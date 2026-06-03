"""
EDGAR Power Industry verilerine dayalı elektrik katsayısı hesaplayıcı
Türkiye'nin tahmini nüfusuna (85M) bölerek kişi başına düşen güncel emisyonu hesaplar
"""

import pandas as pd
from pathlib import Path
import constants

def load_edgar_power_data():
    """
    EDGAR CO2-emissions-by-sector.csv dosyasını yükle
    """
    print("⚡ EDGAR POWER INDUSTRY VERİSİ YÜKLENİYOR...")
    
    # EDGAR veri dosyasını ara
    edgar_path = Path("data/CO2-emissions-by-sector.csv")
    if not edgar_path.exists():
        print(f"❌ EDGAR veri dosyası bulunamadı: {edgar_path}")
        print("💡 Alternatif: data/turkiye_emisyon.csv dosyasını kullanıyor")
        return None
    
    try:
        df = pd.read_csv(edgar_path)
        print(f"✅ EDGAR verisi yüklendi: {len(df)} kayıt")
        return df
    except Exception as e:
        print(f"❌ EDGAR verisi okunamadı: {e}")
        return None

def calculate_turkey_electricity_factor():
    """
    Türkiye'ye özel elektrik katsayısını hesapla
    EDGAR Power Industry verisi + Türkiye nüfusu
    """
    print("🇹🇷 TÜRKİYE ÖZEL ELEKTRİK KATSAYISI HESAPLANIYOR...")
    
    # EDGAR verisini yükle
    df_edgar = load_edgar_power_data()
    if df_edgar is None:
        return None
    
    # Türkiye Power Industry verilerini bul
    turkey_power_data = df_edgar[df_edgar['Country'] == 'Turkey']
    
    if len(turkey_power_data) == 0:
        print("❌ Türkiye için EDGAR verisi bulunamadı")
        return None
    
    print(f"📊 Türkiye Power Industry verisi: {len(turkey_power_data)} kayıt")
    print(f"📅 Tarih aralığı: {turkey_power_data['Year'].min()} - {turkey_power_data['Year'].max()}")
    
    # En son yılın verisini al
    latest_data = turkey_power_data[turkey_power_data['Year'] == turkey_power_data['Year'].max()]
    
    if 'Power Industry' not in latest_data:
        print("❌ 'Power Industry' sütunu bulunamadı")
        return None
    
    # En son yılın emisyon değeri (ton CO2)
    power_emissions_ton = latest_data['Power Industry']
    
    # Türkiye'nin tahmini nüfusu (85 milyon)
    turkey_population = constants.TURKIYE_NUFUS
    
    # Türkiye'nin tahmini elektrik tüketimi (kWh/yıl)
    # Dünya Bankası ve EPDK verilerine dayalı tahmin
    turkey_electricity_consumption = 300_000_000_000  # 300 milyar kWh/yıl
    
    # Elektrik katsayısını hesapla (kg CO2/kWh)
    electricity_factor = (power_emissions_ton * 1000) / turkey_electricity_consumption
    
    print(f"📈 HESAPLAMA BİLGİLERİ:")
    print(f"  Son yıl Power Industry emisyonu: {power_emissions_ton:,.0f} ton CO2")
    print(f"  Türkiye nüfusu: {turkey_population:,} kişi")
    print(f"  Tahmini elektrik tüketimi: {turkey_electricity_consumption:,} kWh/yıl")
    print(f"  Hesaplanan elektrik katsayısı: {electricity_factor:.6f} kg CO2/kWh")
    
    # Karşılaştırma
    etkb_factor = 0.469  # Mevcut ETKEB katsayısı
    print(f"  Mevcut ETKEB katsayısı: {etkb_factor:.6f} kg CO2/kWh")
    print(f"  Fark: {(electricity_factor - etkb_factor):+.6f} kg CO2/kWh")
    print(f"  Değişim oranı: {((electricity_factor / etkb_factor - 1) * 100):+.1f}%")
    
    return {
        'edgar_factor': electricity_factor,
        'etkb_factor': etkb_factor,
        'power_emissions_ton': power_emissions_ton,
        'turkey_population': turkey_population,
        'electricity_consumption_kwh': turkey_electricity_consumption,
        'difference_percent': ((electricity_factor / etkb_factor - 1) * 100),
        'data_source': 'EDGAR Power Industry + Türkiye nüfus tahmini',
        'year': latest_data['Year']
    }

def save_electricity_factors(electricity_data, output_path="data/turkiye_elektrik_katsayilari.csv"):
    """
    Elektrik katsayılarını kaydet
    """
    print(f"💾 ELEKTRİK KATSAYILARI KAYDEDİLİYOR: {output_path}")
    
    # Çıktı DataFrame oluştur
    df_output = pd.DataFrame([{
        'kaynak': ['EDGAR Power Industry', 'ETKEB Mevcut'],
        'katsayi_kg_per_kwh': [electricity_data['edgar_factor'], electricity_data['etkb_factor']],
        'fark_yuzde': [electricity_data['difference_percent']],
        'power_emisyon_ton': [electricity_data['power_emissions_ton']],
        'nufus': [electricity_data['turkey_population']],
        'elektrik_tuketim_kwh': [electricity_data['electricity_consumption_kwh']],
        'yil': [electricity_data['year']],
        'aciklama': [
            f"EDGAR verisi ile hesaplanan {electricity_data['edgar_factor']:.6f} kg CO2/kWh",
            f"ETKEB mevcut {electricity_data['etkb_factor']:.6f} kg CO2/kWh",
            f"Fark: %{electricity_data['difference_percent']:.1f}"
        ]
    }])
    
    # Kaydet
    Path(output_path).parent.mkdir(exist_ok=True)
    df_output.to_csv(output_path, index=False)
    print(f"✅ Elektrik katsayıları başarıyla kaydedildi!")
    
    return output_path

def main():
    """
    Ana fonksiyon
    """
    print("⚡ EDGAR POWER INDUSTRY VERİLERİYLE ELEKTRİK KATSAYISI")
    print("=" * 60)
    
    # Elektrik katsayısını hesapla
    electricity_data = calculate_turkey_electricity_factor()
    
    if electricity_data is None:
        print("❌ Elektrik katsayısı hesaplanamadı!")
        return None
    
    # Sonuçları kaydet
    output_path = save_electricity_factors(electricity_data)
    
    print(f"\n✅ ELEKTRİK KATSAYISI HESAPLAMA TAMAMLANDI!")
    print(f"📊 EDGAR katsayısı: {electricity_data['edgar_factor']:.6f} kg CO2/kWh")
    print(f"📊 ETKEB katsayısı: {electricity_data['etkb_factor']:.6f} kg CO2/kWh")
    print(f"📈 Fark: %{electricity_data['difference_percent']:.1f}")
    print(f"💾 Çıktı dosyası: {output_path}")
    
    return electricity_data

if __name__ == "__main__":
    electricity_data = main()
