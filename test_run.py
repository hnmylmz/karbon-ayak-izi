from veriler import hesapla_toplam_emisyon

g = {
    'electricity_kwh':250,'dogalgaz_m3':30,'otomobil_km':300,'ucak_km':100,'kirmizi_et':2,'beyaz_et':1,'balik':0.5,'sut_urunleri':5,'yumurta':12,'sebzeler':10,'meyveler':5,'giyim':1,'elektronik':30,'dolmus_km':0,'minibus_km':0,'otobus_km':40,'metro_km':20,'taksi_km':10,'tren_km':0,'gemi_km':0,'lag_1_co2':42,'lag_2_co2':40,'lag_3_co2':39,'lag_4_co2':41,'hafta':17,'sehir_kodu':0,'arac_sahibi':1
}

print(hesapla_toplam_emisyon(g))
