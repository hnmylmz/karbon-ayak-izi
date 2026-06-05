# Karbon Ayak İzi Projesi

Bu proje Flask tabanlı bir web uygulamasıdır. Kullanıcılar kayıt olup giriş yaparak kişisel karbon ayak izi hesaplamalarını yapabilir ve geçmiş kayıtlara erişebilir.

Önemli özellikler:
- Kullanıcı kayıt/giriş (parola hash ile saklanır)
- E-posta doğrulama token'ı (SMTP yapılandırılmışsa otomatik gönderim)
- Kullanıcıya bağlı geçmiş kayıtlar (`weekly_history.user_id`) — tablo adı legacy niteliktedir, uygulama artık aylık toplamlar üzerinden hesap yapar
- Basit rate-limiting, session güvenlik ayarları ve dotenv desteği

Hızlı başlangıç (yerel geliştirme):

1. Sanal ortam oluştur ve etkinleştir

```bash
python -m venv .venv
# Windows Powershell
.\.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate
```

2. Bağımlılıkları yükle

```bash
python -m pip install -r requirements.txt
```

3. Ortam değişkenleri
- Üretimde `FLASK_SECRET_KEY` ayarlayın. Aksi halde proje `modeller/secret.key` dosyasını oluşturup kullanır.
- E-posta doğrulama istiyorsanız `.env` dosyasına `.env.example` içindeki SMTP değerlerini doldurun.
- Doğrulama e-postasındaki bağlantının doğru olabilmesi için `BASE_URL` değerini uygulamanın çalıştığı adrese göre ayarlayın.

4. Uygulamayı başlat

```bash
python app.py
```

5. Tarayıcıda açın: `http://localhost:5000`

Veri kaynakları
- Uygulama kendisi doğrudan `data/turkiye_emisyon.csv` ve `data/turkiye_emisyon_temiz.csv` dosyalarını kullanır.
- `veri_kaynaklari.md` yalnızca dokümantasyon amaçlıdır; kodda doğrudan okunmaz.

Test kullanıcı
- Geliştirme için oluşturulmuş test kullanıcı: `testuser / secret`. Üretimde bu kullanıcıyı silin.

Güvenlik notları (üretim):
- HTTPS zorunlu kılın.
- Güçlü `FLASK_SECRET_KEY` kullanın (env var).
- SMTP ile e-posta doğrulamayı aktif edin.
- `flask-limiter` kurarak rate limiting etkinleştirin.
- Oturum ayarlarını (cookie secure, httpOnly) kontrol edin.
- Parola yeniden sıfırlama ve e-posta doğrulama süreçlerini dikkatle yönetin.

## Üretim (prod) deploy adımları

Bu projeyi üretimde çalıştırmak için nginx + gunicorn + systemd + HTTPS kombinasyonu önerilir.

### 1. nginx konfigürasyonu
- `deploy/nginx-karbon.conf.example` dosyasını şu yere kopyalayın:
  ```bash
  sudo cp deploy/nginx-karbon.conf.example /etc/nginx/sites-available/karbon
  ```
- İçindeki `server_name` değerini kendi domaininizle değiştirin.
- `example.com` yerine kendi domaininizi yazın.
- Konfigürasyonu aktif edin:
  ```bash
  sudo ln -s /etc/nginx/sites-available/karbon /etc/nginx/sites-enabled/
  sudo nginx -t
  sudo systemctl restart nginx
  ```

### 2. HTTPS almak
- Certbot ve nginx eklentisini kurun:
  ```bash
  sudo apt install certbot python3-certbot-nginx
  ```
- Sertifika al:
  ```bash
  sudo certbot --nginx -d example.com -d www.example.com
  ```
- `example.com` yerine gerçek domaininizi yazın.
- Yenilemeyi test et:
  ```bash
  sudo certbot renew --dry-run
  ```

### 3. Gunicorn + systemd
- `deploy/karbon.service.example` dosyasını şu yere kopyalayın:
  ```bash
  sudo cp deploy/karbon.service.example /etc/systemd/system/karbon.service
  ```
- Dosyadaki `/path/to/your/project` ve `.venv` yolunu kendi proje yoluna göre değiştirin.
- Ortam değişkenlerini (`FLASK_SECRET_KEY`, SMTP bilgileri) üretim ortamınıza göre ayarlayın.
- Servisi başlatın:
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl start karbon
  sudo systemctl enable karbon
  sudo systemctl status karbon
  ```

### 4. Güvenli environment
- `FLASK_SECRET_KEY` için güçlü bir anahtar üretin:
  ```bash
  python - <<'PY'
  import secrets
  print(secrets.token_urlsafe(64))
  PY
  ```
- Bu değeri `karbon.service` içine veya sunucu ortamına ekleyin.
- SMTP kullanıyorsanız `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` ayarlayın.

### 5. Rate limiting
- Nginx konfigürasyonunda limite eklemek için `nginx.conf` içine aşağıyı ekleyin:
  ```nginx
  http {
      limit_req_zone $binary_remote_addr zone=one:10m rate=10r/m;
      ...
  }
  ```
- `login` ve `register` lokasyonlarına ekleyin:
  ```nginx
  location /login {
      limit_req zone=one burst=5 nodelay;
      proxy_pass http://127.0.0.1:8000;
  }
  location /register {
      limit_req zone=one burst=5 nodelay;
      proxy_pass http://127.0.0.1:8000;
  }
  ```

### 6. Parola güvenliği
- Mevcut parola politikası: en az 8 karakter, en az 1 harf ve 1 rakam.
- Üretimde daha sıkı bir politika için ek olarak:
  - En az 12 karakter
  - Büyük harf
  - Küçük harf
  - Rakam
  - Özel karakter

### 7. Çalıştırma öncesi kontrol
- Uygulamayı test edin:
  ```bash
  gunicorn -w 4 -b 127.0.0.1:8000 app:app
  ```
- Nginx yönlendirmesini test edin ve HTTPS ile erişin.
- Giriş/kayıt akışını test edin.

---

### Dosya şablonları
- `deploy/nginx-karbon.conf.example`
- `deploy/karbon.service.example`

Bu şablonları sunucunuzda kopyalayıp kendi değerlerinizle düzenleyin.

