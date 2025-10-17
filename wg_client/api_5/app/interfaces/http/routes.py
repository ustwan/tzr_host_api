"""FastAPI роуты для API 5"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.infrastructure.db.database import get_db
from app.infrastructure.db.repositories import (
    ShopRepository, ItemTemplateRepository, ShopItemRepository,
    SnapshotRepository, BotSessionRepository
)
from app.infrastructure.db.models import Base
from app.infrastructure.db.database import db
from pydantic import BaseModel


# Pydantic схемы для API
class HealthResponse(BaseModel):
    status: str
    service: str = "API 5 - Shop Parser"


class ItemResponse(BaseModel):
    id: int
    txt: str
    price: Optional[float]
    current_quality: Optional[int]
    max_quality: Optional[int]
    shop_id: Optional[int]
    template_id: Optional[int]
    owner: Optional[str]
    count: Optional[int] = None  # Количество товара в позиции (для патронов, энергомодулей)
    weight: Optional[float] = None  # Масса
    infinty: Optional[bool] = None  # Бесконечный товар
    caliber: Optional[str] = None  # Калибр (для оружия/патронов)
    added_at: Optional[str] = None  # Дата добавления


class ItemListResponse(BaseModel):
    items: List[ItemResponse]
    total: int
    page: int
    limit: int


class SnapshotResponse(BaseModel):
    id: int
    shop_id: int
    created_at: str
    items_count: int
    worker_name: Optional[str]


class SnapshotListResponse(BaseModel):
    snapshots: List[SnapshotResponse]
    total: int


class BotStatusResponse(BaseModel):
    shop_code: str
    bot_login: str
    authenticated: bool
    session_id: Optional[str]
    last_activity: Optional[str]


# Роутеры
router = APIRouter()


def item_to_response(item) -> ItemResponse:
    """Конвертация ShopItem в ItemResponse"""
    return ItemResponse(
        id=item.id,
        txt=item.txt,
        price=float(item.price) if item.price else None,
        current_quality=item.current_quality,
        max_quality=item.max_quality,
        shop_id=item.shop_id,
        template_id=item.template_id,
        owner=item.owner,
        count=item.max_count,  # Количество товара в позиции
        weight=item.weight,  # Масса
        infinty=item.infinty,  # Бесконечный
        caliber=item.caliber,  # Калибр
        added_at=item.added_at.isoformat() if item.added_at else None,  # Дата
    )


# ========== Health & Service ==========

@router.get("/healthz", response_model=HealthResponse, tags=["Health"])
async def healthz():
    """Проверка работоспособности сервиса"""
    return HealthResponse(status="ok")


@router.get("/shop/health", response_model=HealthResponse, tags=["Health"])
async def shop_health():
    """Проверка работоспособности модуля магазина"""
    return HealthResponse(status="ok", service="Shop Parser Module")


@router.get("/db/health", tags=["Health"])
async def db_health(session: Session = Depends(get_db)):
    """Проверка подключения к БД"""
    try:
        # Простой запрос к БД
        session.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ========== Items (Товары) ==========

@router.get("/items/list", response_model=ItemListResponse, tags=["Items"])
async def get_items_list(
    shop_code: Optional[str] = None,
    page: int = 1,
    limit: int = 100,
    session: Session = Depends(get_db)
):
    """
    Получить список товаров
    
    - **shop_code**: Код магазина (moscow/oasis/neva) - опционально
    - **page**: Номер страницы (с 1)
    - **limit**: Количество на странице (max 1000)
    """
    if limit > 1000:
        limit = 1000
    
    offset = (page - 1) * limit
    
    # Репозитории
    shop_repo = ShopRepository(session)
    item_repo = ShopItemRepository(session)
    
    # Получить shop_id если указан код
    shop_id = None
    if shop_code:
        shop = shop_repo.get_by_code(shop_code)
        if not shop:
            raise HTTPException(status_code=404, detail=f"Shop {shop_code} not found")
        shop_id = shop.id
    
    # Подсчёт ОБЩЕГО количества
    from app.infrastructure.db.models import ShopItemModel
    query_count = session.query(ShopItemModel)
    if shop_id:
        query_count = query_count.filter(ShopItemModel.shop_id == shop_id)
    total_count = query_count.count()
    
    # Получить товары
    items = item_repo.get_list(shop_id=shop_id, limit=limit, offset=offset)
    
    # Конвертация в response
    items_response = [item_to_response(item) for item in items]
    
    return ItemListResponse(
        items=items_response,
        total=total_count,
        page=page,
        limit=limit,
    )


@router.get("/items/{item_id}", response_model=ItemResponse, tags=["Items"])
async def get_item(item_id: int, session: Session = Depends(get_db)):
    """Получить детали товара по ID"""
    item_repo = ShopItemRepository(session)
    item = item_repo.get_by_id(item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return item_to_response(item)


# ========== Snapshots (Снимки) ==========

@router.get("/snapshots/list", response_model=SnapshotListResponse, tags=["Snapshots"])
async def get_snapshots_list(
    shop_code: Optional[str] = None,
    session: Session = Depends(get_db)
):
    """
    Получить список снимков
    
    - **shop_code**: Код магазина (опционально)
    """
    from app.infrastructure.db.models import SnapshotModel
    
    # Получить shop_id если указан
    shop_id = None
    if shop_code:
        shop_repo = ShopRepository(session)
        shop = shop_repo.get_by_code(shop_code)
        if not shop:
            raise HTTPException(status_code=404, detail=f"Shop {shop_code} not found")
        shop_id = shop.id
    
    # Запрос snapshots
    query = session.query(SnapshotModel)
    if shop_id:
        query = query.filter(SnapshotModel.shop_id == shop_id)
    
    snapshots = query.order_by(SnapshotModel.created_at.desc()).all()
    
    # Конвертация
    snapshots_response = [
        SnapshotResponse(
            id=s.id,
            shop_id=s.shop_id,
            created_at=s.created_at.isoformat(),
            items_count=s.items_count,
            worker_name=s.worker_name
        )
        for s in snapshots
    ]
    
    return SnapshotListResponse(
        snapshots=snapshots_response,
        total=len(snapshots),
    )


@router.get("/snapshots/latest", response_model=SnapshotResponse, tags=["Snapshots"])
async def get_latest_snapshot(
    shop_code: str,
    session: Session = Depends(get_db)
):
    """Получить последний снимок магазина"""
    shop_repo = ShopRepository(session)
    snapshot_repo = SnapshotRepository(session)
    
    shop = shop_repo.get_by_code(shop_code)
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {shop_code} not found")
    
    snapshot = snapshot_repo.get_latest(shop.id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No snapshots for {shop_code}")
    
    return SnapshotResponse(
        id=snapshot.id,
        shop_id=snapshot.shop_id,
        created_at=snapshot.created_at.isoformat(),
        items_count=snapshot.items_count,
        worker_name=snapshot.worker_name,
    )


# ========== Categories (Категории) ==========

@router.get("/categories/list", tags=["Categories"])
async def get_categories():
    """Получить список всех категорий магазина"""
    from app.config import config
    
    categories = [
        {"code": "k", "name": "Холодное оружие", "group": "Оружие"},
        {"code": "p", "name": "Пистолеты", "group": "Оружие"},
        {"code": "v", "name": "Винтовки/автоматы", "group": "Оружие"},
        {"code": "w", "name": "Тяжёлое оружие", "group": "Оружие"},
        {"code": "e", "name": "Энергетическое", "group": "Оружие"},
        {"code": "x", "name": "Биологическое", "group": "Оружие"},
        {"code": "g", "name": "Метательное", "group": "Оружие"},
        {"code": "m", "name": "Боевые устройства", "group": "Оружие"},
        {"code": "a", "name": "Патроны", "group": "Оружие"},
        {"code": "i", "name": "Энергомодули", "group": "Оружие"},
        {"code": "h", "name": "Каски/береты", "group": "Одежда"},
        {"code": "c", "name": "Куртки/бронежилеты", "group": "Одежда"},
        {"code": "l", "name": "Нарукавники", "group": "Одежда"},
        {"code": "t", "name": "Брюки", "group": "Одежда"},
        {"code": "b", "name": "Обувь", "group": "Одежда"},
        {"code": "f", "name": "Гражданская одежда", "group": "Одежда"},
        {"code": "q", "name": "Комплекты брони", "group": "Одежда"},
        {"code": "u", "name": "Встройки", "group": "Прочее"},
        {"code": "n", "name": "Улучшение", "group": "Прочее"},
        {"code": "j", "name": "Оборудование", "group": "Прочее"},
        {"code": "d", "name": "Медицина", "group": "Прочее"},
        {"code": "s", "name": "Ресурсы", "group": "Прочее"},
        {"code": "y", "name": "Крафт-реагенты", "group": "Прочее"},
        {"code": "r", "name": "Документы", "group": "Прочее"},
        {"code": "z", "name": "Прочее", "group": "Прочее"},
        {"code": "0", "name": "Импланты", "group": "Прочее"},
        {"code": "1", "name": "Мои вещи", "group": "Персональное"},
    ]
    
    return {"categories": categories, "total": len(categories)}


@router.get("/categories/{category_code}/items", tags=["Categories"])
async def get_items_by_category(
    category_code: str,
    shop_code: Optional[str] = None,
    limit: int = 100,
    session: Session = Depends(get_db)
):
    """
    Получить все товары из конкретной категории
    
    - **category_code**: k, p, v, h, s, y, ... (см. /categories/list)
    - **shop_code**: moscow/oasis/neva (опционально)
    - **limit**: максимум товаров (default=100, max=1000)
    """
    from app.infrastructure.db.models import ShopItemModel, ItemTemplateModel
    
    # Получить shop_id если указан
    shop_id = None
    if shop_code:
        shop_repo = ShopRepository(session)
        shop = shop_repo.get_by_code(shop_code)
        if shop:
            shop_id = shop.id
    
    # Запрос товаров по категории
    query = session.query(ShopItemModel).join(ItemTemplateModel)
    query = query.filter(ItemTemplateModel.category == category_code)
    
    if shop_id:
        query = query.filter(ShopItemModel.shop_id == shop_id)
    
    if limit > 1000:
        limit = 1000
    
    # Подсчёт ОБЩЕГО количества (до limit)
    total_count = query.count()
    
    items = query.limit(limit).all()
    
    # Конвертация (модели → entities → response)
    item_repo = ShopItemRepository(session)
    items_entities = [item_repo._model_to_entity(item) for item in items]
    items_response = [item_to_response(item) for item in items_entities]
    
    return {
        "category": category_code,
        "shop_code": shop_code,
        "items": items_response,
        "total": total_count
    }


# ========== Sellers (Продавцы) ==========

class SellerStatsResponse(BaseModel):
    owner: str
    items_count: int
    total_value: float
    min_price: Optional[float]
    max_price: Optional[float]
    avg_price: Optional[float]


@router.get("/sellers/search", tags=["Sellers"])
async def search_items_by_seller(
    owner: str,
    shop_code: Optional[str] = None,
    limit: int = 100,
    session: Session = Depends(get_db)
):
    """
    Поиск товаров по нику продавца
    
    - **owner**: Ник продавца
    - **shop_code**: moscow/oasis/neva (опционально)
    - **limit**: максимум товаров (default=100, max=1000)
    """
    from app.infrastructure.db.models import ShopItemModel
    
    # Получить shop_id если указан
    shop_id = None
    if shop_code:
        shop_repo = ShopRepository(session)
        shop = shop_repo.get_by_code(shop_code)
        if shop:
            shop_id = shop.id
    
    # Запрос товаров продавца
    query = session.query(ShopItemModel).filter(ShopItemModel.owner == owner)
    
    if shop_id:
        query = query.filter(ShopItemModel.shop_id == shop_id)
    
    if limit > 1000:
        limit = 1000
    
    total_count = query.count()
    items = query.limit(limit).all()
    
    # Конвертация (модели → entities → response)
    item_repo = ShopItemRepository(session)
    items_entities = [item_repo._model_to_entity(item) for item in items]
    items_response = [item_to_response(item) for item in items_entities]
    
    return {
        "owner": owner,
        "shop_code": shop_code,
        "items": items_response,
        "total": total_count
    }


@router.get("/sellers/stats", response_model=List[SellerStatsResponse], tags=["Sellers"])
async def get_sellers_stats(
    shop_code: Optional[str] = None,
    min_items: int = 1,
    limit: int = 100,
    session: Session = Depends(get_db)
):
    """
    Статистика по всем продавцам (ник, количество товаров, общая стоимость)
    
    - **shop_code**: moscow/oasis/neva (опционально)
    - **min_items**: минимум товаров для включения в список (default=1)
    - **limit**: максимум продавцов (default=100)
    """
    from sqlalchemy import func
    from app.infrastructure.db.models import ShopItemModel
    
    # Получить shop_id если указан
    shop_id = None
    if shop_code:
        shop_repo = ShopRepository(session)
        shop = shop_repo.get_by_code(shop_code)
        if shop:
            shop_id = shop.id
    
    # Агрегация по продавцам (исключаем infinty товары где owner=NULL)
    query = session.query(
        ShopItemModel.owner,
        func.count(ShopItemModel.id).label('items_count'),
        func.sum(ShopItemModel.price).label('total_value'),
        func.min(ShopItemModel.price).label('min_price'),
        func.max(ShopItemModel.price).label('max_price'),
        func.avg(ShopItemModel.price).label('avg_price'),
    ).filter(ShopItemModel.owner.isnot(None))
    
    if shop_id:
        query = query.filter(ShopItemModel.shop_id == shop_id)
    
    query = query.group_by(ShopItemModel.owner)
    query = query.having(func.count(ShopItemModel.id) >= min_items)
    query = query.order_by(func.count(ShopItemModel.id).desc())
    query = query.limit(limit)
    
    results = query.all()
    
    # Конвертация
    stats = [
        SellerStatsResponse(
            owner=row.owner,
            items_count=row.items_count,
            total_value=float(row.total_value) if row.total_value else 0.0,
            min_price=float(row.min_price) if row.min_price else None,
            max_price=float(row.max_price) if row.max_price else None,
            avg_price=float(row.avg_price) if row.avg_price else None,
        )
        for row in results
    ]
    
    return stats


@router.get("/sellers/{owner}/summary", tags=["Sellers"])
async def get_seller_summary(
    owner: str,
    shop_code: Optional[str] = None,
    session: Session = Depends(get_db)
):
    """
    Подробная сводка по продавцу
    
    - **owner**: Ник продавца
    - **shop_code**: moscow/oasis/neva (опционально)
    """
    from sqlalchemy import func
    from app.infrastructure.db.models import ShopItemModel, ItemTemplateModel
    
    # Получить shop_id
    shop_id = None
    if shop_code:
        shop_repo = ShopRepository(session)
        shop = shop_repo.get_by_code(shop_code)
        if shop:
            shop_id = shop.id
    
    # Общая статистика
    query = session.query(
        func.count(ShopItemModel.id).label('items_count'),
        func.sum(ShopItemModel.price).label('total_value'),
        func.min(ShopItemModel.price).label('min_price'),
        func.max(ShopItemModel.price).label('max_price'),
        func.avg(ShopItemModel.price).label('avg_price'),
    ).filter(ShopItemModel.owner == owner)
    
    if shop_id:
        query = query.filter(ShopItemModel.shop_id == shop_id)
    
    stats = query.first()
    
    if not stats or stats.items_count == 0:
        raise HTTPException(status_code=404, detail=f"Seller {owner} not found")
    
    # Статистика по категориям
    cat_query = session.query(
        ItemTemplateModel.category,
        func.count(ShopItemModel.id).label('count')
    ).join(ItemTemplateModel).filter(ShopItemModel.owner == owner)
    
    if shop_id:
        cat_query = cat_query.filter(ShopItemModel.shop_id == shop_id)
    
    cat_query = cat_query.group_by(ItemTemplateModel.category)
    categories = cat_query.all()
    
    return {
        "owner": owner,
        "shop_code": shop_code,
        "total_items": stats.items_count,
        "total_value": float(stats.total_value) if stats.total_value else 0.0,
        "min_price": float(stats.min_price) if stats.min_price else None,
        "max_price": float(stats.max_price) if stats.max_price else None,
        "avg_price": float(stats.avg_price) if stats.avg_price else None,
        "by_category": [
            {"category": cat.category, "count": cat.count}
            for cat in categories
        ]
    }


# ========== Admin (Администрирование) ==========

@router.post("/admin/snapshot/trigger", tags=["Admin"])
async def trigger_snapshot(
    shop_code: str,
    session: Session = Depends(get_db)
):
    """
    Запустить создание снимка магазина (ручной запуск)
    
    - **shop_code**: moscow/oasis/neva
    """
    from app.config import config
    from app.infrastructure.game_socket_client import GameSocketClient
    from app.parsers.shop_parser import ShopParser
    from app.usecases.parse_category import ParseCategoryUseCase
    from app.usecases.create_snapshot import CreateSnapshotUseCase
    
    # Получить конфигурацию бота
    bots_config = config.get_bots_config()
    if shop_code not in bots_config:
        raise HTTPException(status_code=400, detail=f"Unknown shop: {shop_code}")
    
    bot_config = bots_config[shop_code]
    
    # Проверить что бот включен и есть ключ
    if not bot_config.enabled:
        raise HTTPException(status_code=400, detail=f"Bot for {shop_code} is disabled")
    
    if not bot_config.login_key:
        raise HTTPException(
            status_code=503,
            detail=f"Bot key not configured for {shop_code}. Set SOVA_{shop_code.upper()}_KEY environment variable."
        )
    
    # Получить или создать shop в БД
    shop_repo = ShopRepository(session)
    shop = shop_repo.get_by_code(shop_code)
    if not shop:
        from app.domain.entities import Shop
        shop = Shop(
            code=shop_code,
            name=bot_config.shop_name,
            bot_login=bot_config.login
        )
        shop_repo.create(shop)
        session.commit()
    
    # Создать game client и авторизовать
    game_client = GameSocketClient(
        host=config.GAME_SERVER_HOST,
        port=config.GAME_SERVER_PORT,
        timeout=config.GAME_SERVER_TIMEOUT
    )
    
    try:
        # Авторизовать бота
        success, session_id = game_client.authenticate(bot_config.login, bot_config.login_key)
        if not success:
            raise HTTPException(status_code=503, detail=f"Failed to authenticate bot {bot_config.login}")
        
        # Создать parser и use cases
        template_repo = ItemTemplateRepository(session)
        item_repo = ShopItemRepository(session)
        snapshot_repo = SnapshotRepository(session)
        
        parse_category_uc = ParseCategoryUseCase(
            shop_repo=shop_repo,
            template_repo=template_repo,
            item_repo=item_repo,
            client=game_client
        )
        
        use_case = CreateSnapshotUseCase(
            shop_repo=shop_repo,
            snapshot_repo=snapshot_repo,
            item_repo=item_repo,
            parse_category_uc=parse_category_uc
        )
        
        # Запустить создание снимка
        snapshot = use_case.execute(shop_code=shop_code, worker_name="manual_trigger")
        
        # Отключиться
        game_client.disconnect()
        
        return {
            "status": "success",
            "shop_code": shop_code,
            "snapshot_id": snapshot.id,
            "items_count": snapshot.items_count,
            "created_at": snapshot.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        game_client.disconnect()
        raise HTTPException(status_code=500, detail=f"Failed to create snapshot: {str(e)}")


@router.get("/admin/bots/status", tags=["Admin"])
async def get_bots_status(session: Session = Depends(get_db)):
    """Получить статус всех ботов"""
    bot_repo = BotSessionRepository(session)
    
    statuses = []
    for shop_code in ["moscow", "oasis", "neva"]:
        bot_session = bot_repo.get_by_shop(shop_code)
        if bot_session:
            statuses.append(BotStatusResponse(
                shop_code=bot_session.shop_code,
                bot_login=bot_session.bot_login,
                authenticated=bot_session.authenticated,
                session_id=bot_session.session_id[:8] + "..." if bot_session.session_id else None,
                last_activity=bot_session.last_activity.isoformat() if bot_session.last_activity else None,
            ))
    
    return {"bots": statuses}


# ========== Analytics (Аналитика экономики) ==========

class NewItemResponse(BaseModel):
    """Новый товар"""
    item_id: int
    txt: str
    owner: str
    price: float
    category: str
    added_at: str
    snapshot_id: int


class SoldItemResponse(BaseModel):
    """Проданный товар"""
    item_id: int
    txt: str
    owner: str
    price: float
    category: str
    removed_at: str
    snapshot_id: int


class PriceChangeResponse(BaseModel):
    """Изменение цены"""
    item_id: int
    txt: str
    owner: str
    old_price: float
    new_price: float
    price_diff: float
    price_diff_percent: float
    category: str


class MarketActivityResponse(BaseModel):
    """Активность рынка"""
    period_start: str
    period_end: str
    new_items: int
    sold_items: int
    new_sellers: int
    active_sellers: int
    total_value_new: float
    total_value_sold: float
    top_categories: List[dict]


@router.get("/analytics/new-items", response_model=List[NewItemResponse], tags=["Analytics"])
async def get_new_items(
    shop_code: str = "moscow",
    since_snapshot_id: Optional[int] = None,
    hours: int = 24,
    limit: int = 100,
    session: Session = Depends(get_db)
):
    """
    Новые товары за период (появились после указанного snapshot)
    
    - **shop_code**: moscow/oasis/neva
    - **since_snapshot_id**: ID snapshot для сравнения (если None - берётся предпоследний)
    - **hours**: альтернатива - за последние N часов (default=24)
    - **limit**: максимум товаров (default=100)
    """
    from app.infrastructure.db.models import ShopItemModel, ItemTemplateModel, SnapshotModel, SnapshotItemModel
    from datetime import datetime, timedelta
    from sqlalchemy import and_, not_, exists
    
    # Получить shop
    shop_repo = ShopRepository(session)
    shop = shop_repo.get_by_code(shop_code)
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {shop_code} not found")
    
    # Определить базовый snapshot для сравнения
    if since_snapshot_id:
        base_snapshot = session.query(SnapshotModel).filter_by(id=since_snapshot_id).first()
        if not base_snapshot:
            raise HTTPException(status_code=404, detail=f"Snapshot {since_snapshot_id} not found")
    else:
        # Взять предпоследний snapshot
        snapshots = session.query(SnapshotModel).filter_by(shop_id=shop.id).order_by(SnapshotModel.created_at.desc()).limit(2).all()
        if len(snapshots) < 2:
            # Если только 1 snapshot - показать все товары
            base_snapshot = None
        else:
            base_snapshot = snapshots[1]  # Предпоследний
    
    # Найти товары которых не было в base_snapshot
    query = session.query(ShopItemModel).join(ItemTemplateModel).filter(ShopItemModel.shop_id == shop.id)
    
    if base_snapshot:
        # Товары которых НЕТ в base_snapshot
        subquery = session.query(SnapshotItemModel.item_id).filter(SnapshotItemModel.snapshot_id == base_snapshot.id)
        query = query.filter(~ShopItemModel.id.in_(subquery))
    else:
        # Если нет base_snapshot - показать товары за последние N часов
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(ShopItemModel.updated_at >= cutoff_time)
    
    items = query.order_by(ShopItemModel.updated_at.desc()).limit(limit).all()
    
    # Конвертация
    result = []
    for item in items:
        result.append(NewItemResponse(
            item_id=item.id,
            txt=item.txt,
            owner=item.owner or "unknown",
            price=float(item.price) if item.price else 0,
            category=item.template.category,
            added_at=item.updated_at.isoformat(),
            snapshot_id=session.query(SnapshotModel).filter_by(shop_id=shop.id).order_by(SnapshotModel.created_at.desc()).first().id
        ))
    
    return result


@router.get("/analytics/sold-items", response_model=List[SoldItemResponse], tags=["Analytics"])
async def get_sold_items(
    shop_code: str = "moscow",
    snapshot_id: Optional[int] = None,
    limit: int = 100,
    session: Session = Depends(get_db)
):
    """
    Проданные товары (были в старом snapshot, исчезли из нового)
    
    - **shop_code**: moscow/oasis/neva
    - **snapshot_id**: ID старого snapshot (если None - берётся предпоследний)
    - **limit**: максимум товаров (default=100)
    """
    from app.infrastructure.db.models import ShopItemModel, ItemTemplateModel, SnapshotModel, SnapshotItemModel
    
    # Получить shop
    shop_repo = ShopRepository(session)
    shop = shop_repo.get_by_code(shop_code)
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {shop_code} not found")
    
    # Определить старый и новый snapshots
    snapshots = session.query(SnapshotModel).filter_by(shop_id=shop.id).order_by(SnapshotModel.created_at.desc()).limit(2).all()
    if len(snapshots) < 2:
        return []  # Нужно минимум 2 snapshot
    
    old_snapshot = snapshots[1] if not snapshot_id else session.query(SnapshotModel).filter_by(id=snapshot_id).first()
    new_snapshot = snapshots[0]
    
    if not old_snapshot:
        raise HTTPException(status_code=404, detail="Old snapshot not found")
    
    # Найти товары которые БЫЛИ в old_snapshot но НЕТ в new_snapshot
    old_item_ids = set([si.item_id for si in session.query(SnapshotItemModel).filter_by(snapshot_id=old_snapshot.id).all()])
    new_item_ids = set([si.item_id for si in session.query(SnapshotItemModel).filter_by(snapshot_id=new_snapshot.id).all()])
    
    sold_item_ids = old_item_ids - new_item_ids
    
    if not sold_item_ids:
        return []
    
    # Получить информацию о проданных товарах (из старого snapshot)
    result = []
    for item_id in list(sold_item_ids)[:limit]:
        # Найти товар в старых данных (может быть удалён из shop_items)
        item = session.query(ShopItemModel).filter_by(id=item_id).first()
        if item and item.template:
            result.append(SoldItemResponse(
                item_id=item.id,
                txt=item.txt,
                owner=item.owner or "unknown",
                price=float(item.price) if item.price else 0,
                category=item.template.category,
                removed_at=new_snapshot.created_at.isoformat(),
                snapshot_id=new_snapshot.id
            ))
    
    return result


@router.get("/analytics/price-changes", response_model=List[PriceChangeResponse], tags=["Analytics"])
async def get_price_changes(
    shop_code: str = "moscow",
    min_change_percent: float = 10.0,
    limit: int = 100,
    session: Session = Depends(get_db)
):
    """
    Изменения цен между последними двумя snapshots
    
    - **shop_code**: moscow/oasis/neva
    - **min_change_percent**: минимальное изменение цены в % (default=10%)
    - **limit**: максимум товаров (default=100)
    """
    from app.infrastructure.db.models import ItemChangeModel, ShopItemModel, ItemTemplateModel
    
    # Получить shop
    shop_repo = ShopRepository(session)
    shop = shop_repo.get_by_code(shop_code)
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {shop_code} not found")
    
    # Получить изменения цен
    changes = session.query(ItemChangeModel).join(ShopItemModel).join(ItemTemplateModel).filter(
        ShopItemModel.shop_id == shop.id,
        ItemChangeModel.field_name == 'price',
        ItemChangeModel.old_value.isnot(None),
        ItemChangeModel.new_value.isnot(None)
    ).order_by(ItemChangeModel.changed_at.desc()).limit(limit * 2).all()  # Берём больше для фильтрации
    
    result = []
    for change in changes:
        try:
            old_price = float(change.old_value)
            new_price = float(change.new_value)
            diff = new_price - old_price
            diff_percent = (diff / old_price * 100) if old_price > 0 else 0
            
            if abs(diff_percent) >= min_change_percent:
                item = change.item
                result.append(PriceChangeResponse(
                    item_id=item.id,
                    txt=item.txt,
                    owner=item.owner or "unknown",
                    old_price=old_price,
                    new_price=new_price,
                    price_diff=diff,
                    price_diff_percent=diff_percent,
                    category=item.template.category if item.template else "unknown"
                ))
                
                if len(result) >= limit:
                    break
        except:
            continue
    
    return result


@router.get("/analytics/market-activity", response_model=MarketActivityResponse, tags=["Analytics"])
async def get_market_activity(
    shop_code: str = "moscow",
    session: Session = Depends(get_db)
):
    """
    Активность рынка между последними двумя snapshots
    
    - **shop_code**: moscow/oasis/neva
    
    Показывает:
    - Сколько новых товаров
    - Сколько продано
    - Новые продавцы
    - Топ категории по активности
    """
    from app.infrastructure.db.models import ShopItemModel, ItemTemplateModel, SnapshotModel, SnapshotItemModel
    from sqlalchemy import func
    
    # Получить shop
    shop_repo = ShopRepository(session)
    shop = shop_repo.get_by_code(shop_code)
    if not shop:
        raise HTTPException(status_code=404, detail=f"Shop {shop_code} not found")
    
    # Последние 2 snapshots
    snapshots = session.query(SnapshotModel).filter_by(shop_id=shop.id).order_by(SnapshotModel.created_at.desc()).limit(2).all()
    if len(snapshots) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 snapshots")
    
    old_snapshot = snapshots[1]
    new_snapshot = snapshots[0]
    
    # Получить ID товаров
    old_item_ids = set([si.item_id for si in session.query(SnapshotItemModel).filter_by(snapshot_id=old_snapshot.id).all()])
    new_item_ids = set([si.item_id for si in session.query(SnapshotItemModel).filter_by(snapshot_id=new_snapshot.id).all()])
    
    # Новые и проданные
    new_ids = new_item_ids - old_item_ids
    sold_ids = old_item_ids - new_item_ids
    
    # Продавцы
    old_sellers = set([item.owner for item in session.query(ShopItemModel).filter(ShopItemModel.id.in_(old_item_ids)).all() if item.owner])
    new_sellers = set([item.owner for item in session.query(ShopItemModel).filter(ShopItemModel.id.in_(new_item_ids)).all() if item.owner])
    
    # Стоимость
    new_items = session.query(ShopItemModel).filter(ShopItemModel.id.in_(new_ids)).all()
    sold_items = session.query(ShopItemModel).filter(ShopItemModel.id.in_(sold_ids)).all()
    
    total_value_new = sum([float(item.price or 0) for item in new_items])
    total_value_sold = sum([float(item.price or 0) for item in sold_items])
    
    # Топ категорий по активности (новые товары)
    category_stats = session.query(
        ItemTemplateModel.category,
        func.count(ShopItemModel.id).label('cnt')
    ).join(ShopItemModel).filter(
        ShopItemModel.id.in_(new_ids)
    ).group_by(ItemTemplateModel.category).order_by(func.count(ShopItemModel.id).desc()).limit(5).all()
    
    top_categories = [{"category": c.category, "new_items": c.cnt} for c in category_stats]
    
    return MarketActivityResponse(
        period_start=old_snapshot.created_at.isoformat(),
        period_end=new_snapshot.created_at.isoformat(),
        new_items=len(new_ids),
        sold_items=len(sold_ids),
        new_sellers=len(new_sellers - old_sellers),
        active_sellers=len(new_sellers),
        total_value_new=total_value_new,
        total_value_sold=total_value_sold,
        top_categories=top_categories
    )


