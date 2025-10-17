"""
Voting Ensemble Bot Detector: K-means + Isolation Forest
Комбинирует стиль игры (K-means) и детекцию аномалий (Isolation Forest)
"""

import numpy as np
from typing import Dict, Any, Optional, List
import pickle
import os
from datetime import datetime, timedelta

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class BotDetector:
    """Voting Ensemble для детекции ботов: K-means + Isolation Forest"""
    
    def __init__(self, model_path: str = "/app/models/bot_detector.pkl"):
        self.model_path = model_path
        self.if_model: Optional[IsolationForest] = None
        self.kmeans_classifier = None
        self.is_trained = False
    
    def train(self, player_features: np.ndarray, player_ids: List[int] = None) -> Dict[str, Any]:
        """
        Обучает Isolation Forest на фичах игроков
        
        player_features: массив [n_players, n_features]
        Фичи: [pvp_ratio, kpm, survival_rate, avg_session_len, regularity, etc]
        """
        if not SKLEARN_AVAILABLE:
            return {"status": "error", "error": "sklearn not available"}
        
        if len(player_features) < 10:
            return {"status": "error", "error": "Недостаточно данных (минимум 10 игроков)"}
        
        start_time = datetime.now()
        
        # Обучаем Isolation Forest
        # contamination=0.1 означает что ожидаем ~10% ботов
        self.if_model = IsolationForest(
            n_estimators=100,
            contamination=0.10,
            random_state=42,
            n_jobs=-1,
            max_samples='auto',
            bootstrap=False
        )
        
        self.if_model.fit(player_features)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Загружаем K-means classifier
        from app.ml.playstyle_classifier import PlaystyleClassifier
        self.kmeans_classifier = PlaystyleClassifier()
        kmeans_loaded = self.kmeans_classifier.load_model()
        
        if not kmeans_loaded:
            return {"status": "error", "error": "K-means модель не обучена"}
        
        self.is_trained = True
        
        # Сохраняем модель
        self.save_model()
        
        # Статистика
        predictions = self.if_model.predict(player_features)
        anomalies_detected = np.sum(predictions == -1)
        
        return {
            "status": "success",
            "players_analyzed": len(player_features),
            "anomalies_detected": int(anomalies_detected),
            "anomaly_rate": round(anomalies_detected / len(player_features), 3),
            "training_time": round(elapsed, 2),
            "model_saved": self.model_path
        }
    
    def save_model(self) -> bool:
        """Сохраняет Isolation Forest модель"""
        if not self.if_model:
            return False
        
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.if_model, f)
            return True
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def load_model(self) -> bool:
        """Загружает Isolation Forest модель"""
        if not SKLEARN_AVAILABLE:
            return False
        
        if not os.path.exists(self.model_path):
            return False
        
        try:
            with open(self.model_path, 'rb') as f:
                self.if_model = pickle.load(f)
            
            # Загружаем K-means
            from app.ml.playstyle_classifier import PlaystyleClassifier
            self.kmeans_classifier = PlaystyleClassifier()
            kmeans_loaded = self.kmeans_classifier.load_model()
            
            self.is_trained = self.if_model is not None and kmeans_loaded
            return self.is_trained
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    async def detect(self, player_id: int, db, days: int = 90) -> Dict[str, Any]:
        """
        Voting Ensemble детекция бота для одного игрока
        
        Возвращает:
        {
            'is_bot': bool,
            'confidence': float (0-1),
            'method': str ('voting', 'kmeans_only', 'if_only'),
            'kmeans_bot': bool,
            'if_anomaly': bool,
            'playstyle': str,
            'reasons': List[str]
        }
        """
        if not self.is_trained:
            return {"error": "Model not trained"}
        
        # Получаем фичи игрока
        features = await self._get_player_features(player_id, db, days)
        
        if not features:
            return {"error": "No features"}
        
        # 1. K-means детекция через playstyle
        kmeans_result = None
        kmeans_bot = False
        playstyle = 'unknown'
        
        if self.kmeans_classifier:
            kmeans_result = await self.kmeans_classifier.classify_player(player_id, db, days)
            if kmeans_result:
                playstyle = kmeans_result.get('playstyle', 'unknown')
                bd = kmeans_result.get('bot_detection', {})
                kmeans_bot = bd.get('is_likely_bot', False) or bd.get('bot_score', 0) >= 0.75
        
        # 2. Isolation Forest детекция (аномалии)
        feature_array = np.array([list(features.values())]).reshape(1, -1)
        if_prediction = self.if_model.predict(feature_array)[0]
        if_score = self.if_model.decision_function(feature_array)[0]
        if_anomaly = (if_prediction == -1)
        
        # 3. ДИНАМИЧЕСКИЙ расчёт bot_probability (0-100%)
        
        # 3.1 Isolation Forest score (нормализуем к 0-1)
        # decision_function: negative = anomaly, positive = normal
        # Типичный диапазон: -0.2 до +0.2
        if_probability = max(0, min(1, (-if_score - 0.05) / 0.3))
        
        # 3.2 K-means bot_score (уже 0-1)
        kmeans_probability = 0
        if kmeans_result:
            kmeans_probability = kmeans_result.get('bot_detection', {}).get('bot_score', 0)
        
        # 3.3 Критические признаки
        ultra_short_ratio = features.get('ultra_short_ratio', 0)
        session_variance = features.get('session_variance', 1)
        hour_diversity = features.get('hour_diversity', 12)
        
        critical_probability = 0
        if ultra_short_ratio > 0.5:
            critical_probability = max(critical_probability, 0.95)  # 95% - явный бот
        elif ultra_short_ratio > 0.3:
            critical_probability = max(critical_probability, 0.70)  # 70% - подозрителен
        elif ultra_short_ratio > 0.1:
            critical_probability = max(critical_probability, 0.40)  # 40% - возможен
        
        if session_variance < 0.1:
            critical_probability = max(critical_probability, 0.60)  # Идеальные сессии
        
        if hour_diversity < 3:
            critical_probability = max(critical_probability, 0.50)  # Жёсткое расписание
        
        # 3.4 Взвешенная комбинация
        weights = {
            'critical': 0.50,      # Ультра-короткие интервалы + сессии - главное
            'isolation_forest': 0.30,  # Аномальность поведения
            'kmeans': 0.20         # Стиль игры
        }
        
        bot_probability = (
            critical_probability * weights['critical'] +
            if_probability * weights['isolation_forest'] +
            kmeans_probability * weights['kmeans']
        )
        
        # Ограничиваем 0-1
        bot_probability = max(0, min(1, bot_probability))
        
        # 4. Классификация
        is_bot = bot_probability >= 0.5
        
        if bot_probability >= 0.85:
            method = 'high_confidence'
        elif bot_probability >= 0.70:
            method = 'medium_high'
        elif bot_probability >= 0.50:
            method = 'medium'
        else:
            method = 'clean'
        
        # 5. Причины
        reasons = []
        if kmeans_bot:
            reasons.append(f"K-means: стиль '{kmeans_result.get('display_name')}' подозрителен")
            if kmeans_result:
                reasons.extend(kmeans_result.get('bot_detection', {}).get('reasons', []))
        
        if if_anomaly:
            reasons.append(f"Isolation Forest: аномальное поведение (score={if_score:.2f})")
            # Определяем какие фичи аномальны
            anomaly_features = self._explain_anomaly(features)
            reasons.extend(anomaly_features)
        
        return {
            'is_bot': is_bot,
            'bot_probability': round(bot_probability * 100, 1),  # 0-100%
            'confidence_level': method,
            'detection_breakdown': {
                'critical_indicators': round(critical_probability, 3),
                'anomaly_score': round(if_probability, 3),
                'playstyle_score': round(kmeans_probability, 3),
                'weighted_score': round(bot_probability, 3)
            },
            'kmeans_bot': kmeans_bot,
            'if_anomaly': if_anomaly,
            'if_anomaly_score': round(float(if_score), 3),
            'playstyle': kmeans_result.get('display_name') if kmeans_result else 'Unknown',
            'reasons': reasons
        }
    
    async def _get_player_features(self, player_id: int, db, days: int) -> Optional[Dict[str, float]]:
        """Извлекает фичи игрока для Isolation Forest (14 признаков + вариативность сессий!)"""
        cutoff = datetime.now() - timedelta(days=days)
        
        # Запрос с вариативностью сессий
        query = """
            WITH player_battles_ordered AS (
                SELECT 
                    bp.player_id,
                    b.id as battle_id,
                    b.ts,
                    b.battle_type,
                    bp.kills_players,
                    bp.kills_monsters,
                    bp.survived,
                    b.loc_x,
                    b.loc_y,
                    EXTRACT(EPOCH FROM (b.ts - LAG(b.ts) OVER (PARTITION BY bp.player_id ORDER BY b.ts))) as gap_seconds,
                    EXTRACT(HOUR FROM b.ts) as hour_of_day
                FROM battle_participants bp
                JOIN battles b ON b.id = bp.battle_id
                WHERE bp.player_id = $1 AND b.ts >= $2
            ),
            player_sessions AS (
                SELECT 
                    player_id,
                    battle_id,
                    ts,
                    gap_seconds,
                    -- Определяем сессии: gap > 1800 сек (30 минут) = новая сессия
                    SUM(CASE WHEN gap_seconds > 1800 OR gap_seconds IS NULL THEN 1 ELSE 0 END) 
                        OVER (PARTITION BY player_id ORDER BY ts) as session_id
                FROM player_battles_ordered
            ),
            session_lengths AS (
                SELECT 
                    player_id,
                    session_id,
                    COUNT(*) as battles_in_session
                FROM player_sessions
                GROUP BY player_id, session_id
            )
            SELECT 
                COUNT(DISTINCT pb.battle_id) as total_battles,
                AVG(CASE WHEN pb.battle_type IN ('B', 'C') THEN 1.0 ELSE 0.0 END) as pvp_ratio,
                AVG(pb.kills_players + pb.kills_monsters) as kpm,
                AVG(CASE WHEN pb.survived::int = 1 THEN 1.0 ELSE 0.0 END) as survival_rate,
                AVG(pb.kills_monsters) as avg_kills_monsters,
                AVG(pb.kills_players) as avg_kills_players,
                COUNT(DISTINCT pb.loc_x || ',' || pb.loc_y) as location_diversity,
                COUNT(DISTINCT pb.hour_of_day) as hour_diversity,
                SUM(CASE WHEN pb.gap_seconds <= 0.5 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(pb.gap_seconds), 0) as ultra_short_ratio,
                MAX(pb.gap_seconds) / 3600.0 as max_gap_hours,
                STDDEV(pb.gap_seconds) / NULLIF(AVG(pb.gap_seconds), 0) as time_regularity,
                AVG(sl.battles_in_session) as avg_session_length,
                STDDEV(sl.battles_in_session) / NULLIF(AVG(sl.battles_in_session), 0) as session_variance,
                COUNT(DISTINCT sl.session_id) as total_sessions
            FROM player_battles_ordered pb
            LEFT JOIN session_lengths sl ON sl.player_id = pb.player_id
            WHERE pb.player_id = $1
            GROUP BY pb.player_id
            HAVING COUNT(DISTINCT pb.battle_id) >= 5
        """
        
        try:
            result = await db._execute_one(query, player_id, cutoff)
            
            if not result:
                return None
            
            # Нормализуем фичи (14 признаков)
            features = {
                'pvp_ratio': float(result['pvp_ratio'] or 0),
                'kpm': min(float(result['kpm'] or 0), 30),
                'survival_rate': float(result['survival_rate'] or 0),
                'avg_kills_monsters': min(float(result['avg_kills_monsters'] or 0), 50),
                'avg_kills_players': min(float(result['avg_kills_players'] or 0), 20),
                'time_regularity': min(float(result['time_regularity'] or 1), 10),
                'location_diversity': min(float(result['location_diversity'] or 1), 20),
                'total_battles': min(float(result['total_battles'] or 0), 1000),
                'ultra_short_ratio': float(result['ultra_short_ratio'] or 0),
                'max_gap_hours': min(float(result['max_gap_hours'] or 24), 48),
                # НОВОЕ: Вариативность сессий
                'hour_diversity': min(float(result['hour_diversity'] or 1), 24),
                'avg_session_length': min(float(result['avg_session_length'] or 10), 100),
                'session_variance': min(float(result['session_variance'] or 1), 5),
                'total_sessions': min(float(result['total_sessions'] or 1), 100),
            }
            
            return features
        except Exception as e:
            print(f"Error extracting features: {e}")
            return None
    
    def _explain_anomaly(self, features: Dict[str, float]) -> List[str]:
        """Объясняет почему игрок аномален (с вариативностью сессий!)"""
        reasons = []
        
        # КРИТИЧНО: Ультра-короткие интервалы - ГЛАВНЫЙ ПРИЗНАК БОТА!
        ultra_short_ratio = features.get('ultra_short_ratio', 0)
        if ultra_short_ratio > 0.3:
            reasons.append(f"🔴 КРИТИЧНО: {ultra_short_ratio:.1%} боёв с интервалом < 0.5 сек (ботовая активность)")
        elif ultra_short_ratio > 0.1:
            reasons.append(f"🟠 Много коротких интервалов < 0.5 сек: {ultra_short_ratio:.1%}")
        
        # НОВОЕ: Вариативность сессий (боты играют одинаковыми сессиями)
        session_variance = features.get('session_variance', 1)
        if session_variance < 0.2:
            reasons.append(f"🟠 Одинаковая длина сессий (variance={session_variance:.2f}) - ботовый паттерн")
        
        # НОВОЕ: Разнообразие времени игры
        hour_diversity = features.get('hour_diversity', 12)
        if hour_diversity < 4:
            reasons.append(f"🟠 Играет только в {int(hour_diversity)} часа суток (расписание бота)")
        
        # Отсутствие перерывов
        max_gap_hours = features.get('max_gap_hours', 24)
        if max_gap_hours < 0.5:
            reasons.append(f"🟠 Нет перерывов > {max_gap_hours*60:.0f} минут")
        
        # Длинные марафоны без перерывов
        avg_session_length = features.get('avg_session_length', 10)
        if avg_session_length > 50:
            reasons.append(f"🟡 Длинные марафоны: {avg_session_length:.0f} боёв подряд")
        
        # Экстремальные значения
        if features.get('kpm', 0) > 30:
            reasons.append(f"🟡 Экстремальный KPM: {features['kpm']:.1f}")
        
        if features.get('survival_rate', 0) > 0.97:
            reasons.append(f"🟡 Очень высокий SR: {features['survival_rate']:.1%}")
        
        if features.get('time_regularity', 1) < 0.2:
            reasons.append("🟡 Идеальная регулярность игры")
        
        if features.get('location_diversity', 10) < 3:
            reasons.append(f"🟡 Мало локаций: {int(features['location_diversity'])}")
        
        if features.get('pvp_ratio', 0.5) < 0.02:
            reasons.append(f"🟡 Почти нет PvP: {features['pvp_ratio']:.1%}")
        
        return reasons


