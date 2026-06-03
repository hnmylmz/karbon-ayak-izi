"""
TÜRKİYE'YE ÖZEL KARBON EMİSYON SABİTLERİ
Gerçek Türkiye verilerine dayalı hesaplanmış değerler
"""

from typing import Dict

# Türkiye nüfus ve temel veriler (2024 tahmini)
TURKIYE_NUFUS = 85_000_000  # 85 milyon
HANE_SAYISI = 25_000_000  # 25 milyon hane
CALISAN_NUFUS = 32_000_000  # 32 milyon çalışan

# 2024 yılı gerçek Türkiye emisyon verileri (ton CO2)
TURKIYE_2024_TRANSPORT = 99_286_300  # Ulaşım sektörü
TURKIYE_2024_POWER = 140_913_000     # Enerji sektörü  
TURKIYE_2024_BUILDINGS = 72_687_100  # Binalar sektörü
TURKIYE_2024_TOTAL = 312_886_400      # Toplam emisyon

# KİŞİ BAŞINA YILLIK EMİSYON LİMİTLERİ (gerçek Türkiye verisi)
KIŞI_BASINA_YILLIK_LIMITLER: Dict[str, float] = {
    "transport": TURKIYE_2024_TRANSPORT / TURKIYE_NUFUS,      # 1.17 ton CO2/kisi/yıl
    "power": TURKIYE_2024_POWER / HANE_SAYISI,            # 5.64 ton CO2/hane/yıl
    "residential": TURKIYE_2024_BUILDINGS / HANE_SAYISI,   # 2.91 ton CO2/hane/yıl
    "total": TURKIYE_2024_TOTAL / TURKIYE_NUFUS,          # 3.68 ton CO2/kisi/yıl
}

# KİŞİ BAŞINA GÜNLÜK EMİSYON LİMİTLERİ
KIŞI_BASINA_GUNLUK_LIMITLER: Dict[str, float] = {
    "transport": KIŞI_BASINA_YILLIK_LIMITLER["transport"] / 365,      # 3.21 kg CO2/kisi/gün
    "power": KIŞI_BASINA_YILLIK_LIMITLER["power"] / 365,            # 15.45 kg CO2/hane/gün
    "residential": KIŞI_BASINA_YILLIK_LIMITLER["residential"] / 365,   # 7.97 kg CO2/hane/gün
    "total": KIŞI_BASINA_YILLIK_LIMITLER["total"] / 365,            # 10.08 kg CO2/kisi/gün
}

# HAFTALIK EMİSYON LİMİTLERİ
HAFTALIK_LIMITLER: Dict[str, float] = {
    "transport": KIŞI_BASINA_GUNLUK_LIMITLER["transport"] * 7,      # 22.47 kg CO2/kisi/hafta
    "power": KIŞI_BASINA_GUNLUK_LIMITLER["power"] * 7,            # 108.15 kg CO2/hane/hafta
    "residential": KIŞI_BASINA_GUNLUK_LIMITLER["residential"] * 7,   # 55.79 kg CO2/hane/hafta
    "total": KIŞI_BASINA_GUNLUK_LIMITLER["total"] * 7,            # 70.56 kg CO2/kisi/hafta
}

# EMİSYON SEVİYE SINIFLANDIRMALARI
EMISYON_SEVIYELERI: Dict[str, float] = {
    "cok_dusuk": 0.5,      # Türkiye ortalamasının %50'si altı
    "dusuk": 0.8,          # Türkiye ortalamasının %80'i altı  
    "normal": 1.2,         # Türkiye ortalamasına yakın (%120)
    "yuksek": 1.8,        # Türkiye ortalamasının %180'i üstü
    "cok_yuksek": 2.5,     # Türkiye ortalamasının %250'i üstü
}

