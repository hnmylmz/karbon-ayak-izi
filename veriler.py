"""
Turkiye'ye ozgu emisyon katsayilari ve yardimci fonksiyonlar.
Gerçek Türkiye verilerine dayalı güncellenmiş versiyon.
Birimler:
- Elektrik: kgCO2e / kWh
- Ulasim: kgCO2e / km
"""

from typing import Any, Dict, Mapping, Sequence, Tuple

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

import constants
import gida_emisyon_sozlugu

# Mevcut ETKB/EVCED katsayilari (constants.py'den alınıyor)
EMISSION_FACTORS_TR = {
    "electricity_kg_per_kwh": constants.TURKIYE_ULASIM_KATSAYILARI["elektrik_kg_per_kwh_edgar"],  # EDGAR Power Industry verisi
    "dogalgaz_kg_per_m3": 1.90,  # Resmi ETKB Verisi
    "dolmus_kg_per_km": constants.TURKIYE_ULASIM_KATSAYILARI["dolmus_kg_per_km"],  # Türkiye'ye özgü (%20 artış)
    "minibus_kg_per_km": constants.TURKIYE_ULASIM_KATSAYILARI["minibus_kg_per_km"],  # Türkiye'ye özgü (%25 artış)
    "otobus_kg_per_km": constants.TURKIYE_ULASIM_KATSAYILARI["otobus_kg_per_km"],  # Yeni filo
    "metro_kg_per_km": constants.TURKIYE_ULASIM_KATSAYILARI["metro_kg_per_km"],  # Elektrikli
    "otomobil_kg_per_km": constants.TURKIYE_ULASIM_KATSAYILARI["otomobil_kg_per_km"],  # Standart
    "ucak_kg_per_km": constants.TURKIYE_ULASIM_KATSAYILARI["ucak_kg_per_km"],  # Türk Hava Yolları
    "taksi_kg_per_km": constants.TURKIYE_ULASIM_KATSAYILARI["taksi_kg_per_km"],  # Yüksek boşta çalışma
    "tren_kg_per_km": constants.TURKIYE_ULASIM_KATSAYILARI["tren_kg_per_km"],  # TCDD
    "gemi_kg_per_km": constants.TURKIYE_ULASIM_KATSAYILARI["gemi_kg_per_km"],  # Liman operasyonları
}

# Türkiye ortalamasina gore kalibre edilmis katsayilar (constants.py'den alınıyor)
TURKIYE_ORTALAMA_KATSAYILARI = {
    "electricity_kg_per_kwh": constants.TURKIYE_ORTALAMA_KATSAYILARI["elektrik_kwh_per_ay"] / 30,  # Aylık ortalama
    "dogalgaz_kg_per_m3": constants.TURKIYE_ORTALAMA_KATSAYILARI["dogalgaz_m3_per_ay"] / 30,   # Aylık ortalama
    "ulasim_kg_per_km": (constants.KIŞI_BASINA_GUNLUK_LIMITLER["transport"] * 7) / constants.TURKIYE_ORTALAMA_KATSAYILARI["ulasim_km_per_hafta"],  # Türkiye ortalaması
}

# Gıda emisyon katsayıları (Oxford ve IPCC verileri)
GIDA_EMISYON_KATSAYILARI = constants.GIDA_EMISYON_KATSAYILARI

class RequestCleaner(BaseEstimator, TransformerMixin):
    def __init__(self, feature_names: Sequence[str], fill_value: float = 0.0) -> None:
        self.feature_names = list(feature_names)
        self.fill_value = fill_value

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if isinstance(X, dict):
            rows = [X]
        else:
            rows = list(X)

        cleaned_rows = []
        for row in rows:
            cleaned_row = [self._to_float(row.get(feature, self.fill_value)) for feature in self.feature_names]
            cleaned_rows.append(cleaned_row)

        return np.array(cleaned_rows, dtype=float)

    def _to_float(self, value: Any) -> float:
        try:
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return self.fill_value
            return float(value)
        except (TypeError, ValueError):
            return self.fill_value


