"""
KMeans clustering ile kullanıcı profilleri oluşturma
Türkiye ortalamasına göre kalibrasyon yapar
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import joblib
from pathlib import Path
import constants

def load_user_data():
    """Mevcut kullanıcı verilerini yükle"""
    try:
        # Sentetik veri setini yükle
        df = pd.read_csv("archive/sentetik/sentetik_tr_ulasim_haftalik_temiz.csv")
        
        # Kullanıcı bazında özetle
        user_profiles = df.groupby('user_id').agg({
            'dolmus_km': 'mean',
            'otobus_km': 'mean', 
            'metro_km': 'mean',
            'otomobil_km': 'mean',
            'ucak_km': 'mean',
            'haftalik_co2_kg': 'mean'
        }).reset_index()
        
        print(f"📊 {len(user_profiles)} kullanıcı profili yüklendi")
        return user_profiles
        
    except FileNotFoundError:
        print("⚠️ Kullanıcı veri dosyası bulunamadı")
        return None

def create_features(user_profiles):
    """KMeans için özellikler oluştur"""
    features = []
    
    for _, user in user_profiles.iterrows():
        # Ulaşım pattern'leri
        total_transport = user['dolmus_km'] + user['otobus_km'] + user['metro_km'] + user['otomobil_km'] + user['ucak_km']
        public_transport_ratio = (user['dolmus_km'] + user['otobus_km'] + user['metro_km']) / max(total_transport, 1)
        private_transport_ratio = user['otomobil_km'] / max(total_transport, 1)
        air_travel_ratio = user['ucak_km'] / max(total_transport, 1)
        
        # Emisyon seviyesi
        weekly_emission = user['haftalik_co2_kg']
        emission_level = weekly_emission / constants.HAFTALIK_LIMITLER['total']
        
        feature_vector = [
            total_transport,           # Toplam ulaşım
            public_transport_ratio,     # Toplu taşıma oranı
            private_transport_ratio,    # Özel araç oranı
            air_travel_ratio,          # Uçak oranı
            weekly_emission,           # Haftalık emisyon
            emission_level,            # Emisyon seviyesi (Türkiye ortalamasına göre)
            user['dolmus_km'],        # Dolmus
            user['otobus_km'],        # Otobüs
            user['metro_km'],           # Metro
            user['otomobil_km'],       # Otomobil
            user['ucak_km'],           # Uçak
        ]
        
        features.append(feature_vector)
    
    return np.array(features)

def find_optimal_clusters(features, max_clusters=6):
    """Optimal küme sayısını bul"""
    silhouette_scores = []
    inertias = []
    
    for k in range(2, max_clusters + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features)
        
        silhouette_avg = silhouette_score(features, labels)
        silhouette_scores.append(silhouette_avg)
        inertias.append(kmeans.inertia_)
        
        print(f"  K={k}: Silhouette={silhouette_avg:.3f}, Inertia={kmeans.inertia_:.0f}")
    
    # En yüksek silhouette skoruna göre küme seç
    optimal_k = np.argmax(silhouette_scores) + 2
    print(f"\n🎯 Optimal küme sayısı: {optimal_k}")
    
    return optimal_k

def train_kmeans_model():
    """KMeans model eğit"""
    print("🤖 KMEANS KULLANICI PROFİLLEME")
    print("=" * 50)
    
    # Veriyi yükle
    user_profiles = load_user_data()
    if user_profiles is None:
        return None, None
    
    # Özellikler oluştur
    features = create_features(user_profiles)
    print(f"📊 Özellik matrisi: {features.shape}")
    
    # Özellikleri ölçeklendir
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # Optimal küme sayısını bul
    optimal_k = find_optimal_clusters(features_scaled)
    
    # Final model eğit
    print(f"\n🔧 Final KMeans model eğitiliyor (K={optimal_k})...")
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=20)
    labels = kmeans.fit_predict(features_scaled)
    
    # Küme merkezlerini analiz et
    cluster_centers = scaler.inverse_transform(kmeans.cluster_centers_)
    
    print(f"\n📊 KÜME ANALİZİ (K={optimal_k}):")
    feature_names = [
        'Toplam Ulaşım', 'Toplu Taşıma Oranı', 'Özel Araç Oranı', 'Uçak Oranı',
        'Haftalık Emisyon', 'Emisyon Seviyesi', 'Dolmuş', 'Otobüs', 'Metro', 'Otomobil', 'Uçak'
    ]
    
    for i, center in enumerate(cluster_centers):
        print(f"\n🏷️ Küme {i+1}:")
        for j, (name, value) in enumerate(zip(feature_names, center)):
            if j < 5:  # İlk 5 özellik oran
                print(f"  {name}: {value:.3f}")
            else:  # Gerçek değerler
                print(f"  {name}: {value:.1f} km/hafta")
    
    # Modeli kaydet
    model_dir = Path("modeller")
    model_dir.mkdir(exist_ok=True)
    
    joblib.dump(kmeans, model_dir / "kmeans_user_profiles.joblib")
    joblib.dump(scaler, model_dir / "kmeans_scaler.joblib")
    
    print(f"\n✅ KMeans modeli kaydedildi: {model_dir / 'kmeans_user_profiles.joblib'}")
    print(f"✅ Scaler kaydedildi: {model_dir / 'kmeans_scaler.joblib'}")
    
    # Kullanıcı etiketlerini kaydet
    user_profiles['cluster'] = labels
    user_profiles.to_csv(model_dir / "user_cluster_labels.csv", index=False)
    print(f"✅ Kullanıcı etiketleri kaydedildi: {model_dir / 'user_cluster_labels.csv'}")
    
    return kmeans, scaler

def predict_user_profile(user_data, kmeans_model, scaler):
    """Yeni kullanıcı için profil tahmini yap"""
    # Özellikler oluştur
    total_transport = (user_data.get('dolmus_km', 0) + user_data.get('otobus_km', 0) + 
                     user_data.get('metro_km', 0) + user_data.get('otomobil_km', 0) + user_data.get('ucak_km', 0))
    public_transport_ratio = (user_data.get('dolmus_km', 0) + user_data.get('otobus_km', 0) + 
                          user_data.get('metro_km', 0)) / max(total_transport, 1)
    private_transport_ratio = user_data.get('otomobil_km', 0) / max(total_transport, 1)
    air_travel_ratio = user_data.get('ucak_km', 0) / max(total_transport, 1)
    
    weekly_emission = user_data.get('haftalik_co2_kg', 0)
    emission_level = weekly_emission / constants.HAFTALIK_LIMITLER['total']
    
    features = [[
        total_transport, public_transport_ratio, private_transport_ratio, air_travel_ratio,
        weekly_emission, emission_level, user_data.get('dolmus_km', 0), user_data.get('otobus_km', 0),
        user_data.get('metro_km', 0), user_data.get('otomobil_km', 0), user_data.get('ucak_km', 0)
    ]]
    
    # Tahmin yap
    features_scaled = scaler.transform(features)
    cluster = kmeans_model.predict(features_scaled)[0]
    
    return cluster

def get_cluster_recommendations(cluster_id, kmeans_model, scaler):
    """Küme bazında öneriler oluştur"""
    # Tüm kullanıcı verilerini yükle
    user_profiles = load_user_data()
    if user_profiles is None:
        return {}
    
    # Özellikler oluştur
    features = create_features(user_profiles)
    features_scaled = scaler.transform(features)
    labels = kmeans_model.predict(features_scaled)
    
    # Kümenin ortalamasını hesapla
    cluster_mask = labels == cluster_id
    if not np.any(cluster_mask):
        return {"error": "Küme bulunamadı"}
    
    cluster_users = user_profiles[cluster_mask]
    
    # Küme özellikleri
    avg_profile = {
        'total_transport': cluster_users['dolmus_km'] + cluster_users['otobus_km'] + 
                          cluster_users['metro_km'] + cluster_users['otomobil_km'] + cluster_users['ucak_km'],
        'emission_level': cluster_users['haftalik_co2_kg'].mean() / constants.HAFTALIK_LIMITLER['total'],
        'dominant_transport': cluster_users[['dolmus_km', 'otobus_km', 'metro_km', 'otomobil_km', 'ucak_km']].mean().idxmax(),
        'user_count': len(cluster_users)
    }
    
    # Öneriler
    recommendations = {}
    
    if avg_profile['emission_level'] > 1.2:  # Türkiye ortalamasından yüksek
        recommendations['priority'] = "Yüksek emisyon azaltmalı"
        recommendations['actions'] = [
            "Toplu taşıma kullanımını artır",
            "Özel araç kullanımını azalt",
            "Kısa mesafelerde yürü/bisiklet",
            "Uçak seyahatlerini optimize et"
        ]
    elif avg_profile['emission_level'] < 0.8:  # Türkiye ortalamasından düşük
        recommendations['priority'] = "Düşük emisyon sürdür"
        recommendations['actions'] = [
            "Mevcut alışkanlıkları koru",
            "Diğerlerine örnek ol",
            "Sürdürülebilir seçimleri paylaş"
        ]
    else:
        recommendations['priority'] = "Normal seviye devam et"
        recommendations['actions'] = [
            "Küçük iyileştirmeler yap",
            "Yenilenebilir enerji kullan",
            "Verimliliği artır"
        ]
    
    return {
        'cluster_id': cluster_id,
        'profile': avg_profile,
        'recommendations': recommendations
    }

if __name__ == "__main__":
    kmeans_model, scaler = train_kmeans_model()
    
    if kmeans_model is not None:
        print(f"\n✅ KMeans profilleme tamamlandı!")
        print(f"🎯 {len(set(kmeans_model.labels_))} farklı kullanıcı profili tespit edildi")
        print(f"📊 Türkiye ortalamasına göre kalibrasyon hazır")
