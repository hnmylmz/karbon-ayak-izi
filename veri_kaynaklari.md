# 🌍 Karbon Ayak İzi Veri Kaynakları

## 📊 Mevcut Durum
- **Veri Seti:** `archive/sentetik/sentetik_tr_ulasim_haftalik_temiz.csv` (2700 kayıt)
- **Kapsam:** 120 kullanıcı × 20 hafta + 300 ek kayıt
- **Özellikler:** Ulaşım verileri, şehir bilgisi, CO2 emisyonları

## 🎯 Ek Veri Kaynakları

### 1. 🇹🇷 Türkiye Resmi Veri Kaynakları
- **TÜİK (Türkiye İstatistik Kurumu)**
  - Ulaşım istatistikleri
  - Enerji tüketim verileri
  - Bölgesel karbon emisyon raporları
  
- **EPDK (Enerji Piyasası Düzenleme Kurumu)**
  - Elektrik tüketim istatistikleri
  - Yenilenebilir enerji oranları
  - Şehir bazlı enerji verileri

- **Çevre, Şehircilik ve İklim Değişikliği Bakanlığı**
  - Ulusal sera gazı envanteri
  - Karbon salım raporları
  - İklim değişikliği verileri

### 2. 🌍 Uluslararası Veri Kaynakları
- **World Bank Open Data**
  - CO2 emissions (kt)
  - Energy consumption data
  - Transportation statistics

- **IEA (International Energy Agency)**
  - Country-level energy data
  - Emission factors database
  - Transportation sector analysis

- **European Environment Agency**
  - Emission factors database
  - Carbon footprint calculators
  - Best practice datasets

### 3. 🏢 Sektörel Veri Kaynakları
- **Ulaşım Sektörü**
  - İETT (İstanbul Elektrik Tramvay ve Tünel) verileri
  - Belediye toplu taşıma verileri
  - Otopark ve araç sayım verileri

- **Enerji Sektörü**
  - Dağıtım şirketleri verileri
  - Şebeke kayıp oranları
  - Yenilenebilir enerji üretim verileri

### 4. 📱 Gerçek Zamanlı Veri Kaynakları
- **API'ler**
  - OpenWeatherMap (hava durumu ve enerji)
  - Google Maps API (ulaşım mesafeleri)
  - Carbon Intensity API (elektrik karbon yoğunluğu)

### 5. 🎓 Akademik ve Araştırma Verileri
- **Kaggle Datasets**
  - Carbon emission prediction datasets
  - Transportation behavior studies
  - Energy consumption patterns

- **Research Papers**
  - Turkish transportation emission studies
  - Urban carbon footprint research
  - Behavioral change impact studies

## 🔧 Veri Toplama Stratejileri

### Kısa Vade (1-3 ay)
1. **TÜİK verilerini entegre et**
   - Şehir bazlı ulaşım istatistikleri
   - Aylık enerji tüketim verileri

2. **Mevcut veriyi zenginleştir**
   - Mevsimsel faktörler ekle
   - Tatil günleri etkisini dahil et
   - COVID-19 etkisini modelle

### Orta Vade (3-6 ay)
1. **API entegrasyonu**
   - Gerçek zamanlı enerji verileri
   - Hava durumu etkileri
   - Ulaşım yoğunluk verileri

2. **Kullanıcı veri toplama**
   - Mobil uygulama entegrasyonu
   - GPS tablı ulaşım takibi
   - Anket verileri

### Uzun Vade (6-12 ay)
1. **Makine öğrenmesi veri üretimi**
   - Transfer learning uygulamaları
   - Sentetik veri artırımı
   - Gerçek veri ile sentetik veri birleştirme

## 📋 Veri Kalitesi Kontrol Listesi
- [ ] Eksik veri oranı < 5%
- [ ] Aykırı değerler temizlenmiş
- [ ] Zaman serisi tutarlılığı
- [ ] Coğrafi dağılım dengesi
- [ ] Mevsimsel varyasyonlar
- [ ] Güncellik (son 6 ay)

## 🚀 Önerilen Eylemler
1. **Mevcut veriyi kullanarak model eğit**
2. **TÜİK API'sini entegre et**
3. **Gerçek kullanıcı verisi toplamaya başla**
4. **Veri kalitesini düzenli izle**
5. **Aylık veri güncelleme döngüsü kur**

## 📞 İletişim ve Kaynaklar
- TÜİK: https://www.tuik.gov.tr/
- EPDK: https://www.epdk.gov.tr/
- Çevre Bakanlığı: https://www.csb.gov.tr/
- World Bank: https://data.worldbank.org/
- IEA: https://www.iea.org/data-and-statistics
