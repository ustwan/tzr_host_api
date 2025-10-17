#!/usr/bin/env python3
"""Тест парсинга группы патронов"""
import sys
sys.path.insert(0, '/app')

from app.config import config
from app.infrastructure.game_socket_client import GameSocketClient

shop_code = "moscow"
bot_config = config.get_bots_config()[shop_code]

print("=" * 80)
print("ТЕСТ ПАРСИНГА ГРУППЫ ПАТРОНОВ")
print("=" * 80)

client = GameSocketClient(
    host=config.GAME_SERVER_HOST,
    port=config.GAME_SERVER_PORT,
    timeout=config.GAME_SERVER_TIMEOUT
)

success, _ = client.authenticate(bot_config.login, bot_config.login_key)
if not success:
    print("❌ Авторизация не удалась")
    sys.exit(1)

print("✓ Авторизация успешна\n")

# Запрос первой страницы категории 'a' (патроны)
print("📄 Запрос категории 'a' (патроны) страница 0...")
xml = client.fetch_shop_category("a", 0)
if xml:
    print(f"Ответ длиной {len(xml)} символов:")
    print("-" * 80)
    print(xml[:2000])  # Первые 2000 символов
    print("-" * 80)
else:
    print("❌ Нет ответа")
    client.disconnect()
    sys.exit(1)

# Попробуем раскрыть первую группу
print("\n📦 Запрос группы патронов name:b1-a3, type:2.0...")
filter_str = "name:b1-a3,type:2.0"
xml_group = client.fetch_shop_category("a", 0, filter_str)
if xml_group:
    print(f"Ответ группы длиной {len(xml_group)} символов:")
    print("-" * 80)
    print(xml_group)
    print("-" * 80)
else:
    print("❌ Нет ответа группы")

client.disconnect()
print("\n✓ Готово")