def normalize_girdi(girdi: Mapping[str, Any]) -> Dict[str, float]:
    """Eksik/hatalı degerleri 0.0'a cevirip sayisal veri doner."""

    def to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    return {
        "electricity_kwh": to_float(girdi.get("electricity_kwh", 0)),
        "dogalgaz_m3": to_float(girdi.get("dogalgaz_m3", 0)),
        "dolmus_km": to_float(girdi.get("dolmus_km", 0)),
        "minibus_km": to_float(girdi.get("minibus_km", 0)),
        "otobus_km": to_float(girdi.get("otobus_km", 0)),
        "metro_km": to_float(girdi.get("metro_km", 0)),
        "otomobil_km": to_float(girdi.get("otomobil_km", 0)),
        "ucak_km": to_float(girdi.get("ucak_km", 0)),
        "taksi_km": to_float(girdi.get("taksi_km", 0)),
        "tren_km": to_float(girdi.get("tren_km", 0)),
        "gemi_km": to_float(girdi.get("gemi_km", 0)),
        # Gıda verileri
        "kirmizi_et": to_float(girdi.get("kirmizi_et", 0)),
        "beyaz_et": to_float(girdi.get("beyaz_et", 0)),
        "balik": to_float(girdi.get("balik", 0)),
        "sut_urunleri": to_float(girdi.get("sut_urunleri", 0)),
        "yumurta": to_float(girdi.get("yumurta", 0)),
        "sebzeler": to_float(girdi.get("sebzeler", 0)),
        "meyveler": to_float(girdi.get("meyveler", 0)),
        "giyim": to_float(girdi.get("giyim", 0)),
        "elektronik": to_float(girdi.get("elektronik", 0)),
    }


def hesapla_sektor_emisyonlari(
    girdi: Mapping[str, Any],
    use_turkiye_averages: bool = False,
) -> Dict[str, float]:
    """Kullanici girdilerini faktorlerle carpip kalem bazinda emisyon doner."""
    temiz = normalize_girdi(girdi)

    if use_turkiye_averages:
        factors = TURKIYE_ORTALAMA_KATSAYILARI
    else:
        factors = EMISSION_FACTORS_TR
    
    return {
        "elektrik": temiz["electricity_kwh"] * factors["electricity_kg_per_kwh"],
        "dogalgaz": temiz["dogalgaz_m3"] * factors["dogalgaz_kg_per_m3"],
        "dolmus": temiz["dolmus_km"] * factors["dolmus_kg_per_km"],
        "minibus": temiz["minibus_km"] * factors["minibus_kg_per_km"],
        "otobus": temiz["otobus_km"] * factors["otobus_kg_per_km"],
        "metro": temiz["metro_km"] * factors["metro_kg_per_km"],
        "otomobil": temiz["otomobil_km"] * factors["otomobil_kg_per_km"],
        "ucak": temiz["ucak_km"] * factors["ucak_kg_per_km"],
        "taksi": temiz["taksi_km"] * factors["taksi_kg_per_km"],
        "tren": temiz["tren_km"] * factors["tren_kg_per_km"],
        "gemi": temiz["gemi_km"] * factors["gemi_kg_per_km"],
    }


