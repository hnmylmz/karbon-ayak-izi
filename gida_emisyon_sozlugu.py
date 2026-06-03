"""
Gıda emisyon faktörleri sözlüğü
IPCC ve Oxford Üniversitesi verilerine dayalı
Türkiye'ye özgü gıda kategorileri içerir
"""

# IPCC Gıda Emisyon Faktörleri (kg CO2e/kg ürün veya özel birim faktörleri)
IPCC_GIDA_KATSAYILARI = {
    # Kırmızı Et
    "sığır_eti": 27.0,        # Sığır eti
    "dana_eti": 27.0,         # Dana eti
    "koyun_eti": 24.0,        # Koyun eti
    "tavuk_eti": 6.9,         # Tavuk eti
    "balik": 6.0,              # Balık ve su ürünleri
    "yumurta": 0.27,           # Yumurta (adet başına ortalama emisyon)
    "giyim": 5.0,              # Giyim (adet başına ortalama emisyon)
    "elektronik": 0.05,        # Elektronik (saat başına ortalama kullanım emisyonu)
    "sut_ve_urunleri": 3.2,    # Süt ve süt ürünleri
    "peynir": 13.5,            # Peynir
    
    # Bitkisel Ürünler
    "bugday": 1.4,             # Buğday
    "pirinc": 2.7,             # Pirinç
    "mısır": 1.0,              # Mısır
    "arpa": 1.2,               # Arpa
    "sebzeler": 0.4,           # Genel sebze ortalaması
    "domates": 0.4,            # Domates
    "salatalik": 0.3,          # Salatalık sebzeler
    "kuru_baklagiller": 1.2,    # Kuru baklagiller
    "meyveler": 0.5,           # Genel meyve ortalaması
    "elma": 0.3,               # Elma
    "portakal": 0.4,            # Portakal
    "muz": 0.9,                # Muz
    
    # Yağlar ve Şekerler
    "zeytinyagi": 5.9,          # Zeytinyağı
    "aycicek_yagi": 3.2,       # Ayçiçek yağı
    "sogan_yagi": 4.0,          # Soğan yağı
    "seker": 1.6,               # Şeker (beyaz şeker)
    
    # İçecekler
    "kahve": 15.0,             # Kahve (kavrulmuş)
    "cay": 8.0,                # Çay (kavrulmuş)
    "meyve_suyu": 2.0,         # Meyve suyu
    "alkol": 2.3,               # Alkol (genel)
    "kola": 3.5,                # Kola ve gazlı içecekler
    
    # İşlenmiş Gıdalar
    "ekmek": 0.9,              # Ekmek (beyaz)
    "makarna": 1.0,             # Makarna
    "pilav": 1.1,               # Pilav
    "biskuvi": 3.5,            # Bisküvi
    "cikolata": 4.0,           # Çikolata
    "dondurma": 2.8,             # Dondurulmuş ürünler
    "konserve": 1.5,             # Konserve ürünler
    "turşu": 1.8,               # Turşu ve salamura ürünler
    
    # Fast Food ve Restoran
    "hamburger": 8.5,           # Hamburger
    "pizza": 6.0,                # Pizza
    "doner": 7.2,               # Döner
    "kebap": 9.0,               # Kebap
    "lahmacun": 6.5,            # Lahmacun
    "kokorec": 7.8,             # Köfte
    "corba": 2.0,                # Çorba
    "salata": 1.5,              # Salata
}

# Oxford Üniversitesi Gıda Emisyon Verileri (Türkiye'ye özgü ayarlamalar)
OXFORD_GIDA_DUZELTMELERI = {
    # Türkiye'de yaygın gıdalar için emisyon ayarları
    "sığır_eti": 1.0,         # Türkiye'de daha az tüketim
    "dana_eti": 1.1,           # Türkiye'de daha fazla tüketim
    "tavuk_eti": 0.8,          # Türkiye'de daha yaygın
    "balik": 0.7,               # Akdeniz kıyısı avantajı
    "yumurta": 0.9,            # Yerel üretim avantajı
    "giyim": 1.0,              # Adet bazlı giyim emisyonu için düzenleme
    "elektronik": 1.0,         # Saat bazlı elektronik emisyonu için düzenleme
    "sut_ve_urunleri": 0.85,   # Yerel süt üretimi
    "peynir": 0.95,            # Geleneksel peynir üretimi
    
    "bugday": 0.8,             # Türkiye buğday üretimi
    "pirinc": 1.2,              # İthal pirinç
    "sebzeler": 0.7,           # Yerel sebze üretimi
    "meyveler": 0.8,           # Akdeniz iklimi avantajı
    "zeytinyagi": 0.6,           # Ege bölgesi zeytinyağı
    "kahve": 1.1,              # Türk kahvesi kültürü
    "cay": 0.6,                # Türk çayı kültürü
    "ekmek": 0.9,              # Yerel un üretimi
    "doner": 0.85,             # Türk döner kültürü
    "kebap": 0.9,              # Türk kebap kültürü
}

