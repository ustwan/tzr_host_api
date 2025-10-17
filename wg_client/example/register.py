from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommand
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from datetime import datetime
import re

import mysql.connector
import asyncio
import hashlib
import socket

API_TOKEN = ''

REQUIRED_GROUP_ID = '' # ID группы

MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'tzserver'
}

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# Машина состояний
class RegistrationStates(StatesGroup):
    waiting_for_login = State()
    waiting_for_gender = State()        # новый шаг
    waiting_for_password = State()

class RecoverStates(StatesGroup):
    waiting_for_password = State()


gender_kb = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="♀ Женский", callback_data="0"),
        InlineKeyboardButton(text="♂ Мужской", callback_data="1"),
    ]]
)
def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)


# Проверка, состоит ли пользователь в группе
async def is_user_in_group(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(REQUIRED_GROUP_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def send_xml_to_server(XML, host='127.0.0.1', port=5190):
    # Создание TCP-сокета
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # Подключение к серверу
            sock.connect((host, port))
            print(f"Соединение установлено с {host}:{port}")

            #while True:
            # Формирование XML

            # Отправка XML
            sock.sendall(XML.encode('utf-8'))
            #print(f"Отправлено: {XML}")


        except ConnectionRefusedError:
            print(f"Не удалось подключиться к {host}:{port}")
        except Exception as e:
            print(f"Произошла ошибка: {e}")

# Старт регистрации
@dp.message(Command("register"))
async def start_registration(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        if message.chat.id == REQUIRED_GROUP_ID:
            await message.reply("Пожалуйста, отправьте команду в личные сообщения.")
        return

    user_id = message.from_user.id

    if not await is_user_in_group(user_id):
        await message.reply("Вы должны состоять в группе, чтобы использовать эту команду.")
        return

    # Проверяем, зарегистрирован ли пользователь
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Проверяем количество зарегистрированных персонажей
        cursor.execute("SELECT COUNT(*) FROM tgplayers WHERE telegram_id = %s", (user_id,))
        result = cursor.fetchone()

        if result and result[0] >= 5:
            await message.reply("Вы уже зарегистрировали максимум персонажей!")
        else:
            await message.reply("Введите логин персонажа:")
            await state.set_state(RegistrationStates.waiting_for_login)
    finally:
        cursor.close()
        conn.close()


# Получение логина
@dp.message(RegistrationStates.waiting_for_login, F.text, ~F.text.startswith('/'))
async def get_login(message: types.Message, state: FSMContext):
    login = message.text

   # Проверяем, что логин:
    #  — либо строго 1–16 латинских букв: ^[a-zA-Z]{1,16}$
    #  — либо строго 1–16 русских букв (включая 'ё'): ^[а-яА-ЯёЁ]{1,16}$
    # Добавляем lookahead `(?=.*[a-zA-Z])` — в логине
    # должна быть хотя бы одна английская буква
    pattern_en = r'^(?=.*[a-zA-Z])[a-zA-Z0-9_\-\ ]{3,16}$'

    # должна быть хотя бы одна русская буква (учитываем ё/Ё)
    pattern_ru = r'^(?=.*[а-яА-ЯёЁ])[а-яА-ЯёЁ0-9_\-\ ]{3,16}$'

    if not (re.fullmatch(pattern_en, login) or re.fullmatch(pattern_ru, login)):
        await message.reply(
            "Некорректный логин. Логин должен быть длиной от 3 до 16 символов и "
            "состоять из русских или английских букв, разрешены символы '-', '_', цифры и пробел ."
        )
        return

    # Проверка на существующий логин
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT login FROM users WHERE login = %s", (login,))
        result = cursor.fetchone()

        if result:
            await message.reply("Этот логин уже занят. Пожалуйста, выберите другой.")
            return

        # Сохраняем логин во временном хранилище
        await state.update_data(login=login)
        await message.reply("Выберите пол персонажа:", reply_markup=gender_kb)
        await state.set_state(RegistrationStates.waiting_for_gender)
    finally:
        cursor.close()
        conn.close()

# выбор пола (callback «0»/«1»)

@dp.callback_query(
    F.data.in_(("0", "1")),
    RegistrationStates.waiting_for_gender,
)
async def step_gender(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    gender = int(callback.data)
    await state.update_data(gender=gender)

    await callback.message.edit_text("Теперь введите пароль (6‑20 ASCII‑символов):")
    await state.set_state(RegistrationStates.waiting_for_password)


# Получение пароля и завершение регистрации
@dp.message(RegistrationStates.waiting_for_password, F.text, ~F.text.startswith('/'))
async def get_password(message: types.Message, state: FSMContext):
    password = message.text
    user_id = message.from_user.id
    username = message.from_user.username

    # Получаем данные из хранилища
    data = await state.get_data()
    gender = data.get("gender")
    login = data.get("login")

    pattern_ascii = r'^[\x20-\x7E]{6,20}$'

    if not re.fullmatch(pattern_ascii, password):
        await message.reply(
            "Пароль должен быть длиной от 6 до 20 символов "
            "и состоять из латиницы."
        )
        return

    # Сохраняем данные в базе
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO tgplayers (telegram_id, username, login) VALUES (%s, %s, %s)",
            (user_id, username, login)
        )

        xml = (
            f'<ADDUSER l="{login}" '
            f'p="{encrypt(password, "0123456789ABCDEF0123456789ABCDEF")}" '
            f'g="{gender}" '
            f'm="test@test.ru"/>\0'
        )
        send_xml_to_server(xml)
        print(xml)

        conn.commit()
        await message.reply("Вы успешно зарегистрированы в игре!")
    except Exception as e:
        await message.reply(f"Ошибка при регистрации: {e}")
    finally:
        cursor.close()
        conn.close()

    # Завершаем FSM
    await state.clear()

def encrypt(psw, key):
    # Формируем строку для хеширования
    concatenated_string = (
        psw[0] + key[:10] + psw[1:] + key[10:]
    ).replace(" ", "")

    # Генерируем SHA1-хеш строки
    sha1_hash = hashlib.sha1(concatenated_string.encode("ascii")).hexdigest().upper()

    # Индексы символов для извлечения из хеша
    indices = [
        30, 26, 24, 39, 2, 15, 1, 4, 5, 18,
        27, 38, 10, 19, 33, 17, 7, 36, 34, 31,
        8, 14, 23, 21, 29, 3, 32, 25, 37, 20,
        28, 11, 22, 16, 35, 0, 6, 9, 13, 12
    ]

    # Формируем результат из символов хеша по заданным индексам
    result = "".join(sha1_hash[index] for index in indices)

    return result

# Команда /сбросить_пароль
@dp.message(Command("recover"))
async def reset_password(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        if message.chat.id == REQUIRED_GROUP_ID:
            await message.reply("Пожалуйста, отправьте команду в личные сообщения.")
        return

    user_id = message.from_user.id

    # Подключение к базе данных
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Проверяем, зарегистрирован ли пользователь
        cursor.execute("SELECT COUNT(*) FROM tgplayers WHERE telegram_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result or result[0] == 0:
            await message.reply("Вы не зарегистрированы в игре. Используйте команду для регистрации.")
            return

        await message.reply("Введите новый пароль для всех ваших персонажей:")

        # Сохраняем id пользователя в FSM контексте, чтобы отслеживать, кому принадлежит процесс
        await state.update_data(user_id=user_id)

        # Устанавливаем состояние ожидания нового пароля
        await state.set_state(RecoverStates.waiting_for_password)

    except Exception as e:
        await message.reply(f"Ошибка: {e}")
    finally:
        # Закрываем соединение после завершения работы
        conn.close()

# Получение пароля и завершение восстановления
@dp.message(RecoverStates.waiting_for_password, F.text, ~F.text.startswith('/'))
async def get_new_password(message: types.Message, state: FSMContext):
    # Получаем данные из состояния FSM
    user_data = await state.get_data()
    user_id = user_data.get("user_id")

    if user_id != message.from_user.id:
        # Игнорируем сообщения, не относящиеся к текущему пользователю
        return

    new_password = message.text

    pattern_ascii = r'^[\x20-\x7E]{6,20}$'

    if not re.fullmatch(pattern_ascii, new_password):
        await message.reply(
            "Пароль должен быть длиной от 6 до 20 символов "
            "и состоять из латиницы."
        )
        return

    # Подключение к базе данных
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Получаем логины всех персонажей пользователя
        cursor.execute("SELECT login FROM tgplayers WHERE telegram_id = %s", (user_id,))
        logins = cursor.fetchall()

        if not logins:
            await message.reply("У вас нет зарегистрированных персонажей.")
            return

        # Обновляем пароль для всех найденных логинов в таблице users
        for login in logins:
            XML = f'<NEWPAS l=\"{login[0]}\" pwd2=\"{encrypt(new_password, "0123456789ABCDEF0123456789ABCDEF")}\"/>\0'
            #print(XML)
            send_xml_to_server(XML)

        conn.commit()

        await message.reply("Пароль успешно обновлён для всех ваших персонажей!")
        #Завершаем FSM
        #await state.clear()

    except Exception as e:
        await message.reply(f"Ошибка при обновлении пароля: {e}")
    finally:
        cursor.close()
        conn.close()
        # Завершаем FSM
        await state.clear()

@dp.message(Command("cancel"), flags={"state": "*"})
async def cancel_process(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply("Действие отменено. Вы можете начать заново.", reply_markup=types.ReplyKeyboardRemove())

async def set_commands():
    commands = [
        #BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="register", description="Зарегистрироваться в игре"),
        BotCommand(command="recover", description="Изменить пароль"),
        BotCommand(command="cancel", description="Отменить текущее действие"),
        #BotCommand(command="помощь", description="Получить справку о боте")
    ]
    await bot.set_my_commands(commands)

# Запуск бота
async def main():
    await set_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