# HAFTALIK EMİSYON EŞİK DEĞERLERİ
HAFTALIK_ESIK_DEGERLERI: Dict[str, float] = {
    "cok_dusuk": HAFTALIK_LIMITLER["total"] * EMISYON_SEVIYELERI["cok_dusuk"],      # 35.28 kg/hafta
    "dusuk": HAFTALIK_LIMITLER["total"] * EMISYON_SEVIYELERI["dusuk"],          # 56.45 kg/hafta
    "normal": HAFTALIK_LIMITLER["total"] * EMISYON_SEVIYELERI["normal"],         # 84.67 kg/hafta
    "yuksek": HAFTALIK_LIMITLER["total"] * EMISYON_SEVIYELERI["yuksek"],         # 127.01 kg/hafta
    "cok_yuksek": HAFTALIK_LIMITLER["total"] * EMISYON_SEVIYELERI["cok_yuksek"],   # 176.40 kg/hafta
}

# İYİLEŞTİRME HEDEF ORANLARI
IYILESTIRME_HEDEFLERI: Dict[str, float] = {
    "kisa_vade": 0.10,      # 3 ayda %10 azaltım
    "orta_vade": 0.25,       # 6 ayda %25 azaltım  
    "uzun_vade": 0.50,      # 12 ayda %50 azaltım
    "surdurulebilir": 0.75,  # Sürdürülebilir seviye (%75 azaltım)
}

# TÜRKİYE ÖZEL KATSAYILAR (gerçek verilere dayalı)
TURKIYE_ORTALAMA_KATSAYILARI: Dict[str, float] = {
    "elektrik_kwh_per_ay": 250,      # Ortalama hane elektrik tüketimi
    "dogalgaz_m3_per_ay": 80,       # Ortalama hane doğalgaz tüketimi
    "ulasim_km_per_hafta": 150,     # Ortalama kişi ulaşım mesafesi
    "araba_sahibi_orani": 0.55,     # Araç sahipliği oranı
    "toplu_tasima_orani": 0.35,    # Toplu taşıma kullanım oranı
}

# GIDA EMİSYON KATSAYILARI (Oxford ve IPCC verileri)
GIDA_EMISYON_KATSAYILARI: Dict[str, float] = {
    # Kırmızı Et
    "kirmizi_et": 27.0,         # kg CO2/kg (Oxford ayarlı)
    "dana_eti": 29.7,           # kg CO2/kg (Türkiye'ye özgü)
    "koyun_eti": 24.0,        # kg CO2/kg
    "sığir_eti": 27.0,         # kg CO2/kg
    
    # Beyaz Et ve Diğer
    "tavuk_eti": 6.0,          # kg CO2/kg (Oxford ayarlı)
    "balik": 6.0,               # kg CO2/kg (Akdeniz avantajı)
    "yumurta": 4.5,             # kg CO2/kg (Türkiye'ye özgü)
    "sut_ve_urunleri": 3.2,     # kg CO2/kg (Yerel üretim)
    "peynir": 12.8,             # kg CO2/kg (Geleneksel peynir)
    
    # Bitkisel Ürünler
    "bugday": 1.4,              # kg CO2/kg (Türkiye buğdayı)
    "pirinc": 3.2,              # kg CO2/kg (İthal pirinç)
    "misir": 1.0,               # kg CO2/kg
    "arpa": 1.2,                # kg CO2/kg
    "sebzeler": 0.4,            # kg CO2/kg (Yerel üretim)
    "domates": 0.4,             # kg CO2/kg
    "salatalik": 0.3,          # kg CO2/kg
    "kuru_baklagiller": 1.2,    # kg CO2/kg
    "meyveler": 0.5,            # kg CO2/kg (Akdeniz iklimi)
    "elma": 0.3,               # kg CO2/kg
    "portakal": 0.4,            # kg CO2/kg
    "muz": 0.9,                # kg CO2/kg (İthal)
    
    # Yağlar ve Şekerler
    "zeytinyagi": 3.5,           # kg CO2/kg (Ege bölgesi)
    "aycicek_yagi": 3.2,       # kg CO2/kg
    "sogan_yagi": 4.0,          # kg CO2/kg
    "seker": 1.6,               # kg CO2/kg (beyaz şeker)
    
    # İçecekler
    "kahve": 16.5,              # kg CO2/kg (Türk kahvesi)
    "cay": 4.8,                # kg CO2/kg (Türk çayı)
    "meyve_suyu": 2.0,         # kg CO2/kg
    "alkol": 2.3,               # kg CO2/kg (genel)
    "kola": 3.5,                # kg CO2/kg (gazlı içecekler)
    
    # İşlenmiş Gıdalar
    "ekmek": 0.9,              # kg CO2/kg (yerel un)
    "makarna": 1.0,             # kg CO2/kg
    "pilav": 1.1,               # kg CO2/kg
    "biskuvi": 3.5,            # kg CO2/kg
    "cikolata": 4.0,           # kg CO2/kg
    "dondurma": 2.8,             # kg CO2/kg
    "konserve": 1.5,             # kg CO2/kg
    "tursu": 1.8,               # kg CO2/kg (geleneksel)
    
    # Fast Food ve Restoran
    "hamburger": 8.5,           # kg CO2/kg
    "pizza": 6.0,                # kg CO2/kg
    "doner": 6.1,               # kg CO2/kg (Türk döner)
    "kebap": 9.0,               # kg CO2/kg (Türk kebap)
    "lahmacun": 6.5,            # kg CO2/kg
    "kokorec": 7.8,             # kg CO2/kg
    "corba": 2.0,               # kg CO2/kg
    "salata": 1.5,              # kg CO2/kg
}

