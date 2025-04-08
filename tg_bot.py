import os
import random
import json
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# Словарь для хранения времени уведомлений пользователей
user_scheduled_times = {}

async def load_love_messages():
    """Загружает сообщения из JSON-файла"""
    try:
        with open('messages.json', 'r', encoding='utf-8') as file:
            messages = json.load(file)
            return messages
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка загрузки JSON: {e}")
        # Фолбэк сообщения, если файл не найден или поврежден
        return [
            "Я тебя люблю! ❤️",
            "Ты самое лучшее, что со мной случилось! 💖",
            "С тобой каждый день становится лучше! 🌟",
            "Ты мое солнышко! ☀️"
        ]

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    """Обработчик команды /start с клавиатурой выбора времени"""
    await message.reply("Привет! Я буду напоминать тебе о любви каждый день в выбранное время!")
    
    # Создаем клавиатуру с выбором времени (0-23 часа)
    times_left = [f"{i}:00" for i in range(0, 12)]
    times_right = [f"{i}:00" for i in range(12, 24)]
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=left, callback_data=f"time_{i}"),
                InlineKeyboardButton(text=right, callback_data=f"time_{i+12}")
            ] for i, (left, right) in enumerate(zip(times_left, times_right))
        ]
    )
    
    await message.reply(
        "Выбери время, когда ты хочешь получать сообщения:",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data.startswith('time_'))
async def process_time_selection(callback_query: types.CallbackQuery):
    """Обработчик выбора времени через инлайн-кнопки"""
    await callback_query.answer()  # Важно: подтверждаем получение callback
    
    try:
        user_id = callback_query.from_user.id
        selected_hour = int(callback_query.data.split('_')[1])
        
        if selected_hour < 0 or selected_hour > 23:
            raise ValueError("Некорректное время")
        
        # Сохраняем выбор пользователя
        user_scheduled_times[user_id] = selected_hour
        
        # Удаляем старую задачу, если она существует
        old_job = scheduler.get_job(f"love_msg_{user_id}")
        if old_job:
            old_job.remove()
        
        # Добавляем новую задачу
        scheduler.add_job(
            send_love_message,
            'cron',
            hour=selected_hour,
            minute=0,
            args=[user_id],
            id=f"love_msg_{user_id}"
        )
        
        await callback_query.message.answer(
            f"✅ Отлично! Теперь ты будешь получать сообщения каждый день в {selected_hour}:00!"
        )
        
    except (ValueError, IndexError) as e:
        print(f"Ошибка обработки callback: {e}")
        await callback_query.message.answer("Произошла ошибка. Пожалуйста, попробуйте еще раз.")

async def send_love_message(user_id: int):
    """Отправляет случайное любовное сообщение пользователю"""
    try:
        love_messages = await load_love_messages()
        random_message = random.choice(love_messages)
        await bot.send_message(user_id, random_message)
    except Exception as e:
        print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")

@dp.message(Command("current_time"))
async def show_current_time(message: types.Message):
    """Показывает текущее выбранное время уведомлений"""
    user_id = message.from_user.id
    if user_id in user_scheduled_times:
        await message.reply(
            f"Сейчас ты получаешь сообщения в {user_scheduled_times[user_id]}:00"
        )
    else:
        await message.reply("Ты еще не выбрал время для уведомлений. Напиши /start")

async def on_startup():
    """Запуск планировщика при старте бота"""
    if not scheduler.running:
        scheduler.start()
        print("Планировщик запущен")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())