async def train_bot_detector(db, days: int = 90) -> Dict[str, Any]:
    """
    Обучает Voting Ensemble детектор ботов
    
    Собирает фичи всех активных игроков и обучает Isolation Forest
    """
    if not SKLEARN_AVAILABLE:
        return {"status": "error", "error": "sklearn not available"}
    
    cutoff = datetime.now() - timedelta(days=days)
    
    # Получаем фичи всех игроков (с НОВЫМИ метриками + ВАРИАТИВНОСТЬ СЕССИЙ!)
    query = """
        WITH player_battles_ordered AS (
            SELECT 
                bp.player_id,
                b.id as battle_id,
                b.ts,
                b.battle_type,
                bp.kills_players,
                bp.kills_monsters,
                bp.survived,
                b.loc_x,
                b.loc_y,
                EXTRACT(EPOCH FROM (b.ts - LAG(b.ts) OVER (PARTITION BY bp.player_id ORDER BY b.ts))) as gap_seconds,
                EXTRACT(HOUR FROM b.ts) as hour_of_day
            FROM battle_participants bp
            JOIN battles b ON b.id = bp.battle_id
            WHERE b.ts >= $1
        ),
        player_sessions AS (
            SELECT 
                player_id,
                battle_id,
                ts,
                gap_seconds,
                -- Определяем сессии: gap > 1800 сек (30 минут) = новая сессия
                SUM(CASE WHEN gap_seconds > 1800 OR gap_seconds IS NULL THEN 1 ELSE 0 END) 
                    OVER (PARTITION BY player_id ORDER BY ts) as session_id
            FROM player_battles_ordered
        ),
        session_lengths AS (
            SELECT 
                player_id,
                session_id,
                COUNT(*) as battles_in_session
            FROM player_sessions
            GROUP BY player_id, session_id
        ),
        player_stats AS (
            SELECT 
                bp.player_id,
                COUNT(DISTINCT b.id) as total_battles,
                AVG(CASE WHEN b.battle_type IN ('B', 'C') THEN 1.0 ELSE 0.0 END) as pvp_ratio,
                AVG(bp.kills_players + bp.kills_monsters) as kpm,
                AVG(CASE WHEN bp.survived::int = 1 THEN 1.0 ELSE 0.0 END) as survival_rate,
                AVG(bp.kills_monsters) as avg_kills_monsters,
                AVG(bp.kills_players) as avg_kills_players,
                COUNT(DISTINCT b.loc_x || ',' || b.loc_y) as location_diversity,
                COUNT(DISTINCT EXTRACT(HOUR FROM b.ts)) as hour_diversity
            FROM battle_participants bp
            JOIN battles b ON b.id = bp.battle_id
            WHERE b.ts >= $1
            GROUP BY bp.player_id
            HAVING COUNT(*) >= 5
        ),
        player_regularity AS (
            SELECT 
                player_id,
                STDDEV(gap_seconds) / NULLIF(AVG(gap_seconds), 0) as time_regularity,
                -- Ультра-короткие интервалы
                SUM(CASE WHEN gap_seconds <= 0.5 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(gap_seconds), 0) as ultra_short_ratio,
                -- Максимальный разрыв
                MAX(gap_seconds) / 3600.0 as max_gap_hours
            FROM player_battles_ordered
            WHERE gap_seconds IS NOT NULL
            GROUP BY player_id
        ),
        session_variability AS (
            SELECT 
                player_id,
                AVG(battles_in_session) as avg_session_length,
                STDDEV(battles_in_session) / NULLIF(AVG(battles_in_session), 0) as session_variance,
                COUNT(DISTINCT session_id) as total_sessions
            FROM session_lengths
            GROUP BY player_id
        )
        SELECT 
            ps.player_id,
            ps.total_battles,
            ps.pvp_ratio,
            ps.kpm,
            ps.survival_rate,
            ps.avg_kills_monsters,
            ps.avg_kills_players,
            COALESCE(pr.time_regularity, 1.0) as time_regularity,
            ps.location_diversity,
            COALESCE(pr.ultra_short_ratio, 0.0) as ultra_short_ratio,
            COALESCE(pr.max_gap_hours, 24.0) as max_gap_hours,
            ps.hour_diversity,
            COALESCE(sv.avg_session_length, 10.0) as avg_session_length,
            COALESCE(sv.session_variance, 1.0) as session_variance,
            COALESCE(sv.total_sessions, 1) as total_sessions
        FROM player_stats ps
        LEFT JOIN player_regularity pr ON pr.player_id = ps.player_id
        LEFT JOIN session_variability sv ON sv.player_id = ps.player_id
        ORDER BY ps.total_battles DESC
        LIMIT 10000
    """
    
    rows = await db._execute_query(query, cutoff)
    
    if not rows or len(rows) < 10:
        return {"status": "error", "error": "Недостаточно данных"}
    
    # Формируем матрицу фичей (14 признаков: 10 базовых + 4 вариативность сессий!)
    player_ids = []
    features_list = []
    
    for r in rows:
        player_ids.append(r['player_id'])
        
        features = [
            # Базовые признаки (8)
            float(r['pvp_ratio'] or 0),
            min(float(r['kpm'] or 0), 30),
            float(r['survival_rate'] or 0),
            min(float(r['avg_kills_monsters'] or 0), 50),
            min(float(r['avg_kills_players'] or 0), 20),
            min(float(r['time_regularity'] or 1), 10),
            min(float(r['location_diversity'] or 1), 20),
            min(float(r['total_battles'] or 0), 1000),
            # Критичные признаки ботов (2)
            float(r['ultra_short_ratio'] or 0),  # 0-1: интервалы < 0.5 сек
            min(float(r['max_gap_hours'] or 24), 48),  # 0-48: макс перерыв
            # Вариативность сессий (4 - НОВОЕ!)
            min(float(r['hour_diversity'] or 1), 24),  # 1-24: разнообразие часов игры
            min(float(r['avg_session_length'] or 10), 100),  # 1-100: средняя длина сессии
            min(float(r['session_variance'] or 1), 5),  # 0-5: вариативность сессий (STDDEV/AVG)
            min(float(r['total_sessions'] or 1), 100),  # 1-100: количество сессий
        ]
        features_list.append(features)
    
    features_array = np.array(features_list)
    
    # Обучаем детектор
    detector = BotDetector()
    result = detector.train(features_array, player_ids)
    
    return result

