from pathlib import Path
import sqlite3
import os
import secrets
import smtplib
import sys
from email.message import EmailMessage
import importlib
import gc

import numpy as np
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session

import constants
import gida_emisyon_sozlugu
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from typing import Any, Dict, List, Mapping, Sequence, Tuple, Optional
from datetime import datetime, timedelta
from copy import deepcopy

class ValidationError(ValueError):
    def __init__(self, message: str, field_errors: Optional[Dict[str, str]] = None) -> None:
        super().__init__(message)
        self.field_errors = field_errors or {}

# Optional optional dependencies
Limiter = None

def _default_get_remote_address():
    return "127.0.0.1"

get_remote_address = _default_get_remote_address
try:
    limiter_module = importlib.import_module("flask_limiter")
    Limiter = getattr(limiter_module, "Limiter", None)
    util_module = importlib.import_module("flask_limiter.util")
    get_remote_address = getattr(util_module, "get_remote_address", _default_get_remote_address)
except ImportError:
    Limiter = None
    get_remote_address = _default_get_remote_address

try:
    dotenv_module = importlib.import_module("dotenv")
    load_dotenv = getattr(dotenv_module, "load_dotenv", None)
    if load_dotenv:
        load_dotenv()
except ImportError:
    # python-dotenv not installed; ignore .env loading
    pass

from chatbot import generate_chat_reply
from veriler import RequestCleaner, hesapla_toplam_emisyon

app = Flask(__name__)
app.config.setdefault('TEMPLATES_AUTO_RELOAD', True)
app.jinja_env.auto_reload = True
app.config.setdefault('SEND_FILE_MAX_AGE_DEFAULT', 0)

# Secret key: prefer env var, else persistent file in modeller/secret.key
secret_from_env = os.environ.get("FLASK_SECRET_KEY")
secret_file = Path("modeller/secret.key")
if secret_from_env:
    app.secret_key = secret_from_env
else:
    if secret_file.exists():
        app.secret_key = secret_file.read_text().strip()
    else:
        sk = secrets.token_urlsafe(32)
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        secret_file.write_text(sk)
        app.secret_key = sk

# Login manager setup
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

# Rate limiter (optional)
if Limiter:
    limiter = Limiter(app=app, key_func=get_remote_address)