def hesapla_toplam_emisyon(
    girdi: Mapping[str, Any],
    use_turkiye_averages: bool = False,
) -> Tuple[float, Dict[str, float]]:
    """Toplam emisyonu kgCO2e cinsinden hesaplar."""
    kalemler = hesapla_sektor_emisyonlari(girdi, use_turkiye_averages)

    # Gıda emisyonlarini ekle
    gida_emisyonlari = gida_emisyon_sozlugu.hesapla_gida_emisyonlari({
        "kirmizi_et": girdi.get("kirmizi_et", 0),
        "beyaz_et": girdi.get("beyaz_et", 0),
        "balik": girdi.get("balik", 0),
        "sut_urunleri": girdi.get("sut_urunleri", 0),
        "yumurta": girdi.get("yumurta", 0),
        "sebzeler": girdi.get("sebzeler", 0),
        "meyveler": girdi.get("meyveler", 0),
        "giyim": girdi.get("giyim", 0),
        "elektronik": girdi.get("elektronik", 0),
    })
    
    # Toplam emisyonu hesapla
    toplam_sektor_emisyon = sum(kalemler.values())
    toplam_gida_emisyon = gida_emisyonlari["toplam_emisyon"] if gida_emisyonlari else 0
    toplam_emisyon = toplam_sektor_emisyon + toplam_gida_emisyon
    
    # Gıda kalemleri dict'inden sadece emisyon değerlerini al
    gida_kalemler = gida_emisyonlari.get("kalemler", {})
    gida_emisyon_dict = {
        k: float(v.get("emisyon", 0) if isinstance(v, dict) else v)
        for k, v in gida_kalemler.items()
    }
    
    return toplam_emisyon, {
        **kalemler,
        "elektrik": kalemler["elektrik"],
        "dogalgaz": kalemler["dogalgaz"],
        "dolmus": kalemler["dolmus"],
        "minibus": kalemler["minibus"],
        "otobus": kalemler["otobus"],
        "metro": kalemler["metro"],
        "otomobil": kalemler["otomobil"],
        "ucak": kalemler["ucak"],
        "taksi": kalemler["taksi"],
        "tren": kalemler["tren"],
        "gemi": kalemler["gemi"],
        # Gıda kalemleri - sadece emisyon değerleri
        "kirmizi_et": gida_emisyon_dict.get("kirmizi_et", 0),
        "beyaz_et": gida_emisyon_dict.get("beyaz_et", 0),
        "balik": gida_emisyon_dict.get("balik", 0),
        "sut_urunleri": gida_emisyon_dict.get("sut_urunleri", 0),
        "yumurta": gida_emisyon_dict.get("yumurta", 0),
        "sebzeler": gida_emisyon_dict.get("sebzeler", 0),
        "meyveler": gida_emisyon_dict.get("meyveler", 0),
        "giyim": gida_emisyon_dict.get("giyim", 0),
        "elektronik": gida_emisyon_dict.get("elektronik", 0),
    }


def emisyon_seviyesi_belirle(toplam_kg: float) -> str:
    """Emisyon seviyesini Türkiye ortalamasina gore belirler."""
    kisi_basina_yillik = (toplam_kg * 52) / 1000  # Haftalıktan yıllığa
    turkiye_ortalamasi = constants.KIŞI_BASINA_YILLIK_LIMITLER["total"]
    
    oran = kisi_basina_yillik / turkiye_ortalamasi
    
    if oran <= constants.EMISYON_SEVIYELERI["cok_dusuk"]:
        return "cok_dusuk"
    elif oran <= constants.EMISYON_SEVIYELERI["dusuk"]:
        return "dusuk"
    elif oran <= constants.EMISYON_SEVIYELERI["normal"]:
        return "normal"
    elif oran <= constants.EMISYON_SEVIYELERI["yuksek"]:
        return "yuksek"
    else:
        return "cok_yuksek"


def eksik_kategorileri_tamamla(girdi: Mapping[str, Any]) -> Dict[str, float]:
    """Beslenme ve alışveriş gibi eksik kategorileri IPCC katsayilariyla tamamlar."""
    temiz = normalize_girdi(girdi)
    ek_kalemler: Dict[str, float] = {}
    
    # Standart varsayilan değerler (Türkiye ortalamasina gore)
    varsayilan_degerler = {
        "et_kirmizi": 2.0,  # kg/hafta
        "sebze_meyve": 3.0,  # kg/hafta
        "giyim": 0.5,  # kg/hafta
        "elektronik": 0.2,  # adet/hafta
    }
    
    for kategori, miktar in varsayilan_degerler.items():
        if kategori in constants.IPCC_EK_KATSAYILARI:
            emisyon = miktar * constants.IPCC_EK_KATSAYILARI[kategori]
            ek_kalemler[kategori] = emisyon
    
    return ek_kalemler
