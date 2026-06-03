"""
Gerçek Türkiye emisyon verileriyle LinearRegression model eğitimi
Geçmiş yılların trendini öğrenip gelecek haftayı tahmin eder
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import constants

# Türkiye emisyon verisini yükle
def load_turkey_emissions():
    """Türkiye emisyon verilerini yükle ve temizle"""
    df = pd.read_csv("data/turkiye_emisyon.csv")
    
    # Sütunları temizle
    df.columns = df.columns.str.replace('"', '').str.strip()
    df['Category'] = pd.to_numeric(df['Category'])
    
    # Sadece son 20 yılı kullan (2004-2024)
    df_recent = df[df['Category'] >= 2004].copy()
    
    # Yıllık büyüme oranlarını hesapla
    df_recent['transport_growth'] = df_recent['Transport'].pct_change()
    df_recent['power_growth'] = df_recent['Power Industry'].pct_change()
    df_recent['buildings_growth'] = df_recent['Buildings'].pct_change()
    
    return df_recent

def create_features(df):
    """Model için özellikler oluştur"""
    features = []
    targets = []
    
    for i in range(5, len(df)):  # 5 yıllık geçmiş veriyle tahmin
        # Son 5 yılın verileri
        window = df.iloc[i-5:i]
        
        # Özellikler
        feature_row = {
            'year': df.iloc[i]['Category'],
            'transport_5y_avg': window['Transport'].mean(),
            'transport_5y_trend': (window['Transport'].iloc[-1] - window['Transport'].iloc[0]) / 5,
            'power_5y_avg': window['Power Industry'].mean(),
            'power_5y_trend': (window['Power Industry'].iloc[-1] - window['Power Industry'].iloc[0]) / 5,
            'buildings_5y_avg': window['Buildings'].mean(),
            'buildings_5y_trend': (window['Buildings'].iloc[-1] - window['Buildings'].iloc[0]) / 5,
            'total_5y_avg': (window['Transport'] + window['Power Industry'] + window['Buildings']).mean(),
            'year_position': i / len(df),  # Yılın konumu (0-1)
        }
        
        # Hedef değişkenler (bir sonraki yıl)
        target_row = df.iloc[i+1] if i+1 < len(df) else df.iloc[i]
        
        targets.append({
            'transport_next': target_row['Transport'],
            'power_next': target_row['Power Industry'],
            'buildings_next': target_row['Buildings'],
            'total_next': target_row['Transport'] + target_row['Power Industry'] + target_row['Buildings']
        })
        
        features.append(feature_row)
    
    return pd.DataFrame(features), pd.DataFrame(targets)

def train_linear_regression():
    """LinearRegression model eğit"""
    print("🤖 GERÇEK TÜRKİYE VERİLERİYLE MODEL EĞİTİMİ")
    print("=" * 60)
    
    # Veriyi yükle
    df = load_turkey_emissions()
    print(f"📊 Veri aralığı: {df['Category'].min()} - {df['Category'].max()}")
    print(f"📊 Toplam yıl: {len(df)}")
    
    # Özellik ve hedef setleri oluştur
    X, y = create_features(df)
    
    print(f"🎯 Özellik sayısı: {X.shape[1]}")
    print(f"🎯 Eğitim örnek sayısı: {len(X)}")
    
    # Model eğitimi için her sektör ayrı ayrı
    models = {}
    scalers = {}
    
    for sector in ['transport', 'power', 'buildings', 'total']:
        print(f"\n🔧 {sector.upper()} sektörü için model eğitiliyor...")
        
        # Özellik seçimi
        if sector == 'transport':
            feature_cols = ['transport_5y_avg', 'transport_5y_trend', 'year_position']
            target_col = 'transport_next'
        elif sector == 'power':
            feature_cols = ['power_5y_avg', 'power_5y_trend', 'year_position']
            target_col = 'power_next'
        elif sector == 'buildings':
            feature_cols = ['buildings_5y_avg', 'buildings_5y_trend', 'year_position']
            target_col = 'buildings_next'
        else:  # total
            feature_cols = ['total_5y_avg', 'transport_5y_trend', 'power_5y_trend', 'year_position']
            target_col = 'total_next'
        
        X_sector = X[feature_cols]
        y_sector = y[target_col]
        
        # Veriyi ölçeklendir
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_sector)
        
        # Model eğit
        model = LinearRegression()
        model.fit(X_scaled, y_sector)
        
        # Performans değerlendirme
        y_pred = model.predict(X_scaled)
        mae = mean_absolute_error(y_sector, y_pred)
        r2 = r2_score(y_sector, y_pred)
        
        print(f"  📈 MAE: {mae:,.0f} ton CO2")
        print(f"  📊 R²: {r2:.3f}")
        
        models[sector] = model
        scalers[sector] = scaler
    
    # Modelleri kaydet
    model_dir = Path("modeller")
    model_dir.mkdir(exist_ok=True)
    
    for sector, model in models.items():
        model_path = model_dir / f"linear_{sector}_model.joblib"
        joblib.dump(model, model_path)
        print(f"✅ {sector} modeli kaydedildi: {model_path}")
    
    for sector, scaler in scalers.items():
        scaler_path = model_dir / f"linear_{sector}_scaler.joblib"
        joblib.dump(scaler, scaler_path)
        print(f"✅ {sector} scaler'ı kaydedildi: {scaler_path}")
    
    return models, scalers

def predict_next_year():
    """Gelecek yıl için tahmin yap"""
    print("\n🔮 GELECEK YIL TAHMİNİ")
    print("=" * 40)
    
    # Son 5 yılın verileri
    df = load_turkey_emissions()
    recent_data = df.tail(5)
    
    predictions = {}
    
    for sector in ['transport', 'power', 'buildings', 'total']:
        # Model ve scaler yükle
        try:
            model = joblib.load(f"modeller/linear_{sector}_model.joblib")
            scaler = joblib.load(f"modeller/linear_{sector}_scaler.joblib")
            
            # Özellikler oluştur
            if sector == 'transport':
                features = [[
                    recent_data['Transport'].mean(),
                    (recent_data['Transport'].iloc[-1] - recent_data['Transport'].iloc[0]) / 5,
                    1.0  # yıl konumu
                ]]
            elif sector == 'power':
                features = [[
                    recent_data['Power Industry'].mean(),
                    (recent_data['Power Industry'].iloc[-1] - recent_data['Power Industry'].iloc[0]) / 5,
                    1.0
                ]]
            elif sector == 'buildings':
                features = [[
                    recent_data['Buildings'].mean(),
                    (recent_data['Buildings'].iloc[-1] - recent_data['Buildings'].iloc[0]) / 5,
                    1.0
                ]]
            else:  # total
                features = [[
                    (recent_data['Transport'] + recent_data['Power Industry'] + recent_data['Buildings']).mean(),
                    (recent_data['Transport'].iloc[-1] - recent_data['Transport'].iloc[0]) / 5,
                    (recent_data['Power Industry'].iloc[-1] - recent_data['Power Industry'].iloc[0]) / 5,
                    1.0
                ]]
            
            # Tahmin yap
            features_scaled = scaler.transform(features)
            prediction = model.predict(features_scaled)[0]
            
            predictions[sector] = prediction
            print(f"📊 {sector.upper()} 2025 tahmini: {prediction:,.0f} ton CO2")
            
        except FileNotFoundError:
            print(f"⚠️ {sector} modeli bulunamadı")
    
    return predictions

def calculate_weekly_predictions(yearly_predictions):
    """Yıllık tahminleri haftalığa çevir"""
    print("\n📅 HAFTALIK TAHMİNLER")
    print("=" * 30)
    
    weekly_predictions = {}
    
    for sector, yearly_value in yearly_predictions.items():
        weekly_value = yearly_value / 52
        weekly_predictions[sector] = weekly_value
        print(f"📊 {sector}: {weekly_value:.2f} kg CO2/hafta")
    
    return weekly_predictions

if __name__ == "__main__":
    # Model eğit
    models, scalers = train_linear_regression()
    
    # Tahmin yap
    yearly_predictions = predict_next_year()
    
    # Haftalık tahminlere çevir
    weekly_predictions = calculate_weekly_predictions(yearly_predictions)
    
    print(f"\n✅ Model eğitimi tamamlandı!")
    print(f"🇹🇷 Türkiye gerçek verileri kullanıldı")
    print(f"📈 Linear Regression trend tabanlı tahmin yapıyor")
