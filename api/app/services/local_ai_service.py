import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.models.models import PriceLog
import logging

class LocalAIService:
    @staticmethod
    def train_and_predict(db: Session, look_ahead: int = 5, k_neighbors: int = 5):
        """
        Entrena un modelo KNN simple desde cero usando la mitad de los datos
        y predice con la otra mitad.
        """
        # 1. Obtener datos de la DB (limitamos a los últimos 1000 para no saturar)
        logs = db.query(PriceLog).order_by(PriceLog.timestamp.desc()).limit(1000).all()
        
        if len(logs) < 20:
            return {"error": f"Datos insuficientes para entrenar. Se necesitan al menos 20 registros, hay {len(logs)}."}
        
        # Invertir para que estén en orden cronológico ascendente
        logs = list(reversed(logs))
        
        # 2. Crear DataFrame
        data = []
        for log in logs:
            data.append({
                "price": float(log.price),
                "rsi": float(log.rsi) if log.rsi else 50,
                "adx": float(log.adx) if log.adx else 0,
                "volume_ratio": float(log.volume_ratio) if log.volume_ratio else 1,
                "atr": float(log.atr) if log.atr else 0,
                "timestamp": log.timestamp
            })
            
        df = pd.DataFrame(data)
        
        # 3. Crear etiquetas (Target)
        # Queremos predecir si el precio subirá o bajará en 'look_ahead' pasos
        df['future_price'] = df['price'].shift(-look_ahead)
        df['price_change_pct'] = (df['future_price'] - df['price']) / df['price']
        
        # Definir etiquetas: 1 para LONG (sube > 0.1%), -1 para SHORT (baja > 0.1%), 0 para HOLD
        threshold = 0.001 # 0.1%
        df['label'] = 0
        df.loc[df['price_change_pct'] > threshold, 'label'] = 1
        df.loc[df['price_change_pct'] < -threshold, 'label'] = -1
        
        # Eliminar filas donde no podemos ver el futuro
        df_valid = df.dropna(subset=['future_price']).copy()
        
        if len(df_valid) < 10:
            return {"error": "No hay suficientes datos válidos después de aplicar el look_ahead."}
            
        # 4. Dividir datos: Mitad para entrenar, mitad para predecir
        mid_point = len(df_valid) // 2
        train_df = df_valid.iloc[:mid_point].copy()
        test_df = df_valid.iloc[mid_point:].copy()
        
        # Features a usar
        features = ['rsi', 'adx', 'volume_ratio', 'atr']
        
        # Normalización (Min-Max) basada en el set de entrenamiento
        for feat in features:
            f_min = train_df[feat].min()
            f_max = train_df[feat].max()
            # Evitar división por cero
            if f_max == f_min:
                f_max += 1e-5
                
            train_df[f'norm_{feat}'] = (train_df[feat] - f_min) / (f_max - f_min)
            test_df[f'norm_{feat}'] = (test_df[feat] - f_min) / (f_max - f_min)
            
        norm_features = [f'norm_{feat}' for feat in features]
        
        # 5. Predicción KNN desde cero para el último punto del test set (el más reciente)
        # O podemos predecir para todo el test set y dar una métrica de precisión
        
        # Vamos a predecir para el último registro del test set (el estado actual)
        last_test_point = test_df.iloc[-1]
        
        # Calcular distancias euclidianas desde el último punto a todos los puntos de entrenamiento
        distances = []
        for idx, row in train_df.iterrows():
            dist = 0
            for feat in norm_features:
                dist += (last_test_point[feat] - row[feat]) ** 2
            distances.append(np.sqrt(dist))
            
        train_df['distance'] = distances
        
        # Encontrar los K vecinos más cercanos
        neighbors = train_df.sort_values(by='distance').head(k_neighbors)
        
        # Votación
        prediction = neighbors['label'].mode().values[0]
        
        # Calcular precisión en el test set para validar el modelo
        test_predictions = []
        for idx, test_row in test_df.iterrows():
            test_dists = []
            for _, train_row in train_df.iterrows():
                d = 0
                for feat in norm_features:
                    d += (test_row[feat] - train_row[feat]) ** 2
                test_dists.append(np.sqrt(d))
            
            # Crear una copia temporal para no alterar el train_df global
            temp_train = train_df.copy()
            temp_train['temp_dist'] = test_dists
            p = temp_train.sort_values(by='temp_dist').head(k_neighbors)['label'].mode().values[0]
            test_predictions.append(p)
            
        test_df['pred'] = test_predictions
        accuracy = (test_df['pred'] == test_df['label']).mean()
        
        signal_map = {1: "LONG 🚀", -1: "SHORT 📉", 0: "HOLD 😐"}
        
        return {
            "prediction": signal_map[prediction],
            "raw_prediction": int(prediction),
            "model_accuracy": float(accuracy),
            "train_size": len(train_df),
            "test_size": len(test_df),
            "current_state": {
                "price": float(last_test_point['price']),
                "rsi": float(last_test_point['rsi']),
                "adx": float(last_test_point['adx']),
                "volume_ratio": float(last_test_point['volume_ratio'])
            },
            "neighbors_votes": neighbors['label'].value_counts().to_dict()
        }