else:
    class _NoopLimiter:
        def limit(self, *args, **kwargs):
            def _decor(f):
                return f
            return _decor
    limiter = _NoopLimiter()


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Session security defaults (can be overridden by env vars)
app.config.setdefault('SESSION_COOKIE_SECURE', os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True')
app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
app.config.setdefault('SESSION_COOKIE_SAMESITE', os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax'))
app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(days=int(os.environ.get('PERMANENT_SESSION_DAYS', '7'))))

# Input scaling multiplier: multiply small user inputs before sending to model,
# then divide model outputs back by this multiplier for display.
app.config.setdefault('INPUT_MULTIPLIER', float(os.environ.get('INPUT_MULTIPLIER', '1')))

# Use absolute paths relative to this script's directory for models and database
APP_DIR = Path(__file__).parent
MODEL_PATH = APP_DIR / "modeller" / "hibrit_model.joblib"
FEATURES_PATH = APP_DIR / "modeller" / "hybrid_features.joblib"

# Database handling: prefer `DATABASE_URL` env var (e.g. sqlite:///path/to.db).
# If not provided or unsupported, fallback to local SQLite file `modeller/karbon_gecmis.db`.
_db_env = os.environ.get("DATABASE_URL", "").strip()
if _db_env:
    if _db_env.startswith("sqlite:///"):
        sqlite_path = _db_env.replace("sqlite:///", "")
        DB_PATH = Path(sqlite_path)
    elif _db_env.startswith("sqlite://"):
        sqlite_path = _db_env.replace("sqlite://", "")
        DB_PATH = Path(sqlite_path)
    else:
        # Non-sqlite DB URL provided (e.g., Postgres). Current codebase uses sqlite3,
        # so keep using local sqlite DB for now and log a warning.
        DB_PATH = APP_DIR / "modeller" / "karbon_gecmis.db"
        try:
            app.logger.warning(
                "DATABASE_URL provided but is not sqlite. Using local SQLite fallback. Postgres support requires additional changes."
            )
        except Exception:
            pass
else:
    DB_PATH = APP_DIR / "modeller" / "karbon_gecmis.db"
RULE_FEATURES = [
    "electricity_kwh",
    "dogalgaz_m3",
    "dolmus_km",
    "minibus_km",
    "otobus_km",
    "metro_km",
    "otomobil_km",
    "taksi_km",
    "tren_km",
    "gemi_km",
    "ucak_km",
    # Gıda özellikleri
    "kirmizi_et",
    "beyaz_et",
    "balik",
    "sut_urunleri",
    "yumurta",
    "sebzeler",
    "meyveler",
    "giyim",
    "elektronik",
]
ML_EXTRA_FEATURES = ["ay", "sehir_kodu", "arac_sahibi", "lag_1_co2", "lag_2_co2", "lag_3_co2", "lag_4_co2"]
SIMULATION_TRANSPORT_FEATURES = [
    "dolmus_km",
    "minibus_km",
    "otobus_km",
    "metro_km",
    "otomobil_km",
    "taksi_km",
    "tren_km",
    "gemi_km",
    "ucak_km",
]
SIMULATION_TRANSPORT_EMISSION_KEYS = [
    "dolmus",
    "minibus",
    "otobus",
    "metro",
    "otomobil",
    "taksi",
    "tren",
    "gemi",
    "ucak",
]
SIMULATION_RED_MEAT_FEATURE = "kirmizi_et"
SIMULATION_ENERGY_FEATURES = ["electricity_kwh", "dogalgaz_m3"]
SIMULATION_ENERGY_EMISSION_KEYS = ["elektrik", "dogalgaz"]
SIMULATION_FOOD_FEATURES = [
    "kirmizi_et",
    "beyaz_et",
    "balik",
    "sut_urunleri",
    "yumurta",
    "sebzeler",
    "meyveler",
    "giyim",
    "elektronik",
]
CHAT_STATE = {"turn_count": 0, "last_result": None}
DEFAULT_LAGS = [0.0, 0.0, 0.0, 0.0]
TURKIYE_AYLIK_REFERANS_KG = 120.0
WEEKS_PER_MONTH = 4.345
INPUT_FEATURES = RULE_FEATURES + ML_EXTRA_FEATURES
HISTORY_COLUMNS = [
    "electricity_kwh",
    "dogalgaz_m3",
    "dolmus_km",
    "minibus_km",
    "otobus_km",
    "metro_km",
    "otomobil_km",
    "taksi_km",
    "tren_km",
    "gemi_km",
    "ucak_km",
    "kirmizi_et",
    "beyaz_et",
    "balik",
    "sut_urunleri",
    "yumurta",
    "sebzeler",
    "meyveler",
    "giyim",
    "elektronik",
    "ay",
    "sehir_kodu",
    "arac_sahibi",
    "lag_1_co2",
    "lag_2_co2",
    "lag_3_co2",
    "lag_4_co2",
]
INPUT_PIPELINE = Pipeline(
    [
        ("request_cleaner", RequestCleaner(INPUT_FEATURES)),
        ("imputer", SimpleImputer(strategy="constant", fill_value=0.0)),
    ]
)

# Fit the pipeline once with a zero-value sample so transform() can be used immediately.
INPUT_PIPELINE.fit([
    {feature: 0.0 for feature in INPUT_FEATURES}
])


def build_default_form_data() -> Dict[str, str]:
    # Provide realistic example defaults to help users and testing.
    form_data: Dict[str, str] = {f: "0" for f in RULE_FEATURES + ML_EXTRA_FEATURES}
    form_data["ad"] = "Ahmet"
    form_data["soyad"] = "Yilmaz"
    # Typical monthly values as examples
    form_data["electricity_kwh"] = "250"  # kWh/month
    form_data["dogalgaz_m3"] = "30"  # m3/month
    form_data["dolmus_km"] = "0"
    form_data["minibus_km"] = "0"
    form_data["otobus_km"] = "40"
    form_data["metro_km"] = "20"
    form_data["otomobil_km"] = "300"
    form_data["taksi_km"] = "10"
    form_data["tren_km"] = "0"
    form_data["gemi_km"] = "0"
    form_data["ucak_km"] = "100"
    form_data["kirmizi_et"] = "2"  # kg/month
    form_data["beyaz_et"] = "1"
    form_data["balik"] = "0.5"
    form_data["sut_urunleri"] = "5"
    form_data["yumurta"] = "12"
    form_data["sebzeler"] = "10"
    form_data["meyveler"] = "5"
    form_data["giyim"] = "1"
    form_data["elektronik"] = "30"
    form_data["ay"] = "7"
    form_data["sehir_kodu"] = "0"
    form_data["arac_sahibi"] = "1"
    # Gıda varsayılan değerleri
    form_data["kirmizi_et"] = "0"
    form_data["beyaz_et"] = "0"
    form_data["balik"] = "0"
    form_data["sut_urunleri"] = "0"
    form_data["yumurta"] = "0"
    form_data["sebzeler"] = "0"
    form_data["meyveler"] = "0"
    form_data["giyim"] = "0"
    form_data["elektronik"] = "0"
    form_data["ay"] = "7"
    # Ek ulaşım özellikleri
    form_data["minibus_km"] = "0"
    form_data["taksi_km"] = "0"
    form_data["tren_km"] = "0"
    form_data["gemi_km"] = "0"

    return form_data


def build_blank_form_data() -> Dict[str, str]:
    form_data: Dict[str, str] = {f: "0" for f in RULE_FEATURES + ML_EXTRA_FEATURES}
    form_data["ad"] = ""
    form_data["soyad"] = ""
    form_data["ay"] = "1"
    return form_data


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            s = value.strip()
            if s == "":
                return default
            # allow comma as decimal separator and remove spaces
            s = s.replace(" ", "").replace(",", ".")
            return float(s)
        return float(value)
    except (TypeError, ValueError):
        return default


def validate_inputs(payload: Mapping[str, Any]) -> None:
    """Negatif veya uygunsuz sayisal deger girislerini engeller.

    Raises ValidationError with a descriptive message and field-level details.
    """
    negative_fields: List[str] = []
    non_numeric: List[Tuple[str, str]] = []
    field_errors: Dict[str, str] = {}

    for feature in INPUT_FEATURES:
        raw = payload.get(feature, 0)
        # treat empty strings as zero
        if raw is None:
            continue
        s = str(raw).strip()
        if s == "":
            continue
        # normalize common formats (spaces, comma decimal)
        s_norm = s.replace(" ", "").replace(",", ".")
        try:
            val = float(s_norm)
        except Exception:
            non_numeric.append((feature, s))
            field_errors[feature] = f"Sayısal bir değer olmalı: '{s}'"
            continue

        if val < 0:
            negative_fields.append(feature)
            field_errors[feature] = "Negatif değer girilemez."

    messages: List[str] = []
    if non_numeric:
        messages.append(
            "Sayısal olmayan değerler: " + ", ".join(f"{f}='{v}'" for f, v in non_numeric)
        )
    if negative_fields:
        messages.append("Negatif değer girilemez: " + ", ".join(negative_fields))

    if field_errors:
        raise ValidationError("; ".join(messages), field_errors)


def convert_monthly_inputs_to_weekly(girdi: Mapping[str, float]) -> Dict[str, float]:
    """Model artık aylık çalıştığı için bu dönüşe gerek yok — girdiyi olduğu gibi döndürür."""
    return dict(girdi)


def clean_user_payload(payload: Mapping[str, Any]) -> Dict[str, float]:
    if hasattr(payload, "items"):
        source = {key: payload.get(key, 0) for key in INPUT_FEATURES}
    else:
        source = {key: payload[key] if key in payload else 0 for key in INPUT_FEATURES}

    transformed = INPUT_PIPELINE.transform([source])
    return {feature: float(value) for feature, value in zip(INPUT_FEATURES, transformed[0].tolist())}


def parse_identity(data: Mapping[str, Any]) -> Tuple[str, str]:
    # If user is authenticated, use account identity
    if current_user and getattr(current_user, "is_authenticated", False):
        ad = str(getattr(current_user, "ad", "") or getattr(current_user, "username", "") or getattr(current_user, "email", "")).strip()
        soyad = str(getattr(current_user, "soyad", "")).strip()
        if not ad:
            raise ValueError("Kullanici kimligi alinamadi. Lutfen tekrar giris yapiniz.")
        return ad, soyad

    ad = str(data.get("ad", "")).strip()
    soyad = str(data.get("soyad", "")).strip()
    if not ad or not soyad:
        raise ValueError("Lutfen ad ve soyad alanlarini doldurunuz.")
    return ad, soyad


def init_db() -> None:
    """Geçmiş emisyon kayıtlarını saklamak için tablo oluşturur.

    Not: Tablo adı `weekly_history` legacy adıdır ve gerçekte kullanıcı kayıtları
    hem aylık hem de birikimli giriş olarak kaydedilebilir.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS weekly_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad TEXT NOT NULL DEFAULT '',
                soyad TEXT NOT NULL DEFAULT '',
                user_id INTEGER NULL,
                electricity_kwh REAL NOT NULL DEFAULT 0.0,
                dogalgaz_m3 REAL NOT NULL DEFAULT 0.0,
                dolmus_km REAL NOT NULL DEFAULT 0.0,
                minibus_km REAL NOT NULL DEFAULT 0.0,
                otobus_km REAL NOT NULL DEFAULT 0.0,
                metro_km REAL NOT NULL DEFAULT 0.0,
                otomobil_km REAL NOT NULL DEFAULT 0.0,
                taksi_km REAL NOT NULL DEFAULT 0.0,
                tren_km REAL NOT NULL DEFAULT 0.0,
                gemi_km REAL NOT NULL DEFAULT 0.0,
                ucak_km REAL NOT NULL DEFAULT 0.0,
                kirmizi_et REAL NOT NULL DEFAULT 0.0,
                beyaz_et REAL NOT NULL DEFAULT 0.0,
                balik REAL NOT NULL DEFAULT 0.0,
                sut_urunleri REAL NOT NULL DEFAULT 0.0,
                yumurta REAL NOT NULL DEFAULT 0.0,
                sebzeler REAL NOT NULL DEFAULT 0.0,
                meyveler REAL NOT NULL DEFAULT 0.0,
                giyim REAL NOT NULL DEFAULT 0.0,
                elektronik REAL NOT NULL DEFAULT 0.0,
                hafta INTEGER NOT NULL DEFAULT 0,
                sehir_kodu INTEGER NOT NULL DEFAULT 0,
                arac_sahibi INTEGER NOT NULL DEFAULT 0,
                lag_1_co2 REAL NOT NULL DEFAULT 0.0,
                lag_2_co2 REAL NOT NULL DEFAULT 0.0,
                lag_3_co2 REAL NOT NULL DEFAULT 0.0,
                lag_4_co2 REAL NOT NULL DEFAULT 0.0,
                toplam_kg REAL NOT NULL DEFAULT 0.0,
                toplam_ton REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # create users table (with verification fields)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                ad TEXT NOT NULL DEFAULT '',
                soyad TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                verify_token TEXT
            )
            """
        )
        # Ensure users table has verification columns (migration)
        user_cols = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "ad" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN ad TEXT NOT NULL DEFAULT ''")
        if "soyad" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN soyad TEXT NOT NULL DEFAULT ''")
        if "is_verified" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
        if "verify_token" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN verify_token TEXT")
        cols = [row[1] for row in conn.execute("PRAGMA table_info(weekly_history)").fetchall()]
        if "ad" not in cols:
            conn.execute("ALTER TABLE weekly_history ADD COLUMN ad TEXT NOT NULL DEFAULT ''")
        if "soyad" not in cols:
            conn.execute("ALTER TABLE weekly_history ADD COLUMN soyad TEXT NOT NULL DEFAULT ''")
        if "user_id" not in cols:
            conn.execute("ALTER TABLE weekly_history ADD COLUMN user_id INTEGER NULL")
        # add 'ay' column used by HISTORY_COLUMNS and monthly aggregation
        if "ay" not in cols:
            conn.execute("ALTER TABLE weekly_history ADD COLUMN ay TEXT NOT NULL DEFAULT ''")
        for column in [
            "electricity_kwh",
            "dogalgaz_m3",
            "dolmus_km",
            "minibus_km",
            "otobus_km",
            "metro_km",
            "otomobil_km",
            "taksi_km",
            "tren_km",
            "gemi_km",
            "ucak_km",
            "kirmizi_et",
            "beyaz_et",
            "balik",
            "sut_urunleri",
            "yumurta",
            "sebzeler",
            "meyveler",
            "giyim",
            "elektronik",
            "hafta",
            "sehir_kodu",
            "arac_sahibi",
            "lag_1_co2",
            "lag_2_co2",
            "lag_3_co2",
            "lag_4_co2",
            "toplam_kg",
            "toplam_ton",
        ]:
            if column not in cols:
                conn.execute(f"ALTER TABLE weekly_history ADD COLUMN {column} REAL NOT NULL DEFAULT 0.0")
        conn.commit()

