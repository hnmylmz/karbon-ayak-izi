import math
import re
from collections import Counter


WORD_RE = re.compile(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+")

INTENT_KEYWORDS = {
    "greeting": ["merhaba", "selam", "hey", "iyi", "slm", "mrhb", "halo", "naber", "nasilsin", "selamlar"],
    "factors": ["katsayi", "faktor", "elektrik", "dolmus", "ulasim", "gida", "gıda", "beslenme", "yemek", "co2", "emisyon", "deger", "hesaplama", "parametre"],
    "model": ["model", "egit", "xgboost", "tahmin", "ml", "machine learning", "yapay zeka", "ogrenme", "algoritma"],
    "reduction": ["azalt", "dusur", "oner", "tavsiy", "ne yap", "iyilestir", "nasil azalir", "co2 dusuk", "temiz", "gida", "gıda", "beslenme", "yemek"],
    "how_to_use": ["nasil", "kullan", "form", "alan", "site", "hesapla", "calisir", "isleyis", "adimlar", "gida", "gıda", "beslenme", "yemek"],
    "environment": ["cevre", "iklim", "global isinma", "sera gazlari", "karbon", "ekoloji", "doga", "gezegen", "surdurulebilir"],
    "comparison": ["karsilastirma", "fark", "daha iyi", "en iyi", "ortalama", "turkiye", "diger", "kullanici"],
    "technical": ["hata", "sorun", "calismiyor", "api", "veritabani", "database", "log", "debug", "test"],
    "statistics": ["istatistik", "grafik", "veri", "analiz", "rapor", "sayi", "miktar", "yuzde", "artis", "azalis"],
    "personal": ["benim", "kendi", "bireysel", "kisisel", "ev", "is", "yolculuk", "seyahat", "gunluk"],
    "project": ["proje", "amac", "ne yapar", "kapsam", "ozellik", "neden bu", "neden", "uygulama", "mimari", "kullanim alani", "deploy", "uretim", "prod"],
    "deployment": ["nginx", "gunicorn", "systemd", "deploy", "prod", "ssl", "https", "sertifika", "service", "nginx konfig", "certbot"],
    "auth": ["login", "giris", "kayit", "register", "sifre", "email", "e-posta", "dogrulama", "verify", "token", "session"],
    "simulation": ["simulasyon", "tahmin", "tahmini", "slider", "azaltim", "gelecek ay", "gelecek hafta", "simule", "model"],
    "graphics": ["grafik", "grafikler", "cizim", "gorsel", "trend", "diagram", "cizgi", "bar", "karsilastirma", "veri gorsellestirme"],
    "data": ["veri", "kaynak", "dataset", "csv", "kullaniciverisi", "turkiye verisi", "ortalama", "kaynak", "sqlite", "db", "database", "tablo", "modeller"],
    "training": ["egit", "egitim", "egitimi", "train", "xgboost", "ml model", "hibrit", "model dosyasi", "modeller", "feature", "shap"],
}

INTENT_RESPONSES = {
    "greeting": [
        "Merhaba! Karbon ayak izi hesabinda birlikte ilerleyebiliriz. Neye odaklanmak istersin?",
        "Selam! Verilerini girersen kural motoru ve ML tahminini birlikte yorumlayabilirim.",
        "Merhaba, hazirim. Istersen once ulasim kalemlerinden baslayalim, sonra enerji tuketimine bakalim.",
        "Iyi gunler! Sürdürülebilir gelecek icin karbon ayak izini takip etmek onemli. Nasil yardimci olabilirim?",
    ],
    "factors": [
        "Katsayilar `veriler.py` dosyasinda. Elektrik ve ulasim faktorlerini oradan guncelleyebilirsin.",
        "Faktorler uygulamada merkezde `veriler.py` icinde tutuluyor; degisiklik yaptiginda hesaplama hemen etkilenir.",
        "Elektrik, dogalgaz ve ulasim emisyon katsayilarini `veriler.py` uzerinden yonetiyorsun. Turkiye ortalamalari kullaniliyor.",
        "Her kategorinin ozel CO2 katsayisi var: elektrik (kWh), dogalgaz (m3), ulasim (km) bazinda hesaplanir.",
    ],
    "model": [
        "ML modeli icin `python hibrit_model_egit.py` calistirip `modeller/hibrit_model.joblib` dosyasini olusturmalisin.",
        "Tahmin katmani hibrit MLP + XGBoost modeli kullanir; modeli egittikten sonra uygulama otomatik yukler.",
        "Model hazir degilse sistem fallback tahmin verir, model hazirsa hibrit model sonucu doner.",
        "Hibrit model geçmiş ay ve girdi özelliklerini kullanarak gelecek ay emisyonunu tahmin eder.",
    ],
    "reduction": [
        "En etkili azaltim adimlari genelde otomobil, enerji ve gıda kaynakli emisyonu azaltmaktir; toplu tasima, enerji verimliligi ve daha bitkisel beslenme secimleri fark yaratir.",
        "Elektrikte verimli cihaz ve tuketim takibi, ulasimda otomobil yerine metro/otobus secimi toplam emisyonu hizla dusurur.",
        "Onceliklendirme icin once en yuksek kalemi bul: en cok hangi kategori emisyon uretiyorsa ona odaklan.",
        "Karbon ayak izini azaltmak icin: 1) Ozel arac kullanımını azalt, 2) Enerji verimliliğini artır, 3) Gıda kaynaklarını daha sürdürülebilir seç, 4) Az az ama sık sık.",
    ],
    "how_to_use": [
        "Formdaki ulasim, enerji ve gıda alanlarını doldurup 'Karbon Ayak Izini Hesapla' butonuna basabilirsin.",
        "Ulasım, enerji ve gıda girdilerini aynı ekranda girmen daha kapsamlı bir değerlendirme sağlar.",
        "Ardindan ML alani icin ay, sehir kodu ve lag CO2 degerlerini girip tahmini yenileyebilirsin.",
        "Ilk adimda hesaplama yap, ikinci adimda ayni ekranda gelecek ay tahminini kontrol et.",
        "Adim adim: 1) Bilgilerini gir, 2) Hesapla butonuna tikla, 3) Sonuclari incele, 4) Grafikten karsilastirma yap, 5) AI asistanindan oneri al.",
    ],
    "environment": [
        "Karbon ayak izi, bireylerin ve kuruluslarin atmosfere saldigi sera gazlarinin toplam miktaridir.",
        "Global isinma 1.5°C altinda tutmak icin 2030'a kadar emisyonlarin %45 azaltilmasi gerekiyor.",
        "Turkiye'nin yillik ortalama karbon ayak izi kisi basina yaklasik 4-5 ton CO2e civarinda.",
        "Surdurulebilirlik sadece cevre degil, ayni zamanda ekonomik ve sosyal faydalar da saglar.",
    ],
    "comparison": [
        "Turkiye ortalamasi ile karsilastirmak icin grafik bölümunu kullanabilirsin. Ad-soyad girip grafigi guncelle.",
        "Kendi verilerini Turkiye ortalamasiyla karsilastirarak nerede durdugunu gorebilirsin.",
        "Ortalama bir Turk vatandasi yilda 4.5 ton CO2 uretir. Senin degerin bunun altinda mi ustunde mi?",
        "Karsilastirma yapmak motivasyon kaynagidir. Her ay kendi gelismini takip et.",
    ],
    "technical": [
        "Teknik sorunlar icin log'lari kontrol et ve `veriler.py` dosyasindan katsayilari dogrula.",
        "Hata alirsan: 1) Python versiyonunu kontrol et, 2) Gerekli kutuphaneleri yukle, 3) Model dosyasinin varligini kontrol et.",
        "API endpoint'leri: /chat, /tahmin, /laglar, /grafik_veri. Bunlari test edebilirsin.",
        "Veritabani SQLite kullaniliyor, `modeller/karbon_gecmis.db` dosyasinda saklaniyor.",
        "Uygulamayi calistirmadan once `requirements.txt` dosyasini yuklemelisin.",
        "Proje Python 3.11 uyumlu; `app.py` Flask ve model dosyalarina baglidir.",
    ],
    "deployment": [
        "Uretimde nginx + gunicorn + systemd kullanmak onerilir, bu sayede performans ve ozguleme artar.",
        "`deploy/nginx-karbon.conf.example` ve `deploy/karbon.service.example` dosyalarini kendi ortamina gore duzenle.",
        "HTTPS icin certbot ile sertifika alabilir ve nginx uzerinden sunucuyu ayarlayabilirsin.",
        "`FLASK_SECRET_KEY` ve SMTP ayarlari .env dosyasinda tutuluyor. Uretimde bunlari dogrudan share etme.",
    ],
    "auth": [
        "Kullanici kaydi `register` rotasi ile yapiliyor; sifreler hashlenerek `modeller/karbon_gecmis.db`'de saklaniyor.",
        "Giris `login` rotasi uzerinden yapiliyor; e-posta dogrulamasi varsa `verify_token` kullanilir.",
        "E-posta dogrulama icin SMTP ayarlari .env dosyasina eklenmeli ve `BASE_URL` dogru ayarlanmalidir.",
        "Parola politikasi en az 8 karakter, 1 harf ve 1 rakam seklinde kurulmus olabilir.",
    ],
    "statistics": [
        "Grafik kisminda son 8 ayin verilerini gorebilirsin. Zamanla trend takibi yapabilirsin.",
        "Istatistikler gecmis verilerden olusur. Daha fazla hesaplama yaptikca grafigin daha anlamli hale gelir.",
        "Aylik degisimleri takip etmek, hangi ayda daha fazla emisyon urettigini gosterir.",
        "Yuzdesel degisimler, iyilesme veya kotulesme trendini gosterir.",
        "Turkiye benchmark'i kullanici verisi ile daha net karsilastirma saglar.",
    ],
    "personal": [
        "Kisisel karbon ayak izin gunluk aliskanliklarindan etkilenir: ulasim, enerji, beslenme, alisveris.",
        "Evdeki en buyuk emisyon kaynaklari genelde isitma (dogalgaz) ve elektrik tuketimidir.",
        "Ise giderken toplu tasima kullanmak aylik 100-200kg CO2 tasarrufu saglayabilir.",
        "Kisisel hedefler koy: Bu ay %10 azalt, gelecek ay %20 azalt gibi.",
    ],
    "project": [
        "Bu proje, kullanicinin aylik karbon ayak izini hesaplayan, Turkiye ortalamasi ile karsilastiran ve azaltim simulasyonu sunan bir uygulamadir.",
        "Amac, hem bireysel tasarruf onerileri vermek hem de kullanicinin Turkiye ortalamasiyla ne durumda oldugunu gostermektir.",
        "Uygulama hem kural motoruyle anlik emisyon hesaplar hem de ML modelle gelecege yonelik tahminler uretir.",
        "Proje, kullanici girdilerini alir, hem kural tabanli hem de makine ogrenmesi tabanli analizler dondurur.",
    ],
    "simulation": [
        "Simulasyon, kullanicinin ulasim, enerji ve gida azaltim oranlarini alarak beklenen CO2 degisimini tahmin eder.",
        "Sliderlar, azaltilan yuzdeleri guncelleyip yeni bir tahmini cizgiyle gosterir; bu yuzdeyle hedef etki hesaplanir.",
        "Simulasyon sonucu, Turkce referans grafiğinin uzerinde karsilastirmayi kolaylastirir.",
        "Simulasyon tahmini genellikle sabit bir hedef deger olarak grafik uzerinde yatay bir cizgiyle gosterilir.",
    ],
    "graphics": [
        "Grafikler, kullanicinin aylik toplam CO2 degerini Turkiye ortalamasi ve simulasyon tahminiyle karsilastirir.",
        "Line chart, birden fazla ay varken trendleri net gosterir; simdi tek ay varsa sadece nokta gorunur.",
        "Daha iyi bir yorum icin birden fazla ay verisiyle trend çizgileri takip edilebilir.",
        "Grafik, hem kullanici degerini hem de referans ve simulasyon degerlerini ayni eksende gostererek karsilastirmayi basitleştirir.",
    ],
    "data": [
        "Turkiye ortalama degerleri, uygulamadaki sabit benchmark hesaplamalari uzerinden olusturuluyor.",
        "Kullanici verisi aylik CO2 kilogram cinsinden kaydediliyor ve grafikte karsilastirma icin kullaniliyor.",
        "Veri kaynagi olarak hem kullanici girdileri hem de `data/turkiye_emisyon.csv` turu veriler kullaniliyor.",
        "Model egitimi ve benchmarklar Turkiye ortalama parametrelerine dayaniyor.",
    ],
    "training": [
        "Model egitimi icin `hibrit_model_egit.py` dosyasini calistirip uretilecek `modeller/hibrit_model.joblib` dosyasini kullanmalisin.",
        "Hibrit model, hem XGBoost hem de multilayer perceptron (MLP) katmanini birlestirir.",
        "Egitim verisi `data/turkiye_emisyon_temiz.csv` dosyasindan gelmektedir.",
        "Modeli yeniden egitmek istiyorsan once veriyi temizleyip featur engineering yapman gerekiyor.",
        "`modeller/hybrid_features.joblib` modelde kullanilan ozellik listesini icerir.",
        "Model cikisi gram cinsinden tahmin edildikten sonra uygulama bunu kgCO2e'ye cevirir.",
    ],
    "fallback": [
        "Sorunu biraz daha acabilir misin? Ornegin 'katsayiyi nasil guncellerim' veya 'modeli nasil egitirim' diye sorabilirsin.",
        "Bunu daha iyi cevaplamam icin biraz detay verir misin? Hedefin hesaplama, katsayi, model veya cevre olabilir.",
        "Anladigim kadariyla genel bir soru; istersen adim adim nasil kullanacagini anlatabilirim.",
        "Belki su konulardan birini sorabilirsin: nasil kullanilir, katsayilar, model egitimi, emisyon azaltma, cevre bilgileri.",
    ],
}

KNOWLEDGE_CHUNKS = [
    "Bu uygulama iki katmandan olusur: kural motoru anlik CO2 hesabini yapar, ML katmani gelecek ayi tahmin eder.",
    "Kural motoru elektrik, dogalgaz, dolmus, otobus, metro, otomobil ve ucak girdilerinden kgCO2e hesaplar.",
    "Hibrit model MLP + XGBoost bileşimini kullanarak Turkiye emisyon verileriyle egitilir ve gecmis ayları lag ozellikleri olarak kullanir.",
    "Model egitimi tamamlandiginda model dosyasi `modeller/hibrit_model.joblib` olarak kaydedilir.",
    "Daha iyi tahmin icin lag_1_co2 ile lag_4_co2 degerlerinin gercek kullanici gecmisinden gelmesi gerekir.",
    "Karbon ayak izi, bir kisinin veya kurulusun faaliyetleri sonucunda atmosfere saldigi sera gazlarinin toplam miktaridir.",
    "Bir ton CO2, bir yolcu ucağinin New York'tan Los Angeles'a yapacagi ucus kadar emisyona denktir.",
    "Evde en yaygin emisyon kaynaklari: isitma sistemleri (dogalgaz), elektrik tuketimi, sıcak su ve pişirme.",
    "Ulasim emisyonlarinda otomobil en yuksek CO2 kaynagidir, bisiklet ve yurume ise sifir emisyonludur.",
    "Turkiye'de ortalama bir hane yillik 2.5 ton CO2 sadece elektrik tuketiminden uretir.",
    "Global isinmayi 1.5°C ile sinirlandirmak icin 2030'a kadar kuresel emisyonlarin yarisini azaltmak gerekiyor.",
    "Yenilenebilir enerji kaynaklari (gunes, ruzgar) fosil yakitlara gore %90 daha az CO2 uretir.",
    "Agaclandirma her yil bir agac dikmek yillik 22 kg CO2 emebilir, 40 yilda 1 ton CO2 dengeleyebilir.",
    "Et tuketimi, sebze tuketimine gore 2-3 kat daha fazla karbon ayak izine neden olur.",
    "Dijital aktiviteler de CO2 uretir: 100 e-posta gondermek 0.3 kg CO2, 1 saat video izlemek 0.2 kg CO2.",
    "Enerji verimliligini artirmak: LED ampuller %80 daha az enerji kullanir, akilli termostatlar %23 tasarruf saglar.",
    "Toplu tasima kullanmak (metro, otobus) ozel araca gore kisi basina %75 daha az emisyon uretir.",
    "Surdurulebilir alisveris: yerel urunler tercih etmek, uretim ve nakliye emisyonlarini azaltir.",
    "Karbon nötr olmak, urettiginiz kadar CO2'i atmosferden cekmeyi veya dengelemeyi ifade eder.",
    "Paris Anlasmasi, ulkeleri kuresel isinmayi 2°C altinda tutmak icin emisyon azaltma hedefleri belirlemeye zorunlu kilar.",
    "Karbon ayak izi hesaplama kategorileri: tuketim, ulasim, konut, gida, hizmetler ve diger.",
    "Isitma sogutma sistemleri evdeki toplam emisyonun %40'ini olusturabilir, yalitim bu orani %50 azaltabilir.",
    "Elektrikli araclar benzinli araclara gore kuyruk emisyonu olmasa da pil uretimi ve sarj emisyonlari vardir.",
    "Recycling and composting can reduce household emissions by up to 15% annually.",
    "Karbon vergisi, CO2 emisyonlari icin uygulanan ekonomik bir cezalandirma mekanizmasidir.",
    "Yasam dongusu analizi, bir urunun uretiminden atilina kadar tum emisyonlarini hesaplar.",
    "Akilli sehirler ve yeil binalar kentsel emisyonlari %30-40 azaltabilir.",
    "Karbon kredisi, emisyon azaltan projelere yatirim yaparak kendi emisyonlarini dengeleme yontemidir.",
    "Grafik verisi `/grafik_veri` endpointinden aliniyor; son aylik kullanici verileri ve Turkiye benchmarki donduruluyor.",
    "Simulasyon sonucu `/tahmin` endpointine gonderilen slider degerleriyle uretiliyor; varsa hibrit model, yoksa kural tabanli fallback kullanilir.",
    "Kayit ve giris islemleri `register` ve `login` rotalari uzerinden yurutulur; sifreler sqlite veritabaninda hashlenmis sekilde saklanir.",
    "E-posta dogrulama SMTP kullanilarak yapilabilir ve `BASE_URL` degerinin dogru olmasi gerekir.",
    "Uygulamanin prod deployu icin nginx, gunicorn ve systemd kullanilmasi onerilir.",
    "`requirements.txt` dosyasini yuklemek uygulamayi calistirmak icin ilk adimdir.",
]

_DIRECT_ANSWERS = {
    "register": "Kullanici kaydi `register` rotasi uzerinden yapiliyor; sifreler hashlenip `modeller/karbon_gecmis.db` dosyasinda saklaniyor.",
    "login": "Giris `login` rotasi uzerinden yapiliyor; dogrulama icin mail tokenu kullanilabilir ve session verisi Flask ile yonetiliyor.",
    "chat": "Chatbot `/chat` endpointine gelen mesajlari yorumluyor ve projeyle ilgili sorulara cevap veriyor.",
    "grafik_veri": "Grafik verisi `/grafik_veri` endpointinden aliniyor; son aylik kullanici toplamlar ve Turkiye benchmark degerleri donduruluyor.",
    "tahmin": "Tahmin endpointi `/tahmin` kullanilarak slider degerlerine gore simule edilen CO2 sonucunu doner.",
    "turkiye_demo_degerleri": "Demo Turkiye degerleri `/turkiye_demo_degerleri` endpointinden gelir; bu veriler simulasyon ve referans karsilastirmasi icin kullanilir.",
    "hibrit_model_egit.py": "`hibrit_model_egit.py` dosyasi modeli egitir; cikan model `modeller/hibrit_model.joblib` olarak kaydedilir.",
    "modeller/hibrit_model.joblib": "Bu dosya egitilmis hibrit tahmin modelini icerir ve uygulama tahmin fonksiyonunda kullanilir.",
    "veritabani": "Veriler SQLite `modeller/karbon_gecmis.db` dosyasinda saklanir; kullanici ve weekly_history tablolari bulunur.",
    "smtp": "E-posta dogrulama SMTP ile konfigure edilir; `.env` dosyasinda SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD gibi degerler bulunur.",
    "nginx": "Uretimde `deploy/nginx-karbon.conf.example` dosyasini kendi domaininize gore duzenleyip nginx ile kullanabilirsiniz.",
    "gunicorn": "Uygulamayi uretimde yatay olcak sekilde calistirmak icin gunicorn oneriilir. `gunicorn -w 4 -b 127.0.0.1:8000 app:app` seklinde calisir.",
    "dotenv": "Ortam degiskenleri `.env` dosyasinda tutularak `FLASK_SECRET_KEY`, `BASE_URL`, ve SMTP ayarlari konfigure edilir.",
}


def _tokenize(text: str):
    return [t.lower() for t in WORD_RE.findall(text or "")]


def _intent_score(tokens, keywords):
    if not tokens:
        return 0
    token_text = " ".join(tokens)
    score = 0
    
    # Exact matches get higher score
    for kw in keywords:
        if kw in token_text:
            score += 3
        
        # Partial matches
        for tok in tokens:
            if tok.startswith(kw) or kw.startswith(tok):
                score += 1
            # Fuzzy matching for similar words
            elif _levenshtein_distance(tok.lower(), kw.lower()) <= 2:
                score += 0.5
    
    # Bonus for multiple keyword matches
    keyword_matches = sum(1 for kw in keywords if kw in token_text)
    if keyword_matches > 1:
        score += keyword_matches * 0.5
    
    return score


def _levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def detect_intent(message: str) -> str:
    tokens = _tokenize(message)
    best_intent = "fallback"
    best_score = 0
    
    # Check for question patterns first
    question_patterns = {
        "nasıl": "how_to_use",
        "nasil": "how_to_use",
        "ne yapar": "project",
        "ne": "reduction",
        "neden": "project",
        "hangi": "comparison",
        "kaç": "statistics",
        "miktar": "statistics",
        "fark": "comparison",
        "sorun": "technical",
        "hata": "technical",
        "simülasyon": "simulation",
        "simulasyon": "simulation",
        "grafik": "graphics",
        "veri": "data",
        "model": "training",
    }
    
    message_lower = message.lower()
    for pattern, intent in question_patterns.items():
        if pattern in message_lower:
            return intent
    
    # Then use keyword matching
    for intent, kws in INTENT_KEYWORDS.items():
        score = _intent_score(tokens, kws)
        if score > best_score:
            best_score = score
            best_intent = intent
    
    # If score is too low, use fallback
    if best_score < 2:
        return "fallback"
    
    return best_intent


def _vectorize(text: str):
    return Counter(_tokenize(text))


def _cosine_similarity(vec_a, vec_b):
    if not vec_a or not vec_b:
        return 0.0
    common = set(vec_a) & set(vec_b)
    dot = sum(vec_a[w] * vec_b[w] for w in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _retrieve_direct_answer(message: str) -> str:
    message_lower = message.lower()
    for keyword, answer in _DIRECT_ANSWERS.items():
        if keyword in message_lower:
            return answer
    return ""


def retrieve_hint(message: str) -> str:
    query_vec = _vectorize(message)
    best_chunk = ""
    best_score = 0.0
    for chunk in KNOWLEDGE_CHUNKS:
        score = _cosine_similarity(query_vec, _vectorize(chunk))
        if score > best_score:
            best_score = score
            best_chunk = chunk
    return best_chunk if best_score >= 0.05 else ""


def _pick_response(intent: str, turn_count: int) -> str:
    candidates = INTENT_RESPONSES.get(intent, INTENT_RESPONSES["fallback"])
    return candidates[turn_count % len(candidates)]


def generate_chat_reply(message: str, context: dict | None = None):
    context = context or {}
    turn_count = int(context.get("turn_count", 0))
    last_result = context.get("last_result")

    intent = detect_intent(message)
    direct_answer = _retrieve_direct_answer(message)
    if direct_answer:
        return {"intent": intent, "answer": direct_answer}

    base = _pick_response(intent, turn_count)
    hint = retrieve_hint(message)

    dynamic = ""
    
    # Enhanced contextual responses based on user data
    if last_result:
        kalemler = last_result.get("kalemler", {})
        toplam = last_result.get("toplam_kg", 0)
        
        if kalemler:
            en_yuksek = max(kalemler, key=kalemler.get)
            en_dusuk = min(kalemler, key=kalemler.get)
            
            if intent == "reduction":
                dynamic = (
                    f" Son hesaplamanda en yuksek kalem `{en_yuksek}` ({kalemler[en_yuksek]:.2f} kgCO2e) "
                    f"ve en dusuk kalem `{en_dusuk}` ({kalemler[en_dusuk]:.2f} kgCO2e). "
                    f"Toplam emisyonun: {toplam:.2f} kgCO2e."
                )
            elif intent == "comparison":
                if toplam < 50:
                    dynamic = f" Son hesaplamanda {toplam:.2f} kgCO2e ile cok dusuk bir deger! Turkiye ortalamasinin cok altindasin."
                elif toplam < 120:
                    dynamic = f" Son hesaplamanda {toplam:.2f} kgCO2e - ortalama bir deger. Hafif bir iyilesme potansiyelin var."
                else:
                    dynamic = f" Son hesaplamanda {toplam:.2f} kgCO2e ile yuksek bir deger. En yuksek kalemin `{en_yuksek}` - buradan baslayabilirsin."
            elif intent == "personal":
                dynamic = (
                    f" Kişisel profilin: {toplam:.2f} kgCO2e. "
                    f"En buyuk etkin `{en_yuksek}` kategorisinde yapiliyor. "
                    f"Burada %15-20'lik bir dusus toplamda {(toplam * 0.8):.1f} kgCO2'e getirir."
                )
            elif intent in {"how_to_use", "fallback"}:
                dynamic = (
                    f" Son hesaplamanda en yuksek kalem `{en_yuksek}` gorunuyor "
                    f"({kalemler[en_yuksek]:.2f} kgCO2e)."
                )
        
        # Add specific advice based on dominant categories
        if intent == "reduction" and kalemler:
            if "elektrik" in kalemler and kalemler["elektrik"] > 30:
                dynamic += " Elektrik tuketimini dusurmek icin LED lamba ve akilli priz kullanabilirsin."
            if "otomobil" in kalemler and kalemler["otomobil"] > 50:
                dynamic += " Otomobil kullanimini azaltmak icin haftada 2 gun toplu tasima gecmeyi deneyebilirsin."
            if "ucak" in kalemler and kalemler["ucak"] > 20:
                dynamic += " Ucak yolculuklari yerine tren veya otobus tercih etmek buyuk fark yaratabilir."
    
    # Add encouraging messages for progress
    if turn_count > 3 and intent != "greeting":
        encouragement = [
            " Sorularini sormaya devam et! Her adim surdurulebilir bir gelecek icin onemli.",
            " Bilgilenme yolculugunda ilerliyorsun! Baska ne ogrenmek istersin?",
            " Harika sorular! Karbon ayak izi hakkinda daha fazla bilgi ediniyorsun.",
        ]
        if turn_count % 4 == 0:
            dynamic += f" {encouragement[turn_count // 4 % len(encouragement)]}"

    answer = base
    if intent == "fallback" and hint:
        answer = hint
    elif hint:
        answer = f"{base} Bilgi: {hint}"
    if dynamic:
        answer += dynamic

    return {"intent": intent, "answer": answer.strip()}