# Türkiye'ye Özgü Gıda Tüketim Ortalamaları (kg/kişi/hafta)
TURKIYE_GIDA_TUKETIM_ORTALAMALARI = {
    # TÜİK ve anketa verilerine dayalı
    "sığır_eti": 0.15,         # kg/hafta
    "dana_eti": 0.25,           # kg/hafta
    "tavuk_eti": 0.40,         # kg/hafta
    "balik": 0.20,               # kg/hafta
    "yumurta": 0.30,            # kg/hafta (adet)
    "sut_ve_urunleri": 1.5,     # litre/hafta
    "peynir": 0.25,             # kg/hafta
    
    "bugday": 0.50,             # kg/hafta
    "pirinc": 0.15,             # kg/hafta
    "sebzeler": 1.0,             # kg/hafta
    "meyveler": 0.80,             # kg/hafta
    
    "zeytinyagi": 0.10,           # litre/hafta
    "kahve": 0.20,               # kg/hafta
    "cay": 0.15,                # kg/hafta
    
    "ekmek": 0.50,             # kg/hafta
    "makarna": 0.15,             # kg/hafta
    "pilav": 0.20,               # kg/hafta
    
    "hamburger": 0.10,           # adet/hafta
    "pizza": 0.08,               # adet/hafta
    "doner": 0.05,               # porsiyon/hafta
    "kebap": 0.03,               # porsiyon/hafta
}

# Gıda Kategorileri
GIDA_KATEGORILERI = {
    "et_urunleri": [
        "sığır_eti", "dana_eti", "koyun_eti", "tavuk_eti"
    ],
    "sut_urunleri": [
        "yumurta", "sut_ve_urunleri", "peynir"
    ],
    "bitkisel_urunler": [
        "bugday", "pirinc", "mısır", "arpa", "sebzeler", "kuru_baklagiller"
    ],
    "meyveler": [
        "elma", "portakal", "muz", "meyveler"
    ],
    "yaglar": [
        "zeytinyagi", "aycicek_yagi", "sogan_yagi"
    ],
    "icecekler": [
        "kahve", "cay", "meyve_suyu", "alkol", "kola"
    ],
    "islenmis_gidalar": [
        "ekmek", "makarna", "pilav", "biskuvi", "cikolata", "dondurma", "konserve", "turşu"
    ],
    "fast_food": [
        "hamburger", "pizza", "doner", "kebap", "lahmacun", "kokorec", "corba", "salata"
    ],
}

def get_turkiye_gida_faktoru(gida_adi):
    """
    Türkiye'ye özgü gıda emisyon faktörünü hesapla
    IPCC + Oxford ayarlamaları + Türkiye ortalamaları
    """
    if gida_adi not in IPCC_GIDA_KATSAYILARI:
        return 0.0  # Bilinmeyen gıda
    
    # Temel IPCC faktörü
    ipcc_faktor = IPCC_GIDA_KATSAYILARI[gida_adi]
    
    # Oxford ayarlaması
    oxford_ayar = OXFORD_GIDA_DUZELTMELERI.get(gida_adi, 1.0)
    
    # Türkiye'ye özgü faktör
    turkiye_faktor = ipcc_faktor * oxford_ayar
    
    return round(turkiye_faktor, 3)

