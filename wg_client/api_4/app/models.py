"""
Pydantic модели для API_4
Модели для валидации данных API работы с логами боёв
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class LootKind(str, Enum):
    """Типы лута"""
    RESOURCE = "resource"
    MONSTER_PART = "monster_part"
    OTHER = "other"


class BattleType(str, Enum):
    """Типы боёв"""
    A = "A"  # PvP
    B = "B"  # PvE
    C = "C"  # Смешанный
    D = "D"  # Другой


class BattleInfo(BaseModel):
    """Информация о бое"""
    turns: int = Field(..., description="Количество ходов")
    participants_count: int = Field(..., description="Количество участников")
    battle_type: BattleType = Field(..., description="Тип боя")
    location: List[int] = Field(..., description="Координаты [x, y]")
    start_timestamp: int = Field(..., description="Время начала боя (Unix timestamp)")


class Participant(BaseModel):
    """Участник боя"""
    login: str = Field(..., description="Логин игрока")
    clan: Optional[str] = Field(None, description="Название клана")
    profession: Optional[int] = Field(None, description="Профессия")
    side: int = Field(..., description="Сторона (0/1)")
    rank_points: float = Field(..., description="Ранговые очки")
    pve_points: int = Field(..., description="PvE очки")
    level: int = Field(..., description="Уровень")
    gender: int = Field(..., description="Пол")
    survived: bool = Field(..., description="Выжил ли в бою")
    kills_monsters: int = Field(0, ge=0, description="Убито монстров")
    kills_players: int = Field(0, ge=0, description="Убито игроков")


class Monster(BaseModel):
    """Монстр в бою"""
    count: int = Field(..., ge=0, description="Количество")
    min_level: int = Field(..., ge=0, description="Минимальный уровень")
    max_level: int = Field(..., ge=0, description="Максимальный уровень")
    side: int = Field(..., description="Сторона")
    spec: Optional[str] = Field(None, description="Подвид монстра")

    @validator('max_level')
    def max_level_must_be_gte_min_level(cls, v, values):
        if 'min_level' in values and v < values['min_level']:
            raise ValueError('max_level должен быть >= min_level')
        return v


class Loot(BaseModel):
    """Лут из боя"""
    resources_total: Dict[str, int] = Field(default_factory=dict, description="Ресурсы")
    monster_parts_total: Dict[str, int] = Field(default_factory=dict, description="Части монстров")
    other_items: Dict[str, int] = Field(default_factory=dict, description="Другие предметы")


class BattleMeta(BaseModel):
    """Метаданные боя"""
    battle_info: BattleInfo = Field(..., description="Информация о бое")
    participants: List[Participant] = Field(..., description="Участники")
    monsters: Dict[str, Monster] = Field(..., description="Монстры")
    loot: Loot = Field(..., description="Лут")


class BattleResponse(BaseModel):
    """Ответ с информацией о бое"""
    id: int = Field(..., description="ID боя")
    ts: datetime = Field(..., description="Время боя")
    players: List[str] = Field(..., description="Список игроков")
    map: Union[List[str], str] = Field(..., description="Карта (развернутая или сжатая)")
    map_height: int = Field(..., description="Высота карты")
    map_width: int = Field(..., description="Ширина карты")
    size_bytes: int = Field(..., description="Размер файла в байтах")
    sha256: str = Field(..., description="SHA256 хеш файла")
    storage_key: str = Field(..., description="Ключ хранения")
    compressed: bool = Field(..., description="Сжат ли файл")
    meta: BattleMeta = Field(..., description="Метаданные боя")
    
    # Дополнительные поля
    turns: Optional[int] = Field(None, description="Количество ходов")
    battle_type: Optional[str] = Field(None, description="Тип боя")
    location: Optional[List[int]] = Field(None, description="Координаты")
    start_ts: Optional[datetime] = Field(None, description="Время начала")
    players_cnt: Optional[int] = Field(None, description="Количество игроков")
    monsters_cnt: Optional[int] = Field(None, description="Количество монстров")
    entities_cnt: Optional[int] = Field(None, description="Общее количество сущностей")


class BattleListItem(BaseModel):
    """Элемент списка боёв"""
    id: int = Field(..., description="ID боя")
    ts: datetime = Field(..., description="Время боя")
    players: List[str] = Field(..., description="Список игроков")
    battle_type: str = Field(..., description="Тип боя")
    duration: int = Field(..., description="Длительность в секундах")
    monsters_count: int = Field(..., description="Количество монстров")
    location: Optional[List[int]] = Field(None, description="Координаты")


class BattleListResponse(BaseModel):
    """Ответ со списком боёв"""
    battles: List[BattleListItem] = Field(..., description="Список боёв")
    total: int = Field(..., description="Общее количество")
    page: int = Field(..., description="Текущая страница")
    limit: int = Field(..., description="Количество на странице")


class BattleSearchResponse(BaseModel):
    """Ответ с результатами поиска боёв"""
    battles: List[BattleListItem] = Field(..., description="Найденные бои")
    total: int = Field(..., description="Общее количество найденных")
    page: int = Field(..., description="Текущая страница")
    limit: int = Field(..., description="Количество на странице")


class BattleSyncResponse(BaseModel):
    """Ответ синхронизации"""
    synced: int = Field(..., description="Количество синхронизированных файлов")
    total: int = Field(..., description="Общее количество файлов")
    errors: List[str] = Field(default_factory=list, description="Ошибки при обработке")


class BattleRawResponse(BaseModel):
    """Ответ с сырыми данными боя"""
    battle_id: int = Field(..., description="ID боя")
    raw_data: str = Field(..., description="Сырые данные (XML)")


class HealthResponse(BaseModel):
    """Ответ проверки здоровья"""
    status: str = Field(..., description="Статус сервиса")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время проверки")


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    error: str = Field(..., description="Описание ошибки")
    detail: Optional[str] = Field(None, description="Детали ошибки")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время ошибки")


# Модели для аналитики

class PlayerStats(BaseModel):
    """Статистика игрока"""
    player_id: int = Field(..., description="ID игрока")
    login: str = Field(..., description="Логин")
    battles_count: int = Field(..., description="Количество боёв")
    wins: int = Field(..., description="Побед")
    losses: int = Field(..., description="Поражений")
    kills_monsters: int = Field(..., description="Убито монстров")
    kills_players: int = Field(..., description="Убито игроков")
    rank_points_avg: float = Field(..., description="Средние ранговые очки")
    pve_points_avg: float = Field(..., description="Средние PvE очки")


class ClanStats(BaseModel):
    """Статистика клана"""
    clan_id: int = Field(..., description="ID клана")
    name: str = Field(..., description="Название клана")
    members_count: int = Field(..., description="Количество участников")
    battles_count: int = Field(..., description="Количество боёв")
    wins: int = Field(..., description="Побед")
    losses: int = Field(..., description="Поражений")


class ResourceStats(BaseModel):
    """Статистика ресурса"""
    resource_id: int = Field(..., description="ID ресурса")
    name: str = Field(..., description="Название ресурса")
    total_quantity: int = Field(..., description="Общее количество")
    battles_count: int = Field(..., description="Количество боёв с ресурсом")
    avg_per_battle: float = Field(..., description="Среднее количество за бой")


class MonsterStats(BaseModel):
    """Статистика монстра"""
    monster_id: int = Field(..., description="ID монстра")
    kind: str = Field(..., description="Вид монстра")
    spec: Optional[str] = Field(None, description="Подвид")
    battles_count: int = Field(..., description="Количество боёв")
    total_count: int = Field(..., description="Общее количество")
    avg_per_battle: float = Field(..., description="Среднее количество за бой")


# Модели для витрин данных

class DailyPlayerFeatures(BaseModel):
    """Ежедневные фичи игрока"""
    player_id: int
    date: datetime
    battles_count: int
    wins: int
    losses: int
    kills_monsters: int
    kills_players: int
    rank_points_total: float
    pve_points_total: int
    survival_rate: float
    kills_per_turn: float
    activity_score: float


class DailyClanFeatures(BaseModel):
    """Ежедневные фичи клана"""
    clan_id: int
    date: datetime
    members_count: int
    battles_count: int
    wins: int
    losses: int
    total_rank_points: float
    total_pve_points: int
    avg_survival_rate: float
    avg_kills_per_turn: float


class ResourceAnomaly(BaseModel):
    """Аномалия в ресурсах"""
    resource_id: int
    resource_name: str
    date: datetime
    quantity: int
    z_score: float
    is_anomaly: bool
    threshold: float


class BotSuspicion(BaseModel):
    """Подозрение на бота"""
    player_id: int
    login: str
    date: datetime
    suspicion_score: float
    reasons: List[str]
    is_bot: bool
    confidence: float