with app.app_context():
    # Veritabanı tablolarını otomatik oluştur
    init_db()


def send_verification_email(email_to: str, username: str, token: str) -> bool:
    """Try to send verification email if SMTP settings are configured. Returns True if sent."""
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", "587")) if os.environ.get("SMTP_PORT") else None
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user)
    if not smtp_server or not smtp_user or not smtp_pass:
        return False
    base_url = os.environ.get("BASE_URL", "http://localhost:5000").rstrip("/")
    verify_link = f"{base_url}/verify/{token}"
    msg = EmailMessage()
    msg["Subject"] = "Hesap Doğrulama"
    msg["From"] = smtp_from
    msg["To"] = email_to
    msg.set_content(f"Merhaba {username},\n\nLutfen hesabinizi aktiflestirmek icin asagidaki linke tiklayin:\n{verify_link}\n\nTesekkurler.")
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        return True
    except Exception as exc:
        try:
            app.logger.exception("Failed to send verification email to %s", email_to)
        except Exception:
            # logger may not be configured during early import; ignore
            pass
        return False


def get_user_by_username(username: str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT id, username, email, password_hash, is_verified, verify_token, ad, soyad FROM users WHERE username = ?", (username,)).fetchone()
    return row


def get_user_by_email(email: str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT id, username, email, password_hash, is_verified, verify_token, ad, soyad FROM users WHERE email = ?", (email,)).fetchone()
    return row


def delete_user(user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
        conn.commit()


def has_monthly_submission(user_id: int) -> bool:
    current_month = datetime.utcnow().strftime("%Y-%m")
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM weekly_history WHERE user_id = ? AND strftime('%Y-%m', created_at) = ? LIMIT 1",
            (int(user_id), current_month),
        ).fetchone()
    return row is not None


class User(UserMixin):
    def __init__(self, id_, username, email, ad, soyad, password_hash):
        self.id = id_
        self.username = username
        self.email = email
        self.ad = ad
        self.soyad = soyad
        self.password_hash = password_hash

    @staticmethod
    def get(user_id: int):
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT id, username, email, ad, soyad, password_hash FROM users WHERE id = ?", (int(user_id),)).fetchone()
        if row:
            return User(row[0], row[1], row[2], row[3], row[4], row[5])
        return None


def build_history_record(payload: Mapping[str, Any]) -> Dict[str, float]:
    return {field: safe_float(payload.get(field, 0), 0.0) for field in HISTORY_COLUMNS}


def save_weekly_total(ad: str, soyad: str, toplam_kg: float, toplam_ton: float, payload: Mapping[str, Any] = None) -> None:
    """Yeni hesaplanan toplam emisyonu ve girilen tüm alanları gecmise ekler."""
    payload = payload or {}
    record = build_history_record(payload)
    # include user_id if current_user is authenticated
    user_id = getattr(current_user, "id", None) if current_user and hasattr(current_user, "is_authenticated") and current_user.is_authenticated else None
    columns = ["ad", "soyad", "user_id"] + list(record.keys()) + ["toplam_kg", "toplam_ton"]
    placeholders = ",".join(["?" for _ in columns])
    values = [ad, soyad, user_id] + [record[field] for field in record] + [float(toplam_kg), float(toplam_ton)]

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"INSERT INTO weekly_history ({','.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )
        conn.commit()


def get_last_weekly_totals(ad: str = "", soyad: str = "", user_id: int = None, limit: int = 4) -> List[float]:
    """Son N kayıtlı toplam emisyonu (yeniden eskiye) döner."""
    with sqlite3.connect(DB_PATH) as conn:
        if user_id is not None:
            rows = conn.execute(
                "SELECT toplam_kg FROM weekly_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (int(user_id), int(limit)),
            ).fetchall()
        elif ad and soyad:
            rows = conn.execute(
                "SELECT toplam_kg FROM weekly_history WHERE ad = ? AND soyad = ? ORDER BY id DESC LIMIT ?",
                (ad, soyad, int(limit)),
            ).fetchall()
        else:
            return []
    return [float(row[0]) for row in rows]


def get_monthly_user_totals(ad: str = "", soyad: str = "", user_id: int = None, limit: int = 6) -> List[Dict[str, float]]:
    """Kullaniciya ait son N ayin toplam emisyonlarini doner."""
    with sqlite3.connect(DB_PATH) as conn:
        if user_id is not None:
            rows = conn.execute(
                """
                SELECT ay, aylik_toplam FROM (
                    SELECT strftime('%Y-%m', created_at) AS ay, SUM(toplam_kg) AS aylik_toplam
                    FROM weekly_history
                    WHERE user_id = ?
                    GROUP BY ay
                    ORDER BY ay DESC
                    LIMIT ?
                ) t
                ORDER BY ay ASC
                """,
                (int(user_id), int(limit)),
            ).fetchall()
        elif ad and soyad:
            rows = conn.execute(
                """
                SELECT ay, aylik_toplam FROM (
                    SELECT strftime('%Y-%m', created_at) AS ay, SUM(toplam_kg) AS aylik_toplam
                    FROM weekly_history
                    WHERE ad = ? AND soyad = ?
                    GROUP BY ay
                    ORDER BY ay DESC
                    LIMIT ?
                ) t
                ORDER BY ay ASC
                """,
                (ad, soyad, int(limit)),
            ).fetchall()
        else:
            return []
    return [{"ay": row[0], "toplam": round(float(row[1]), 2)} for row in rows]


def get_turkiye_benchmark(month_labels: Sequence[str]) -> List[float]:
    """
    Turkiye ortalamasi icin basit referans seri.
    Aylara gore kucuk mevsimsel fark eklenir.
    """
    seasonal = [1.02, 0.98, 0.96, 0.95, 0.94, 0.96, 1.01, 1.03, 1.00, 1.01, 1.05, 1.07]
    values = []
    for label in month_labels:
        month = int(label.split("-")[1])
        factor = seasonal[month - 1]
        values.append(round(TURKIYE_AYLIK_REFERANS_KG * factor, 2))
    return values


def get_default_monthly_lags(limit: int = 4) -> List[float]:
    """Return default monthly lag values for the last `limit` months."""
    today = datetime.now()
    labels: List[str] = []
    for i in range(limit):
        month_offset = limit - 1 - i
        year = today.year
        month = today.month - month_offset
        while month <= 0:
            month += 12
            year -= 1
        labels.append(f"{year}-{month:02d}")
    return list(reversed(get_turkiye_benchmark(labels)))


def with_auto_lags(form_data: Dict[str, str], ad: str, soyad: str, user_id: int = None) -> Dict[str, str]:
    """Lag alanlarini kullanicinin son aylik toplamlarina gore doldurur.

    Bu fonksiyon aylik ozetleri (`get_monthly_user_totals`) kullanir. Donen
    degerler en yeni ay icin `lag_1_co2`, bir onceki ay icin `lag_2_co2` vb.
    olarak atanir. Eger aylik ozet yoksa laglar 0.00 olarak kalir.
    """
    monthly = []
    if user_id is not None:
        monthly = get_monthly_user_totals(user_id=user_id, limit=4)
    elif ad and soyad:
        monthly = get_monthly_user_totals(ad, soyad, limit=4)
    else:
        monthly = []

    # `get_monthly_user_totals` returns rows oldest->newest; reverse to have newest first
    last_values: List[float] = []
    if monthly:
        vals = [row.get("toplam", 0.0) for row in monthly]
        last_values = list(reversed(vals))

    for i in range(4):
        key = f"lag_{i+1}_co2"
        if i < len(last_values):
            form_data[key] = f"{last_values[i]:.2f}"
        else:
            form_data[key] = f"{0.0:.2f}"
    return form_data


def build_simulation_input(data: Mapping[str, Any]) -> Tuple[Dict[str, float], float, float]:
    girdi = clean_user_payload(data)
    transport_reduction = safe_float(data.get("transport_reduction_pct", 0), 0.0)
    energy_reduction = safe_float(data.get("energy_reduction_pct", 0), 0.0)
    food_reduction = safe_float(data.get("food_reduction_pct", 0), 0.0)

    transport_factor = max(0.0, 1.0 - transport_reduction / 100.0)
    energy_factor = max(0.0, 1.0 - energy_reduction / 100.0)
    food_factor = max(0.0, 1.0 - food_reduction / 100.0)

    for key in SIMULATION_TRANSPORT_FEATURES:
        if key in girdi:
            girdi[key] = round(girdi[key] * transport_factor, 2)

    for key in SIMULATION_ENERGY_FEATURES:
        if key in girdi:
            girdi[key] = round(girdi[key] * energy_factor, 2)

    for key in SIMULATION_FOOD_FEATURES:
        if key in girdi:
            girdi[key] = round(girdi[key] * food_factor, 2)

    return girdi, transport_reduction, energy_reduction, food_reduction


def build_turkiye_demo_values() -> Dict[str, Any]:
    monthly_transport_km = constants.TURKIYE_ORTALAMA_KATSAYILARI["ulasim_km_per_hafta"] * WEEKS_PER_MONTH
    car_monthly_km = monthly_transport_km * constants.TURKIYE_ORTALAMA_KATSAYILARI["araba_sahibi_orani"]
    public_monthly_km = monthly_transport_km * constants.TURKIYE_ORTALAMA_KATSAYILARI["toplu_tasima_orani"]

    food_values_weekly = {
        "kirmizi_et": (
            gida_emisyon_sozlugu.TURKIYE_GIDA_TUKETIM_ORTALAMALARI.get("sığır_eti", 0.0)
            + gida_emisyon_sozlugu.TURKIYE_GIDA_TUKETIM_ORTALAMALARI.get("dana_eti", 0.0)
        ),
        "beyaz_et": gida_emisyon_sozlugu.TURKIYE_GIDA_TUKETIM_ORTALAMALARI.get("tavuk_eti", 0.0),
        "balik": gida_emisyon_sozlugu.TURKIYE_GIDA_TUKETIM_ORTALAMALARI.get("balik", 0.0),
        "sut_urunleri": gida_emisyon_sozlugu.TURKIYE_GIDA_TUKETIM_ORTALAMALARI.get("sut_ve_urunleri", 0.0),
        "yumurta": gida_emisyon_sozlugu.TURKIYE_GIDA_TUKETIM_ORTALAMALARI.get("yumurta", 0.0),
        "sebzeler": gida_emisyon_sozlugu.TURKIYE_GIDA_TUKETIM_ORTALAMALARI.get("sebzeler", 0.0),
        "meyveler": gida_emisyon_sozlugu.TURKIYE_GIDA_TUKETIM_ORTALAMALARI.get("meyveler", 0.0),
    }

    monthly_food_values = {
        name: round(value * WEEKS_PER_MONTH, 2)
        for name, value in food_values_weekly.items()
    }

    monthly_food_values["giyim"] = round(0.5 * WEEKS_PER_MONTH, 2)
    monthly_food_values["elektronik"] = round(0.2 * WEEKS_PER_MONTH, 2)

    return {
        "electricity_kwh": constants.TURKIYE_ORTALAMA_KATSAYILARI["elektrik_kwh_per_ay"],
        "dogalgaz_m3": constants.TURKIYE_ORTALAMA_KATSAYILARI["dogalgaz_m3_per_ay"],
        "otomobil_km": round(car_monthly_km),
        "taksi_km": round(car_monthly_km * 0.08),
        "otobus_km": round(public_monthly_km * 0.5),
        "metro_km": round(public_monthly_km * 0.35),
        "dolmus_km": round(public_monthly_km * 0.15),
        "tren_km": round(public_monthly_km * 0.05),
        "gemi_km": 5,
        "ucak_km": 5,
        **monthly_food_values,
    }


def kural_motoru(girdi: Mapping[str, float]) -> Dict[str, Any]:
    """Kural tabanli katman: faktorler ile toplam emisyonu hesaplar."""
    toplam_kg, kalemler = hesapla_toplam_emisyon(girdi)
    toplam_ton = toplam_kg / 1000
    return {
        "toplam_kg": round(toplam_kg, 2),
        "toplam_ton": round(toplam_ton, 3),
        "kalemler": {k: round(v, 2) for k, v in kalemler.items()},
    }


def _apply_input_multiplier(girdi: Mapping[str, float], multiplier: float) -> Dict[str, float]:
    """Multiply transport km and CO2-like inputs by multiplier before model.

    Rules: multiply any feature ending with '_km' and any feature starting with 'lag_'
    (historical CO2) so small user values become comparable to training scale.
    """
    if multiplier == 1:
        return dict(girdi)
    scaled = deepcopy(dict(girdi))
    for k in list(scaled.keys()):
        try:
            if k.endswith("_km") or k.startswith("lag_") or k.endswith("_co2"):
                scaled[k] = float(scaled.get(k, 0.0)) * multiplier
        except Exception:
            # leave value as-is on any unexpected error
            pass
    return scaled


def _descale_results(sonuc: Dict[str, Any], tahmin: Dict[str, Any], multiplier: float) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Divide model outputs by multiplier to return to user-scale.

    Modifies toplam_kg, toplam_ton and kalemler values, and ML gelecek_ay_kg.
    """
    if multiplier == 1:
        return sonuc, tahmin

    # Descale kural motoru result
    try:
        d_sonuc = deepcopy(sonuc)
        d_sonuc["toplam_kg"] = round(float(d_sonuc.get("toplam_kg", 0.0)) / multiplier, 2)
        d_sonuc["toplam_ton"] = round(float(d_sonuc.get("toplam_ton", 0.0)) / multiplier, 3)
        kalemler = d_sonuc.get("kalemler", {}) or {}
        d_sonuc["kalemler"] = {k: round(float(v) / multiplier, 2) for k, v in kalemler.items()}
    except Exception:
        d_sonuc = sonuc

    # Descale ML tahmin
    try:
        d_tahmin = deepcopy(tahmin)
        if "gelecek_ay_kg" in d_tahmin:
            d_tahmin["gelecek_ay_kg"] = round(float(d_tahmin.get("gelecek_ay_kg", 0.0)) / multiplier, 2)
    except Exception:
        d_tahmin = tahmin

    return d_sonuc, d_tahmin


def feature_label(feature_name: str) -> str:
    labels = {
        "dolmus_km": "Dolmuş kullanımı",
        "minibus_km": "Minibüs kullanımı",
        "otobus_km": "Otobüs kullanımı",
        "metro_km": "Metro kullanımı",
        "otomobil_km": "Otomobil kullanımı",
        "taksi_km": "Taksi kullanımı",
        "tren_km": "Tren kullanımı",
        "gemi_km": "Gemi seyahati",
        "ucak_km": "Uçak yolculuğu",
        "kirmizi_et": "Kırmızı et tüketimi",
        "beyaz_et": "Beyaz et tüketimi",
        "balik": "Balık tüketimi",
        "sut_urunleri": "Süt ürünleri tüketimi",
        "yumurta": "Yumurta (adet/ay)",
        "sebzeler": "Sebze tüketimi",
        "meyveler": "Meyve tüketimi",
        "giyim": "Giyim (adet/ay)",
        "elektronik": "Elektronik (saat/ay)",
        "electricity_kwh": "Elektrik tüketimi",
        "dogalgaz_m3": "Doğalgaz kullanımı",
        "arac_sahibi": "Araç sahibi olma durumu",
        "hafta": "Hafta numarası",
        "ay": "Ay numarası",
        "sehir_kodu": "Şehir kodu",
    }
    return labels.get(feature_name, feature_name.replace("_", " ").capitalize())


def build_shap_analysis(
    model: Any,
    model_features: Sequence[str],
    girdi: Mapping[str, float],
) -> List[str]:
    import pandas as pd
    import shap

    x = pd.DataFrame([{f: float(girdi.get(f, 0.0)) for f in model_features}])
    xgb_model = getattr(model, "xgb_model", None)
    if xgb_model is None:
        del x
        gc.collect()
        return []

    explainer = None
    shap_vals = None
    shap_arr = None
    shap_row = []
    try:
        explainer = shap.TreeExplainer(xgb_model)
        shap_vals = explainer.shap_values(x)
        shap_arr = np.array(shap_vals)
        if shap_arr.ndim == 2:
            shap_row = shap_arr[0].tolist()
        else:
            shap_row = shap_arr.flatten().tolist()
    except Exception:
        del x
        gc.collect()
        return []

    feature_items = []
    means = getattr(model, "feature_means", {}) or {}
    for idx, feature in enumerate(model_features):
        shap_value = float(shap_row[idx]) if idx < len(shap_row) else 0.0
        feature_items.append((feature, shap_value, float(x.iloc[0, idx])))

    pozitiv_items = [item for item in feature_items if item[1] > 0]
    if not pozitiv_items:
        return []

    pozitiv_items.sort(key=lambda item: item[1], reverse=True)
    top3 = pozitiv_items[:3]
    messages = []
    for feature, shap_value, value in top3:
        label = feature_label(feature)
        comparison = ""
        if feature in means:
            if value > means[feature]:
                comparison = "Türkiye ortalamasının üzerinde"
            elif value < means[feature]:
                comparison = "Türkiye ortalamasının altında"
            else:
                comparison = "Türkiye ortalamasına yakın"

        if feature == "kirmizi_et":
            messages.append(
                f"{label} modelde en fazla artıya katkı sağlıyor. Seviyeniz {comparison}; kırmızı eti azaltmak etkili bir adım olabilir."
            )
        elif feature in ["dolmus_km", "minibus_km", "otobus_km", "metro_km", "otomobil_km", "taksi_km", "tren_km", "gemi_km", "ucak_km"]:
            messages.append(
                f"{label}, emisyon tahminini yükselten bir diğer güçlü faktör. Mevcut seviye {comparison}. Toplu taşıma veya seyahat azaltımı fark yaratır."
            )
        elif feature in ["electricity_kwh", "dogalgaz_m3"]:
            messages.append(
                f"{label} modelde artıya güçlü katkıda bulunuyor. Enerji tüketimini düşürmek karbon ayak izinizi azaltacaktır."
            )
        elif feature.startswith("lag_"):
            messages.append(
                f"Geçmiş aylardaki {label} yüksek; geçmiş değerler tahmini yukarı çekiyor. Daha istikrarlı azalma için bu trende dikkat edin."
            )
        else:
            article = f"{label} şu anda tahmini artıran bir faktör. Mevcut seviye {comparison}."
            messages.append(article)

    if 'x' in locals():
        del x
    if 'explainer' in locals():
        del explainer
    if 'shap_vals' in locals():
        del shap_vals
    if 'shap_arr' in locals():
        del shap_arr
    gc.collect()

    return messages


def ml_tahmini(
    girdi: Mapping[str, float],
    kural_sonucu: Dict[str, Any],
    user_id: int | None = None,
) -> Dict[str, Any]:
    """
    ML katmani:
    - Hibrit MLP + XGBoost modeli ile gelecek ay emisyonunu tahmin eder.
    - Model yoksa kural motoru sonucunu baz alarak fallback deger dondurur.
    - Gerçek model veri kümesi gram cinsinden çıkış üretiyor; burada kg cinsine çeviriyoruz.
    """
    try:
        if not MODEL_PATH.exists():
            app.logger.warning(f"Model dosyası bulunamadı: {MODEL_PATH}")
            raise FileNotFoundError(f"Model yolu bulunamadı: {MODEL_PATH}")

        import hibrit_model_egit
        import joblib
        original_main = sys.modules.get("__main__")
        sys.modules["__main__"] = hibrit_model_egit
        try:
            model = joblib.load(MODEL_PATH)
        finally:
            if original_main is not None:
                sys.modules["__main__"] = original_main
            else:
                sys.modules.pop("__main__", None)

        if FEATURES_PATH.exists():
            model_features = joblib.load(FEATURES_PATH)
        else:
            app.logger.warning(f"Features dosyası bulunamadı: {FEATURES_PATH}, RULE_FEATURES kullanılıyor")
            model_features = RULE_FEATURES

        ml_girdi = dict(girdi)
        if user_id is not None:
            ml_girdi["user_id"] = float(user_id)
        else:
            ml_girdi.setdefault("user_id", 0.0)
        ml_girdi = convert_monthly_inputs_to_weekly(ml_girdi)

        x = [[ml_girdi.get(f, 0.0) for f in model_features]]
        tahmin = float(model.predict(x)[0]) / 1000.0
        analysis = build_shap_analysis(model, model_features, ml_girdi)
        app.logger.info(f"Model başarıyla yüklendi ve tahmin yapıldı: {tahmin:.2f} kgCO2e")
        del model
        del model_features
        gc.collect()
        return {
            "kaynak": "hibrit_model",
            "gelecek_ay_kg": round(max(tahmin, 0.0), 2),
            "analysis": analysis,
        }
    except Exception as exc:
        app.logger.exception(f"ML tahmini sırasında hata (model: {MODEL_PATH}): {exc}")

    return {
        "kaynak": "fallback",
        "gelecek_ay_kg": round(max(kural_sonucu.get("toplam_kg", 0.0), 0.0), 2),
        "analysis": [],
    }

def uretilen_aksiyon_mesaji(
    sonuc: Dict[str, Any],
    tahmin: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Kural sonucu + ML tahmini uzerinden kullaniciya aksiyon odakli yorum uretir.
    """
    toplam = float(sonuc["toplam_kg"])
    gelecek = float(tahmin.get("gelecek_ay_kg", tahmin.get("gelecek_hafta_kg", 0.0)))
    kalemler = sonuc.get("kalemler", {})
    en_yuksek_kalem = max(kalemler, key=kalemler.get) if kalemler else ""
    en_yuksek_deger = float(kalemler.get(en_yuksek_kalem, 0.0))

    if toplam >= 200:
        seviye = "yuksek"
    elif toplam >= 110:
        seviye = "orta"
    else:
        seviye = "dusuk"

    hedef_azaltim = round(max(toplam * 0.15, 5.0), 2)
    gelecek_fark = round(gelecek - toplam, 2)
    trend_mesaji = (
        f"ML tahminine gore gelecek donemde +{gelecek_fark:.2f} kg artis bekleniyor."
        if gelecek_fark > 0
        else f"ML tahminine gore gelecek donemde {-gelecek_fark:.2f} kg iyilesme bekleniyor."
    )

    def _kategori_yuksek_kalem(keys: set[str]) -> str | None:
        positif_kalemler = [k for k in keys if float(kalemler.get(k, 0.0)) > 0.0]
        if not positif_kalemler:
            return None
        return max(positif_kalemler, key=lambda k: float(kalemler.get(k, 0.0)))

    def _bolum_aylik_hedef(kalem: str, hedef_kw: float) -> float:
        deger = float(kalemler.get(kalem, 0.0))
        return round(hedef_kw * WEEKS_PER_MONTH * (deger / max(toplam, 1.0)), 2)

    bolum_onerileri: Dict[str, List[str]] = {
        "Enerji": [],
        "Ulaşım": [],
        "Gıda": [],
        "Genel": [],
    }
    oneriler = []

    enerji_kalemleri = {"elektrik", "dogalgaz"}
    en_yuksek_enerji = _kategori_yuksek_kalem(enerji_kalemleri)
    if en_yuksek_enerji == "elektrik":
        aylik_hedef = _bolum_aylik_hedef("elektrik", hedef_azaltim)
        mesaj = (
            "Elektrik tuketimi ana kaynak; bosta kalan cihazlari kapatip LED kullanimini arttir, "
            "cihazlari prizden cek ve gereksiz standby harcamalarini azalt. "
            f"Gelecek ay icin elektrikten en az {aylik_hedef:.2f} kgCO2e azaltim hedefle."
        )
        bolum_onerileri["Enerji"].append(mesaj)
        oneriler.append(mesaj)
    elif en_yuksek_enerji == "dogalgaz":
        aylik_hedef = _bolum_aylik_hedef("dogalgaz", hedef_azaltim)
        mesaj = (
            "Dogalgaz tuketimi yuksek; yalıtımı iyilestir, petekleri ve kaloriferi dusuk ayarda kullan, "
            "gereksiz isitmayi azalt. "
            f"Gelecek ay icin dogalgazda en az {aylik_hedef:.2f} kgCO2e azaltima odaklan."
        )
        bolum_onerileri["Enerji"].append(mesaj)
        oneriler.append(mesaj)

    tasima_kalemleri = {"dolmus", "minibus", "otobus", "metro", "otomobil", "taksi", "tren", "gemi", "ucak"}
    en_yuksek_tasim = _kategori_yuksek_kalem(tasima_kalemleri)
    if en_yuksek_tasim == "otomobil":
        aylik_hedef = _bolum_aylik_hedef("otomobil", hedef_azaltim)
        mesaj = (
            "Otomobil emisyonu yuksek; haftada en az 2 gun toplu tasimaya gec, "
            "aracin bakimini yap ve arac paylasimini dusun. "
            f"Gelecek ay icin bu sekilde en az {aylik_hedef:.2f} kgCO2e azaltim yapmayi hedefle."
        )
        bolum_onerileri["Ulaşım"].append(mesaj)
        oneriler.append(mesaj)
    elif en_yuksek_tasim == "ucak":
        aylik_hedef = _bolum_aylik_hedef("ucak", hedef_azaltim)
        mesaj = (
            "Ucak kaynakli emisyon baskin; mumkunse kisa mesafe ucuslar yerine otobus veya tren sec, "
            "seyahat planini yeniden gozden gecir. "
            f"Gelecek ay icin ucak yerine karbonsuz alternatiflerle en az {aylik_hedef:.2f} kgCO2e azaltim hedefle."
        )
        bolum_onerileri["Ulaşım"].append(mesaj)
        oneriler.append(mesaj)
    elif en_yuksek_tasim in {"dolmus", "otobus", "metro", "taksi", "tren", "gemi"}:
        aylik_hedef = _bolum_aylik_hedef(en_yuksek_tasim, hedef_azaltim)
        mesaj = (
            "Toplu tasima veya alternatif seyahat secenekleri kullan; aktarma planini iyilestir "
            "ve bireysel arac kullanimi azalt. "
            f"Gelecek ay icin bu bolumde en az {aylik_hedef:.2f} kgCO2e azaltma hedefin olsun."
        )
        bolum_onerileri["Ulaşım"].append(mesaj)
        oneriler.append(mesaj)

    gida_kalemleri = {
        "kirmizi_et",
        "beyaz_et",
        "balik",
        "sut_urunleri",
        "yumurta",
        "sebzeler",
        "meyveler",
        "giyim",
        "elektronik",
    }
    en_yuksek_gida = _kategori_yuksek_kalem(gida_kalemleri)
    if en_yuksek_gida == "kirmizi_et":
        aylik_hedef = _bolum_aylik_hedef("kirmizi_et", hedef_azaltim)
        mesaj = (
            "Kirmizi et tuketimi en yuksek kalem; porsiyonlari azalt, bitkisel proteinleri artir "
            "ve hafta ici en az bir gun et yememeye calis. "
            f"Gelecek ay icin bu alanda en az {aylik_hedef:.2f} kgCO2e azaltim hedefle."
        )
        bolum_onerileri["Gıda"].append(mesaj)
        oneriler.append(mesaj)
    elif en_yuksek_gida == "beyaz_et":
        aylik_hedef = _bolum_aylik_hedef("beyaz_et", hedef_azaltim)
        mesaj = (
            "Beyaz et tuketimini dengeli tut; bitkisel bazli alternatiflere yer ver ve porsiyonlari kisalt. "
            f"Gelecek ay icin bu bolumde en az {aylik_hedef:.2f} kgCO2e azaltma hedefi belirle."
        )
        bolum_onerileri["Gıda"].append(mesaj)
        oneriler.append(mesaj)
    elif en_yuksek_gida == "balik":
        aylik_hedef = _bolum_aylik_hedef("balik", hedef_azaltim)
        mesaj = (
            "Balik tuketimi yuksek; yerel ve mevsimsel secimler yap, taze baliklar yerine daha az karbon ayak izine sahip alternatifleri de dene. "
            f"Gelecek ay icin bu bolumde en az {aylik_hedef:.2f} kgCO2e azaltim hedefle."
        )
        bolum_onerileri["Gıda"].append(mesaj)
        oneriler.append(mesaj)
    elif en_yuksek_gida:
        aylik_hedef = _bolum_aylik_hedef(en_yuksek_gida, hedef_azaltim)
        mesaj = (
            "Gida tuketiminde dengeli secimler yap; tuketimi azalt, meyve-sebze oranini artir "
            "ve israfi onlemek icin porsiyonlari kontrol et. "
            f"Gelecek ay icin bu bolumde en az {aylik_hedef:.2f} kgCO2e azaltim hedefle."
        )
        bolum_onerileri["Gıda"].append(mesaj)
        oneriler.append(mesaj)

    if not any(bolum_onerileri[k] for k in ("Enerji", "Ulaşım", "Gıda")):
        mesaj = "En yuksek emisyon kalemine odaklanip haftalik tuketimi duzenli takip et."
        bolum_onerileri["Genel"].append(mesaj)
        oneriler.append(mesaj)

    genel_hedef = f"Bir sonraki donem icin hedefin en az {hedef_azaltim:.2f} kgCO2e azaltim olsun."
    bolum_onerileri["Genel"].append(genel_hedef)
    oneriler.append(genel_hedef)
    bolum_onerileri["Genel"].append(trend_mesaji)
    oneriler.append(trend_mesaji)

    analiz_metni = (
        f"Karbon ayak izin su an {seviye} seviyede ({toplam:.2f} kgCO2e). "
        f"En yuksek kalem: {en_yuksek_kalem} ({en_yuksek_deger:.2f} kgCO2e)."
    )

    return {"analiz": analiz_metni, "oneriler": oneriler, "bolum_onerileri": bolum_onerileri}


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    form_data = build_blank_form_data()
    error = ""
    field_errors: Dict[str, str] = {}
    sonuc = None
    tahmin = None
    sonuc_kisi = ""
    aksiyon = None
    analysis = []

    if request.method == "POST":
        # Giriş yapmış kullanıcının bu ay kaydı olup olmadığını kontrol et
        if current_user and getattr(current_user, "is_authenticated", False) and has_monthly_submission(int(current_user.id)):
            error = "Bu ay için zaten veri girdiniz. Bir sonraki aya kadar yeni kayıt yapamazsınız."
            # Hata durumunda form render edip return et (kayıt yapma)
            user_history = []
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    rows = conn.execute(
                        "SELECT id, created_at, toplam_kg, toplam_ton FROM weekly_history WHERE user_id = ? ORDER BY id DESC LIMIT 20",
                        (int(current_user.id),),
                    ).fetchall()
                user_history = [dict(id=row[0], created_at=row[1], toplam_kg=row[2], toplam_ton=row[3]) for row in rows]
            except:
                pass
            return render_template(
                "index.html",
                form_data=form_data,
                error=error,
                field_errors={},
                sonuc=None,
                tahmin=None,
                aksiyon=None,
                analysis=[],
                sonuc_kisi="",
                model_hazir=MODEL_PATH.exists(),
                current_user=current_user,
                user_history=user_history,
            )
        
        # Formdan gelen sayısal verileri güvenli bir şekilde sözlüğe aktar ve eksik alanları "0" yap
        form_payload = {f: request.form.get(f, "0").strip() for f in RULE_FEATURES + ML_EXTRA_FEATURES}
        
        # Giriş yapan kullanıcının adını ve soyadını direkt oturumdan alıyoruz
        ad = str(getattr(current_user, "ad", "") or getattr(current_user, "username", "") or getattr(current_user, "email", "")).strip()
        soyad = str(getattr(current_user, "soyad", "")).strip()

        try:
            # payload'u valide ediyoruz
            validate_inputs(form_payload)
            girdi = clean_user_payload(form_payload)
            
            multiplier = float(app.config.get('INPUT_MULTIPLIER', 1))
            scaled_girdi = _apply_input_multiplier(girdi, multiplier)
            raw_sonuc = kural_motoru(scaled_girdi)
            raw_tahmin = ml_tahmini(scaled_girdi, raw_sonuc, getattr(current_user, 'id', None))
            sonuc, tahmin = _descale_results(raw_sonuc, raw_tahmin, multiplier)
            analysis = tahmin.get("analysis", [])
            aksiyon = uretilen_aksiyon_mesaji(sonuc, tahmin)
            sonuc_kisi = ad  # Sadece username gösterilecek
            CHAT_STATE["last_result"] = sonuc
            
            save_weekly_total(ad, soyad, sonuc["toplam_kg"], sonuc["toplam_ton"], form_payload)
            
            session["last_index_result"] = {
                "sonuc": sonuc,
                "tahmin": tahmin,
                "aksiyon": aksiyon,
                "analysis": analysis,
                "sonuc_kisi": sonuc_kisi,
            }
            return redirect(url_for("index"))
            
        except ValidationError as exc:
            error = str(exc)  # Validation hatasının tam mesajını göster
            field_errors = exc.field_errors
            # Hata durumunda girilen verilerin kutulardan silinmesini engeller
            form_data.update(form_payload)
            # HATA VAR, HEMEN SAYFAYI DÖN
            return render_template(
                "index.html",
                form_data=form_data,
                error=error,
                field_errors=field_errors,
                sonuc=None,
                tahmin=None,
                aksiyon=None,
                analysis=[],
                sonuc_kisi="",
                model_hazir=MODEL_PATH.exists(),
                current_user=current_user,
                user_history=[],
            )
        except Exception as e:
            app.logger.exception("Hesaplama sırasında beklenmeyen hata")
            error = f"Hesaplama hatası: {str(e)}"
            # Genel bir hata olsa bile kullanıcının girdiği verileri koruyoruz
            form_data.update(form_payload)
            # HATA VAR, HEMEN SAYFAYI DÖN
            return render_template(
                "index.html",
                form_data=form_data,
                error=error,
                field_errors={},
                sonuc=None,
                tahmin=None,
                aksiyon=None,
                analysis=[],
                sonuc_kisi="",
                model_hazir=MODEL_PATH.exists(),
                current_user=current_user,
                user_history=[],
            )

    # restore result after successful POST redirect
    saved_result = session.pop("last_index_result", None)
    if saved_result:
        sonuc = saved_result.get("sonuc")
        tahmin = saved_result.get("tahmin")
        aksiyon = saved_result.get("aksiyon")
        analysis = saved_result.get("analysis", [])
        sonuc_kisi = saved_result.get("sonuc_kisi", "")

    # fetch user-specific history if logged in
    user_history = []
    if current_user and getattr(current_user, "is_authenticated", False):
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id, created_at, toplam_kg, toplam_ton FROM weekly_history WHERE user_id = ? ORDER BY id DESC LIMIT 20",
                (int(current_user.id),),
            ).fetchall()
        user_history = [dict(id=row[0], created_at=row[1], toplam_kg=row[2], toplam_ton=row[3]) for row in rows]

    return render_template(
        "index.html",
        form_data=form_data,
        error=error,
        field_errors=field_errors,
        sonuc=sonuc,
        tahmin=tahmin,
        aksiyon=aksiyon,
        analysis=analysis,
        sonuc_kisi=sonuc_kisi,
        model_hazir=MODEL_PATH.exists(),
        current_user=current_user,
        user_history=user_history,
    )


@app.get("/history_record/<int:record_id>")
@login_required
def history_record(record_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM weekly_history WHERE id = ? AND user_id = ?",
            (int(record_id), int(current_user.id)),
        ).fetchone()
    if not row:
        return jsonify({"error": "Kayıt bulunamadı veya yetkiniz yok."}), 404

    record = {key: row[key] for key in row.keys() if key not in {"user_id", "id"}}
    payload = {field: record.get(field, 0) for field in HISTORY_COLUMNS}
    multiplier = float(app.config.get("INPUT_MULTIPLIER", 1))
    scaled_girdi = _apply_input_multiplier(clean_user_payload(payload), multiplier)
    raw_sonuc = kural_motoru(scaled_girdi)
    raw_tahmin = ml_tahmini(scaled_girdi, raw_sonuc, getattr(current_user, 'id', None))
    sonuc, tahmin = _descale_results(raw_sonuc, raw_tahmin, multiplier)
    aksiyon = uretilen_aksiyon_mesaji(sonuc, tahmin)

    return jsonify(
        {
            "created_at": record.get("created_at"),
            "form": payload,
            "kural": sonuc,
            "tahmin": tahmin,
            "aksiyon": aksiyon,
            "analysis": tahmin.get("analysis", []),
        }
    )


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.post("/chat")
def chat():
    """Intent + bilgi getirimi kullanan chatbot endpoint'i."""
    payload = request.get_json(silent=True) or {}
    mesaj = str(payload.get("message", "")).strip()
    if not mesaj:
        return jsonify({"answer": "Bos mesaj algilandi. Bir soru yazar misin?"}), 400

    chat_context = {
        "turn_count": CHAT_STATE["turn_count"],
        "last_result": CHAT_STATE["last_result"],
    }
    response = generate_chat_reply(mesaj, chat_context)
    CHAT_STATE["turn_count"] += 1

    return jsonify({"answer": response["answer"], "intent": response["intent"]})


@app.post("/tahmin")
@login_required
def tahmin_api():
    """JSON girdi ile kural + ML sonucunu API olarak dondurur."""
    payload = request.get_json(silent=True) or {}
    try:
        validate_inputs(payload)
        ad, soyad = parse_identity(payload)
        girdi = clean_user_payload(payload)
        multiplier = float(app.config.get('INPUT_MULTIPLIER', 1))
        scaled_girdi = _apply_input_multiplier(girdi, multiplier)
        raw_sonuc = kural_motoru(scaled_girdi)
        raw_tahmin = ml_tahmini(scaled_girdi, raw_sonuc, getattr(current_user, 'id', None))
        sonuc, tahmin = _descale_results(raw_sonuc, raw_tahmin, multiplier)
        aksiyon = uretilen_aksiyon_mesaji(sonuc, tahmin)
        CHAT_STATE["last_result"] = sonuc
        save_weekly_total(ad, soyad, sonuc["toplam_kg"], sonuc["toplam_ton"], payload)
        return jsonify({"kural": sonuc, "tahmin": tahmin, "aksiyon": aksiyon})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400



@app.post('/api/auto_fill_lags')
@limiter.limit("10 per minute")
def api_auto_fill_lags():
    """Return last 4 monthly totals for lag auto-fill.

    If the user is authenticated, use their `user_id`. Otherwise the client
    may send `ad` and `soyad` in JSON to try to resolve historic totals.
    """
    payload = request.get_json(silent=True) or {}
    monthly = []
    if current_user and getattr(current_user, 'is_authenticated', False):
        try:
            monthly = get_monthly_user_totals(user_id=current_user.id, limit=4)
        except Exception:
            monthly = []
    else:
        ad = str(payload.get('ad', '')).strip()
        soyad = str(payload.get('soyad', '')).strip()
        if ad and soyad:
            try:
                monthly = get_monthly_user_totals(ad, soyad, limit=4)
            except Exception:
                monthly = []

    # monthly is oldest->newest; reverse to get newest first
    last_values = []
    if monthly and any(float(row.get('toplam', 0.0)) > 0 for row in monthly):
        last_values = list(reversed([row.get('toplam', 0.0) for row in monthly]))
    else:
        last_values = get_default_monthly_lags(4)

    result = {}
    for i in range(4):
        key = f'lag_{i+1}_co2'
        result[key] = round(last_values[i], 2) if i < len(last_values) else 0.0

    return jsonify(result)


@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        ad = request.form.get('ad', '').strip()
        soyad = request.form.get('soyad', '').strip()
        password = request.form.get('password', '')
        # basic password policy: min 8, contains digit and letter
        if not username or not email or not ad or not soyad or not password:
            error = 'Lutfen tum alanlari doldurunuz.'
        elif len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
            error = 'Sifre en az 8 karakter, en az bir harf ve bir rakam icermelidir.'
        else:
            existing = get_user_by_username(username)
            existing_email = get_user_by_email(email)
            if existing and existing[4]:
                error = 'Kullanici adi zaten alinmis.'
            elif existing_email and existing_email[4]:
                error = 'Email zaten alinmis.'
            else:
                if existing and not existing[4]:
                    delete_user(existing[0])
                if existing_email and not existing_email[4] and (not existing or existing_email[0] != existing[0]):
                    delete_user(existing_email[0])
                password_hash = generate_password_hash(password)
                verify_token = secrets.token_urlsafe(24)
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute(
                        'INSERT INTO users (username, email, ad, soyad, password_hash, is_verified, verify_token) VALUES (?, ?, ?, ?, ?, 0, ?)',
                        (username, email, ad, soyad, password_hash, verify_token),
                    )
                    conn.commit()
                sent = send_verification_email(email, username, verify_token)
                if sent:
                    flash('Kayit basarili. Lutfen email adresinizi kontrol ederek hesabinizi dogrulayiniz.')
                    return redirect(url_for('login'))
                else:
                    delete_user(get_user_by_username(username)[0])
                    error = 'Doğrulama e-postası gönderilemedi. SMTP ayarlarınızı veya e-posta sunucunuzu kontrol ediniz.'
    return render_template('register.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user_row = get_user_by_username(username)
        if not user_row:
            error = 'Gecersiz kullanici adi veya sifre.'
        else:
            uid, uname, email, password_hash, *rest = user_row
            # fetch verification status if present
            with sqlite3.connect(DB_PATH) as conn:
                vrow = conn.execute('SELECT is_verified FROM users WHERE id = ?', (uid,)).fetchone()
            is_verified = bool(vrow[0]) if vrow else False
            if not is_verified:
                error = 'Hesabiniz dogrulanmamis. Lutfen e-posta adresinizi kontrol edin.'
            elif check_password_hash(password_hash, password):
                # fetch ad/soyad from the stored user row if available
                ad = ''
                soyad = ''
                if len(user_row) >= 8:
                    ad = user_row[6] or ''
                    soyad = user_row[7] or ''
                user = User(uid, uname, email, ad, soyad, password_hash)
                login_user(user)
                flash('Basariyla giris yapildi.')
                return redirect(url_for('index'))
            else:
                error = 'Gecersiz kullanici adi veya sifre.'
    return render_template('login.html', error=error)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Cikis yapildi.')
    return redirect(url_for('index'))


@app.post("/simulate")
@login_required
def simulate_api():
    """JSON girdi ile slider bazlı karbon azaltma simülasyonunu dondurur."""
    payload = request.get_json(silent=True) or {}
    try:
        validate_inputs(payload)
        # baseline (original) input
        original_girdi = clean_user_payload(payload)
        # reduced input according to sliders
        reduced_girdi, transport_pct, energy_pct, food_pct = build_simulation_input(payload)

        multiplier = float(app.config.get('INPUT_MULTIPLIER', 1))

        # scale for model internals
        scaled_original = _apply_input_multiplier(original_girdi, multiplier)
        scaled_reduced = _apply_input_multiplier(reduced_girdi, multiplier)

        # compute baseline and reduced rule-engine results
        raw_baseline = kural_motoru(scaled_original)
        raw_sonuc = kural_motoru(scaled_reduced)

        # ML prediction based on reduced (simulated) input
        raw_tahmin = ml_tahmini(scaled_reduced, raw_sonuc, getattr(current_user, 'id', None))

        # descale results for user display
        d_baseline, _ = _descale_results(raw_baseline, raw_tahmin, multiplier)
        sonuc, tahmin = _descale_results(raw_sonuc, raw_tahmin, multiplier)

        # compute category deltas (baseline - reduced)
        def sum_keys(d, keys):
            kal = d.get('kalemler', {}) or {}
            return sum(float(kal.get(k, 0.0)) for k in keys)

        transport_baseline = sum_keys(d_baseline, SIMULATION_TRANSPORT_EMISSION_KEYS)
        transport_reduced = sum_keys(sonuc, SIMULATION_TRANSPORT_EMISSION_KEYS)
        transport_delta = round(transport_baseline - transport_reduced, 2)

        energy_baseline = sum_keys(d_baseline, SIMULATION_ENERGY_EMISSION_KEYS)
        energy_reduced = sum_keys(sonuc, SIMULATION_ENERGY_EMISSION_KEYS)
        energy_delta = round(energy_baseline - energy_reduced, 2)

        food_baseline = sum_keys(d_baseline, SIMULATION_FOOD_FEATURES)
        food_reduced = sum_keys(sonuc, SIMULATION_FOOD_FEATURES)
        food_delta = round(food_baseline - food_reduced, 2)

        return jsonify(
            {
                "simulation": {
                    "transport_reduction_pct": transport_pct,
                    "energy_reduction_pct": energy_pct,
                    "food_reduction_pct": food_pct,
                    "kaynak": "kural_model",
                    "gelecek_ay_kg": round(sonuc.get("toplam_kg", 0.0), 2),
                    "ml_gelecek_ay_kg": tahmin.get("gelecek_ay_kg", tahmin.get("gelecek_hafta_kg")),
                    "toplam_kg": sonuc["toplam_kg"],
                    "toplam_ton": sonuc["toplam_ton"],
                    "baseline": {
                        "transport": round(transport_baseline, 2),
                        "energy": round(energy_baseline, 2),
                        "food": round(food_baseline, 2),
                    },
                    "reduced": {
                        "transport": round(transport_reduced, 2),
                        "energy": round(energy_reduced, 2),
                        "food": round(food_reduced, 2),
                    },
                    "delta": {
                        "transport": transport_delta,
                        "energy": energy_delta,
                        "food": food_delta,
                    },
                }
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400



@app.route('/verify/<token>')
def verify_user(token):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute('SELECT id FROM users WHERE verify_token = ?', (token,)).fetchone()
        if not row:
            flash('Gecersiz veya hatali dogrulama linki.')
            return redirect(url_for('login'))
        uid = row[0]
        conn.execute('UPDATE users SET is_verified = 1, verify_token = NULL WHERE id = ?', (uid,))
        conn.commit()
    flash('Hesabiniz dogrulandi. Lutfen giris yapin.')
    return redirect(url_for('login'))


@app.get("/laglar")
def laglar_api():
    # Prefer authenticated user's monthly history
    user_id = None
    if current_user and getattr(current_user, "is_authenticated", False):
        user_id = int(current_user.id)
        ad = str(getattr(current_user, "ad", "") or getattr(current_user, "username", "") or getattr(current_user, "email", "")).strip()
        soyad = str(getattr(current_user, "soyad", "")).strip()
    else:
        ad = str(request.args.get("ad", "")).strip()
        soyad = str(request.args.get("soyad", "")).strip()

    if user_id is None and not (ad and soyad):
        defaults = get_default_monthly_lags(4)
        return jsonify(
            {
                "lag_1_co2": round(defaults[0], 2),
                "lag_2_co2": round(defaults[1], 2),
                "lag_3_co2": round(defaults[2], 2),
                "lag_4_co2": round(defaults[3], 2),
            }
        )

    # use monthly aggregates for lag values
    if user_id is not None:
        monthly = get_monthly_user_totals(user_id=user_id, limit=4)
    else:
        monthly = get_monthly_user_totals(ad, soyad, limit=4)

    # monthly returned oldest->newest; reverse to have newest first
    vals = [row.get('toplam', 0.0) for row in monthly] if monthly else []
    last_values = [float(v) for v in reversed(vals) if float(v) and float(v) > 0]

    lag_map = {}
    if last_values:
        computed = list(reversed([float(row.get('toplam', 0.0)) for row in monthly]))
        if any(v > 0 for v in computed):
            last_values = computed
        else:
            last_values = get_default_monthly_lags(4)
    else:
        last_values = get_default_monthly_lags(4)

    for i in range(4):
        lag_map[f"lag_{i+1}_co2"] = round(last_values[i], 2) if i < len(last_values) else DEFAULT_LAGS[i]
    return jsonify(lag_map)


@app.get("/turkiye_demo_degerleri")
def turkiye_demo_degerleri():
    return jsonify(build_turkiye_demo_values())


@app.get("/grafik_veri")
def grafik_veri_api():
    # Use authenticated user's history if available
    user_id = None
    if current_user and getattr(current_user, "is_authenticated", False):
        user_id = int(current_user.id)
        ad = str(getattr(current_user, "ad", "") or getattr(current_user, "username", "") or getattr(current_user, "email", "")).strip()
        soyad = str(getattr(current_user, "soyad", "")).strip()
    else:
        ad = str(request.args.get("ad", "")).strip()
        soyad = str(request.args.get("soyad", "")).strip()

    if user_id is None and not (ad and soyad):
        return jsonify({"error": "Grafik icin kullanici girisi gerekli."}), 400

    aylik = get_monthly_user_totals(ad, soyad, user_id=user_id, limit=8)
    if not aylik:
        return jsonify({"error": "Bu kullanici icin henuz aylik veri yok."}), 404

    labels = [x["ay"] for x in aylik]
    user_values = [x["toplam"] for x in aylik]
    tr_values = get_turkiye_benchmark(labels)
    user_avg = round(sum(user_values) / len(user_values), 2)
    tr_avg = round(sum(tr_values) / len(tr_values), 2)
    diff_pct = round(((user_avg - tr_avg) / tr_avg) * 100, 2) if tr_avg else 0.0
    durum = "ustunde" if diff_pct > 0 else "altinda"
    return jsonify(
        {
            "labels": labels,
            "kullanici": user_values,
            "turkiye": tr_values,
            "kullanici_adi": f"{ad} {soyad}",
            "user_avg": user_avg,
            "tr_avg": tr_avg,
            "diff_pct": diff_pct,
            "durum": durum,
            "referans_notu": "Turkiye serisi ortalama referans degerdir.",
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