# TÜRKİYE ÖZEL ULAŞIM KATSAYILARI (dolmuş/minibüs ayrımı)
TURKIYE_ULASIM_KATSAYILARI: Dict[str, float] = {
    # Standart katsayılar
    "otobus_kg_per_km": 0.089,   # Yeni filo
    "metro_kg_per_km": 0.035,     # Elektrikli
    "otomobil_kg_per_km": 0.192,  # Standart
    "ucak_kg_per_km": 0.255,    # Türk Hava Yolları
    "tren_kg_per_km": 0.060,     # TCDD
    "gemi_kg_per_km": 0.095,     # Liman operasyonları
    
    # Türkiye'ye özgü dolmuş/minibüs katsayıları
    "dolmus_kg_per_km": 0.138,   # %20 artış (eski filolar)
    "minibus_kg_per_km": 0.156,   # %25 artış (daha eski filolar)
    "taksi_kg_per_km": 0.192,    # Yüksek boşta çalışma
    
    # Elektrik katsayısı (EDGAR Power Industry verisi)
    "elektrik_kg_per_kwh_turkiye": 0.469,  # Mevcut ETKEB
    "elektrik_kg_per_kwh_edgar": 0.467,  # EDGAR hesaplı
}

# VERİ KALİTESİ KONTROLLERİ
VERI_KALITE_KONTROLLERI: Dict[str, float] = {
    "min_veri_gereklilik": 0.8,   # En az %80 veri tamamlanmalı
    "max_aykiri_deger_orani": 0.05, # Maksimum %5 aykırı değer
    "zaman_serisi_tutarliligi": 0.9, # Zaman serisi tutarlılığı
    "cografi_denge": 0.15,        # Coğrafi dağılım dengesi
}

# KULLANICI PROFİLİ KALİBRASYON FAKTÖRLERİ
KULLANICI_PROFIL_KALIBRASYONU: Dict[str, float] = {
    "dusuk_emisyonlu": 0.7,      # Türkiye ortalamasının %70'i
    "ortalama_emisyonlu": 1.0,    # Türkiye ortalaması
    "yuksek_emisyonlu": 1.3,     # Türkiye ortalamasının %130'u
    "cok_yuksek_emisyonlu": 1.6,  # Türkiye ortalamasının %160'u
}