def hesapla_gida_emisyonlari(gida_verileri):
    """
    Gıda verilerinden emisyonları hesapla
    gida_verileri: {gida_adi: miktar, ...}
    """
    toplam_emisyon = 0.0
    gida_kalemleri = {}
    
    for gida_adi, miktar in gida_verileri.items():
        if miktar <= 0:
            continue
            
        faktor = get_turkiye_gida_faktoru(gida_adi)
        emisyon = miktar * faktor
        
        gida_kalemleri[gida_adi] = {
            "miktar": miktar,
            "faktor": faktor,
            "emisyon": emisyon
        }
        
        toplam_emisyon += emisyon
    
    return {
        "toplam_emisyon": toplam_emisyon,
        "kalemler": gida_kalemleri,
        "kaynak": "IPCC + Oxford + Türkiye ayarlamaları"
    }

def get_gida_kategori_onerileri(kategori_adi):
    """
    Gıda kategorisine göre emisyon azaltım önerileri
    """
    oneriler = {
        "et_urunleri": [
            "Kırmızı et tüketimini azaltıp beyaz et ve balığa yönel",
            "Haftada 1 gün vejetaryen gün belirle",
            "Yerel ve organik üreticileri tercih et"
        ],
        "sut_urunleri": [
            "Bitkisel süt alternatiflerini deney",
            "Yerel üreticilerden satın al",
            "Ambalajsız ürünler seç"
        ],
        "bitkisel_urunler": [
            "Mevsim sebzelerini tercih et",
            "Gıda israfını azalt",
            "Kendi bahçende üretmeyi düşün"
        ],
        "meyveler": [
            "Mevsim meyvelerini tüket",
            "Yerel pazarları destekle",
            "Kuru meyve kışın tüket"
        ],
        "yaglar": [
            "Zeytinyağı gibi sağlıklı yağlar tercih et",
            "Doğal ve sızma yöntemleri kullan",
            "Miktarları azaltıp kaliteyi artır"
        ],
        "icecekler": [
            "Su tüketimini artır",
            "Şekerli içecekleri azalt",
            "Yerel üretimleri destekle"
        ],
        "islenmis_gidalar": [
            "Evde yapım tercih et",
            "Ambalajsız ve dökme ürünler seç",
            "Toplu alım yerine ihtiyaca göre al"
        ],
        "fast_food": [
            "Haftada en fazla 1 kez tüket",
            "Evde sağlıklı alternatifler hazırla",
            "Porsiyon kontrolü yap"
        ],
    }
    
    return oneriler.get(kategori_adi, [
        "Emisyonları azaltmak için tüketimini gözden geçir",
        "Daha sürdürülebilir seçimler yap",
        "Gıda israfını önle"
    ])

if __name__ == "__main__":
    print("🍽 GIDA EMİSYON FAKTÖRLERİ SÖZLÜĞÜ")
    print("=" * 50)
    
    # Test örnekleri
    test_gidalari = ["dana_eti", "tavuk_eti", "domates", "zeytinyagi", "kahve"]
    
    print("📊 TÜRKİYE'YE ÖZEL FAKTÖRLER:")
    for gida in test_gidalari:
        faktor = get_turkiye_gida_faktoru(gida)
        ortalama = TURKIYE_GIDA_TUKETIM_ORTALAMALARI.get(gida, 0.1)
        print(f"  {gida}: {faktor} kg CO2/kg (ortalama tüketim: {ortalama} kg/hafta)")
    
    # Örnek hesaplama
    ornek_gida_verileri = {
        "dana_eti": 0.25,      # 250g/hafta
        "tavuk_eti": 0.40,      # 400g/hafta
        "domates": 0.50,        # 500g/hafta
        "zeytinyagi": 0.10,      # 100ml/hafta
        "kahve": 0.20,          # 200g/hafta
    }
    
    sonuc = hesapla_gida_emisyonlari(ornek_gida_verileri)
    
    print(f"\n📈 ÖRNEK HESAPLAMA:")
    print(f"Toplam gıda emisyonu: {sonuc['toplam_emisyon']:.3f} kg CO2/hafta")
    
    print("\n🎯 EMİSYON AZALTIM ÖNERİLERİ:")
    for kategori in GIDA_KATEGORILERI.keys():
        oneriler = get_gida_kategori_onerileri(kategori)
        print(f"\n{kategori.upper()}:")
        for i, oneri in enumerate(oneriler[:3], 1):
            print(f"  {i}. {oneri}")
    
    print(f"\n✅ Gıda emisyon sözlüğü hazır!")
