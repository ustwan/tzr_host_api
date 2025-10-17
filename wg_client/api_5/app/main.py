"""API 5 - Shop Parser: Main application
Last updated: 2025-10-11 11:30 - Fixed bot key validation
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import config
from app.interfaces.http.routes import router


# Валидация конфигурации (не останавливаем запуск API если нет ключей ботов)
try:
    config.validate()
except Exception as e:
    print(f"⚠️  Configuration warning: {e}")
    print(f"⚠️  API will start in read-only mode (workers won't be able to connect)")


# Создание FastAPI приложения
app = FastAPI(
    title="API 5 - Shop Parser",
    description="""
    # API парсинга и аналитики игровых магазинов
    
    ## Магазины
    - **Moscow** (Москва)
    - **Oasis** (Оазис)  
    - **Neva** (Нева)
    
    ## Возможности
    - 📦 Парсинг 27 категорий товаров
    - 📸 Снимки магазинов (каждый час)
    - 🔍 Поиск по категориям и продавцам
    - 📊 Статистика продавцов
    - 🤖 Мониторинг ботов-парсеров
    
    ## Авторизация
    Использует ту же авторизацию что XML Workers (боты Sova)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Health", "description": "🏥 Проверка работоспособности"},
        {"name": "Items", "description": "📦 Работа с товарами"},
        {"name": "Categories", "description": "🗂️ Категории магазина"},
        {"name": "Sellers", "description": "👤 Поиск и статистика продавцов"},
        {"name": "Snapshots", "description": "📸 Снимки магазинов"},
        {"name": "Analytics", "description": "📊 Аналитика экономики и рынка"},
        {"name": "Admin", "description": "👑 Администрирование"},
    ]
)

# CORS middleware (важно для Swagger UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Подключение роутов
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Инициализация при старте"""
    print("=" * 60)
    print("🚀 API 5 - Shop Parser")
    print(f"   Mode: {config.DB_MODE}")
    print(f"   Game Server: {config.GAME_SERVER_HOST}:{config.GAME_SERVER_PORT}")
    print(f"   Snapshot Interval: {config.SNAPSHOT_INTERVAL}s")
    
    bots = config.get_bots_config()
    enabled_bots = [code for code, bot in bots.items() if bot.enabled]
    print(f"   Bots enabled: {', '.join(enabled_bots)}")
    print("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    from app.infrastructure.db.database import db
    db.close()
    print("✓ API 5 stopped")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8085,
        reload=False,
        log_level="info"
    )


