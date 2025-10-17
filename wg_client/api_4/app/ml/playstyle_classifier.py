"""
K-means классификация стилей игры
Автоматически группирует игроков по паттернам поведения
"""

from typing import Dict, Any, List, Optional
import pickle
from datetime import datetime, timedelta
from pathlib import Path

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    KMeans = None
    StandardScaler = None
    np = None


class PlaystyleClassifier:
    """Классификатор стилей игры на основе K-means кластеризации"""
    
    PLAYSTYLE_NAMES = {
        "aggressive_pvp": "Агрессивный PvP",
        "elite_pvp": "Элитный PvP",
        "pvp_assassin": "PvP Ассасин",
        "pvp_tank": "PvP Танк",
        "pvp_support": "PvP Саппорт",
        "safe_farmer": "Безопасный фармер",
        "bot_farmer": "Бот/Фарм-бот",
        "balanced": "Сбалансированный",
        "pvp_novice": "PvP новичок",
        "pve_grinder": "PvE гриндер",
    }
    
    def __init__(self, n_clusters: int = 8, model_path: Optional[str] = None):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn не установлен. Установите: pip install scikit-learn numpy")
        
        self.n_clusters = n_clusters
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.scaler = StandardScaler()
        self.cluster_labels: Dict[int, Dict[str, Any]] = {}
        self.is_trained = False
        self.model_path = model_path or "/tmp/playstyle_model.pkl"
        
    async def train(self, db, days: int = 90, min_battles: int = 10):
        """
        Обучает модель на всех активных игроках
        
        Args:
            db: Database instance
            days: период для анализа
            min_battles: минимум боёв для включения в обучение
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Получаем признаки для всех игроков
        query = """
            SELECT 
                p.id,
                p.login,
                COUNT(*) as total_battles,
                COUNT(CASE WHEN b.players_cnt > 1 THEN 1 END) as pvp_battles_count,
                COUNT(CASE WHEN b.players_cnt > 1 THEN 1 END)::float / COUNT(*) as pvp_ratio,
                AVG(bp.kills_players + bp.kills_monsters) as kpm,
                AVG(CASE WHEN bp.survived::int = 1 THEN 1.0 ELSE 0.0 END) as survival_rate,
                AVG(bp.pve_points) as avg_pve,
                AVG(bp.rank_points) as avg_rank,
                AVG(bp.kills_players)::float / NULLIF(AVG(bp.kills_monsters), 0) as pvp_monster_ratio,
                COUNT(DISTINCT DATE(b.ts)) as active_days,
                -- PvP-специфичные признаки
                AVG(CASE WHEN b.players_cnt > 1 THEN bp.kills_players ELSE NULL END) as avg_kills_per_pvp,
                SUM(CASE WHEN b.players_cnt > 1 AND bp.survived::int = 1 THEN 1 ELSE 0 END)::float / 
                    NULLIF(COUNT(CASE WHEN b.players_cnt > 1 THEN 1 END), 0) as pvp_survival_rate,
                AVG(CASE WHEN b.players_cnt > 1 THEN (bp.damage_total->>'total')::int ELSE NULL END) as avg_pvp_damage
            FROM players p
            JOIN battle_participants bp ON bp.player_id = p.id
            JOIN battles b ON b.id = bp.battle_id
            WHERE b.ts >= $1
            GROUP BY p.id, p.login
            HAVING COUNT(*) >= $2
            ORDER BY COUNT(*) DESC
        """
        
        rows = await db._execute_query(query, cutoff_date, min_battles)
        
        if len(rows) < self.n_clusters:
            raise ValueError(f"Недостаточно данных: {len(rows)} игроков, нужно минимум {self.n_clusters}")
        
        # Формируем матрицу признаков
        self.player_ids = []
        self.player_logins = []
        features = []
        
        for r in rows:
            self.player_ids.append(r['id'])
            self.player_logins.append(r['login'])
            
            # Вектор признаков (12 измерений: 8 базовых + 4 PvP)
            feat = [
                # Базовые признаки
                float(r['pvp_ratio'] or 0),                    # 0-1: доля PvP боёв
                float(r['kpm'] or 0) / 20.0,                  # 0-1: KPM нормализованный
                float(r['survival_rate'] or 0),               # 0-1: процент выживания
                float(r['avg_pve'] or 0) / 100000.0,          # 0-1: средние PvE очки
                float(r['avg_rank'] or 0) / 10.0,             # 0-1: средние rank очки
                float(r['pvp_monster_ratio'] or 0) / 2.0,     # 0-1: агрессия к игрокам
                float(r['total_battles']) / 1000.0,           # 0-1: всего боёв
                float(r['active_days']) / days,               # 0-1: активность
                # PvP-специфичные признаки
                float(r['avg_kills_per_pvp'] or 0) / 5.0,     # 0-1: убийств игроков за PvP бой
                float(r['pvp_survival_rate'] or 0),           # 0-1: выживаемость в PvP
                float(r['pvp_battles_count'] or 0) / 500.0,   # 0-1: количество PvP боёв
                float(r['avg_pvp_damage'] or 0) / 5000.0,     # 0-1: средний урон в PvP
            ]
            features.append(feat)
        
        # Нормализация признаков
        self.features_array = np.array(features)
        self.features_scaled = self.scaler.fit_transform(self.features_array)
        
        # Обучение K-means
        self.kmeans.fit(self.features_scaled)
        self.labels = self.kmeans.labels_
        
        # Интерпретация кластеров
        self._interpret_clusters()
        
        self.is_trained = True
        
        # Сохраняем модель
        self.save_model()
        
        return {
            "players_trained": len(self.player_ids),
            "clusters": self.n_clusters,
            "cluster_distribution": self._get_cluster_distribution(),
        }
    
    def _interpret_clusters(self):
        """Автоматически определяет тип каждого кластера по средним значениям"""
        for cluster_id in range(self.n_clusters):
            # Находим игроков этого кластера
            mask = self.labels == cluster_id
            cluster_features = self.features_array[mask]
            cluster_size = int(mask.sum())
            
            if cluster_size == 0:
                continue
            
            # Средние значения по кластеру (denormalized)
            avg = cluster_features.mean(axis=0)
            pvp_ratio = avg[0]
            kpm_norm = avg[1]
            sr = avg[2]
            pve_norm = avg[3]
            rank_norm = avg[4]
            aggr_ratio = avg[5]
            battles_norm = avg[6]
            activity = avg[7]
            # PvP-специфичные
            kills_per_pvp_norm = avg[8]
            pvp_sr = avg[9]
            pvp_battles_norm = avg[10]
            pvp_damage_norm = avg[11]
            
            kpm = kpm_norm * 20
            pve_points = pve_norm * 100000
            kills_per_pvp = kills_per_pvp_norm * 5
            pvp_damage = pvp_damage_norm * 5000
            
            # Правила классификации на основе признаков
            # ПРИОРИТЕТ 1: Детекция ботов (жёсткие критерии)
            if (pvp_ratio < 0.05 and sr > 0.95 and kpm > 15) or \
               (pvp_ratio < 0.02 and kpm > 20) or \
               (pvp_ratio < 0.1 and sr > 0.97 and kpm > 12):
                name = "bot_farmer"
                desc = "Подозрительно высокая эффективность PvE — ВЕРОЯТНО БОТЫ"
            
            # ПРИОРИТЕТ 2: Элитные PvP игроки
            elif pvp_ratio > 0.8 and pvp_sr > 0.85 and kills_per_pvp > 2.5:
                name = "elite_pvp"
                desc = "Элитные PvP игроки — высокий PvP%, отличная выживаемость, много убийств"
            elif pvp_ratio > 0.6 and kills_per_pvp > 2.0 and aggr_ratio > 0.3:
                name = "aggressive_pvp"
                desc = "Агрессивные PvP игроки — фокус на PvP, высокая агрессия"
            
            # ПРИОРИТЕТ 3: Специализированные PvP роли
            elif pvp_ratio > 0.5 and kills_per_pvp > 3.0 and pvp_sr < 0.7:
                name = "pvp_assassin"
                desc = "PvP Ассасины — много убийств, рискованная игра, средняя выживаемость"
            elif pvp_ratio > 0.5 and pvp_sr > 0.75 and pvp_damage > 2000:
                name = "pvp_tank"
                desc = "PvP Танки — высокая выживаемость, много урона, защитная роль"
            elif pvp_ratio > 0.5 and kills_per_pvp < 1.5 and pvp_sr > 0.65:
                name = "pvp_support"
                desc = "PvP Саппорты — мало убийств, хорошая выживаемость, командная игра"
            
            # ПРИОРИТЕТ 4: Фармеры
            elif pvp_ratio < 0.25 and sr > 0.8 and kpm < 12:
                name = "safe_farmer"
                desc = "Безопасные фармеры — избегают PvP, высокая выживаемость"
            
            # ПРИОРИТЕТ 5: Остальные
            elif pvp_ratio > 0.5 and pvp_sr < 0.6:
                name = "pvp_novice"
                desc = "PvP новички — много PvP, но низкая выживаемость"
            elif pve_points > 50000 and pvp_ratio < 0.3:
                name = "pve_grinder"
                desc = "PvE гриндеры — фокус на фарме монстров"
            else:
                name = "balanced"
                desc = "Сбалансированные игроки — микс PvP и PvE"
            
            self.cluster_labels[cluster_id] = {
                "name": name,
                "display_name": self.PLAYSTYLE_NAMES.get(name, name),
                "description": desc,
                "size": cluster_size,
                "avg_features": {
                    "pvp_ratio": round(pvp_ratio, 3),
                    "kpm": round(kpm, 2),
                    "survival_rate": round(sr, 3),
                    "avg_pve_points": round(pve_points, 0),
                    "aggression_ratio": round(aggr_ratio, 3),
                    "activity_ratio": round(activity, 3),
                    # PvP-специфичные
                    "kills_per_pvp": round(kills_per_pvp, 2),
                    "pvp_survival_rate": round(pvp_sr, 3),
                    "pvp_damage": round(pvp_damage, 0),
                }
            }
    
    def _get_cluster_distribution(self) -> List[Dict[str, Any]]:
        """Возвращает распределение игроков по кластерам"""
        distribution = []
        for cluster_id in range(self.n_clusters):
            if cluster_id in self.cluster_labels:
                label_info = self.cluster_labels[cluster_id]
                distribution.append({
                    "cluster_id": cluster_id,
                    "playstyle": label_info["name"],
                    "display_name": label_info["display_name"],
                    "player_count": label_info["size"],
                })
        return sorted(distribution, key=lambda x: x["player_count"], reverse=True)
    
    async def classify_player(self, player_id: int, db, days: int = 90) -> Optional[Dict[str, Any]]:
        """
        Классифицирует одного игрока
        
        Args:
            player_id: ID игрока
            db: Database instance
            days: период для анализа
        """
        if not self.is_trained:
            # Пытаемся загрузить модель
            if not self.load_model():
                raise ValueError("Модель не обучена. Запустите train() сначала.")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Получаем признаки игрока
        query = """
            SELECT 
                p.login,
                COUNT(*) as total_battles,
                COUNT(CASE WHEN b.players_cnt > 1 THEN 1 END) as pvp_battles_count,
                COUNT(CASE WHEN b.players_cnt > 1 THEN 1 END)::float / COUNT(*) as pvp_ratio,
                AVG(bp.kills_players + bp.kills_monsters) as kpm,
                AVG(CASE WHEN bp.survived::int = 1 THEN 1.0 ELSE 0.0 END) as survival_rate,
                AVG(bp.pve_points) as avg_pve,
                AVG(bp.rank_points) as avg_rank,
                AVG(bp.kills_players)::float / NULLIF(AVG(bp.kills_monsters), 0) as pvp_monster_ratio,
                COUNT(DISTINCT DATE(b.ts)) as active_days,
                -- PvP-специфичные признаки
                AVG(CASE WHEN b.players_cnt > 1 THEN bp.kills_players ELSE NULL END) as avg_kills_per_pvp,
                SUM(CASE WHEN b.players_cnt > 1 AND bp.survived::int = 1 THEN 1 ELSE 0 END)::float / 
                    NULLIF(COUNT(CASE WHEN b.players_cnt > 1 THEN 1 END), 0) as pvp_survival_rate,
                AVG(CASE WHEN b.players_cnt > 1 THEN (bp.damage_total->>'total')::int ELSE NULL END) as avg_pvp_damage
            FROM players p
            JOIN battle_participants bp ON bp.player_id = p.id
            JOIN battles b ON b.id = bp.battle_id
            WHERE p.id = $1 AND b.ts >= $2
            GROUP BY p.id, p.login
        """
        
        r = await db._execute_one(query, player_id, cutoff_date)
        
        if not r or r['total_battles'] < 5:
            return None
        
        # Формируем вектор признаков (12 измерений)
        feat = np.array([[
            float(r['pvp_ratio'] or 0),
            float(r['kpm'] or 0) / 20.0,
            float(r['survival_rate'] or 0),
            float(r['avg_pve'] or 0) / 100000.0,
            float(r['avg_rank'] or 0) / 10.0,
            float(r['pvp_monster_ratio'] or 0) / 2.0,
            float(r['total_battles']) / 1000.0,
            float(r['active_days']) / days,
            # PvP-специфичные
            float(r['avg_kills_per_pvp'] or 0) / 5.0,
            float(r['pvp_survival_rate'] or 0),
            float(r['pvp_battles_count'] or 0) / 500.0,
            float(r['avg_pvp_damage'] or 0) / 5000.0,
        ]])
        
        # Нормализуем и предсказываем
        feat_scaled = self.scaler.transform(feat)
        cluster_id = int(self.kmeans.predict(feat_scaled)[0])
        
        # Расстояние до центра кластера (уверенность)
        distances = self.kmeans.transform(feat_scaled)[0]
        min_distance = distances[cluster_id]
        max_distance = distances.max()
        confidence = 1.0 - (min_distance / max_distance) if max_distance > 0 else 1.0
        
        # Находим похожих игроков из того же кластера
        similar_players = self._find_similar_players(cluster_id, player_id)
        
        cluster_info = self.cluster_labels.get(cluster_id, {})
        
        # ДЕТЕКЦИЯ БОТА на основе индивидуальных признаков
        pvp_r = float(r['pvp_ratio'] or 0)
        kpm_val = float(r['kpm'] or 0)
        sr_val = float(r['survival_rate'] or 0)
        
        bot_indicators = 0
        bot_reasons = []
        
        if pvp_r < 0.05:
            bot_indicators += 1
            bot_reasons.append(f"PvP < 5% ({pvp_r*100:.1f}%)")
        
        if kpm_val > 15:
            bot_indicators += 1
            bot_reasons.append(f"KPM > 15 ({kpm_val:.1f})")
        
        if sr_val > 0.95:
            bot_indicators += 1
            bot_reasons.append(f"SR > 95% ({sr_val*100:.1f}%)")
        
        if pvp_r < 0.02:
            bot_indicators += 1
            bot_reasons.append(f"Почти нет PvP ({pvp_r*100:.2f}%)")
        
        # Bot score: 0.0 - 1.0
        bot_score = min(1.0, bot_indicators / 4.0)
        
        # Если >= 3 признака - вероятно бот
        is_likely_bot = bot_indicators >= 3
        
        return {
            "login": r['login'],
            "cluster_id": cluster_id,
            "playstyle": cluster_info.get("name", "unknown"),
            "display_name": cluster_info.get("display_name", "Неизвестный"),
            "description": cluster_info.get("description", ""),
            "confidence": round(confidence, 3),
            "cluster_size": cluster_info.get("size", 0),
            "player_features": {
                "pvp_ratio": round(pvp_r, 3),
                "kpm": round(kpm_val, 2),
                "survival_rate": round(sr_val, 3),
                "total_battles": int(r['total_battles']),
                "active_days": int(r['active_days']),
            },
            "cluster_averages": cluster_info.get("avg_features", {}),
            "similar_players": similar_players[:5],
            "bot_detection": {
                "bot_score": round(bot_score, 3),
                "is_likely_bot": is_likely_bot,
                "indicators_count": bot_indicators,
                "reasons": bot_reasons,
            }
        }
    
    def _find_similar_players(self, cluster_id: int, exclude_player_id: int) -> List[str]:
        """Находит похожих игроков из того же кластера"""
        similar = []
        for i, (pid, label) in enumerate(zip(self.player_ids, self.labels)):
            if label == cluster_id and pid != exclude_player_id:
                similar.append(self.player_logins[i])
        return similar
    
    def get_cluster_stats(self) -> List[Dict[str, Any]]:
        """Возвращает статистику по всем кластерам"""
        stats = []
        for cluster_id in range(self.n_clusters):
            if cluster_id in self.cluster_labels:
                info = self.cluster_labels[cluster_id]
                stats.append({
                    "cluster_id": cluster_id,
                    "playstyle": info["name"],
                    "display_name": info["display_name"],
                    "description": info["description"],
                    "player_count": info["size"],
                    "avg_features": info["avg_features"],
                })
        return sorted(stats, key=lambda x: x["player_count"], reverse=True)
    
    def save_model(self):
        """Сохраняет обученную модель на диск"""
        if not self.is_trained:
            return False
        
        model_data = {
            "kmeans": self.kmeans,
            "scaler": self.scaler,
            "cluster_labels": self.cluster_labels,
            "player_ids": self.player_ids,
            "player_logins": self.player_logins,
            "labels": self.labels,
            "n_clusters": self.n_clusters,
            "trained_at": datetime.now().isoformat(),
        }
        
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            return True
        except Exception as e:
            print(f"Ошибка сохранения модели: {e}")
            return False
    
    def load_model(self) -> bool:
        """Загружает модель с диска"""
        try:
            if not Path(self.model_path).exists():
                return False
            
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.kmeans = model_data["kmeans"]
            self.scaler = model_data["scaler"]
            self.cluster_labels = model_data["cluster_labels"]
            self.player_ids = model_data["player_ids"]
            self.player_logins = model_data["player_logins"]
            self.labels = model_data["labels"]
            self.n_clusters = model_data["n_clusters"]
            self.is_trained = True
            
            return True
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            return False


async def train_playstyle_model(db, days: int = 90, n_clusters: int = 8) -> Dict[str, Any]:
    """Утилита для обучения модели (можно вызывать из cron/admin endpoint)"""
    if not SKLEARN_AVAILABLE:
        return {"error": "scikit-learn не установлен"}
    
    classifier = PlaystyleClassifier(n_clusters=n_clusters)
    
    try:
        result = await classifier.train(db, days=days)
        return {
            "status": "success",
            "trained_at": datetime.now().isoformat(),
            **result,
            "clusters": classifier.get_cluster_stats(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

