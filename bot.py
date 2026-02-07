#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import os
import logging
import json
from datetime import date
from collections import defaultdict

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен из переменных окружения
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Файл для данных
DATA_FILE = "mood_data.json"

# Загрузка данных
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                mood_data = defaultdict(lambda: defaultdict(list))
                for user_id, dates in data.items():
                    for date_str, scores in dates.items():
                        mood_data[int(user_id)][date_str] = scores
                return mood_data
    except Exception as e:
        logger.error(f"Ошибка загрузки: {e}")
    return defaultdict(lambda: defaultdict(list))

# Сохранение данных
def save_data(data):
    try:
        save_dict = {}
        for user_id, dates in data.items():
            save_dict[str(user_id)] = dict(dates)
        
        with open(DATA_FILE, "w") as f:
            json.dump(save_dict, f, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")

# Загружаем данные
mood_data = load_data()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я трекер настроения. 📊\n\n"
        "Отправь мне цифру от 0 до 10 для оценки настроения.\n"
        "Используй /mood для просмотра графика.\n"
        "/help - справка"
    )

# Команда /help
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 Команды:\n"
        "/start - начать\n"
        "/help - справка\n"
        "/mood - график\n\n"
        "📊 Шкала:\n"
        "0-2: 😔 плохо\n"
        "3-4: 😟 не очень\n"
        "5-6: 😐 нормально\n"
        "7-8: 🙂 хорошо\n"
        "9-10: 😄 отлично!"
    )

# Создание графика
def create_graph(scores):
    plt.figure(figsize=(10, 6))
    
    x = range(1, len(scores) + 1)
    plt.plot(x, scores, 'o-', linewidth=2, markersize=8)
    
    plt.title(f"Настроение за {date.today().strftime('%d.%m.%Y')}")
    plt.xlabel("Измерение")
    plt.ylabel("Оценка (0-10)")
    plt.ylim(0, 10.5)
    plt.grid(True, alpha=0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    return buf

# Команда /mood
async def mood_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = date.today().isoformat()
    
    scores = mood_data[user_id][today]
    
    if not scores:
        await update.message.reply_text("Нет данных за сегодня. Отправь первую оценку!")
        return
    
    try:
        chart = create_graph(scores)
        
        caption = (
            f"📊 Статистика:\n"
            f"Оценок: {len(scores)}\n"
            f"Среднее: {np.mean(scores):.1f}/10\n"
            f"Максимум: {max(scores)}/10\n"
            f"Минимум: {min(scores)}/10"
        )
        
        await update.message.reply_photo(photo=chart, caption=caption)
        
    except Exception as e:
        logger.error(f"Ошибка графика: {e}")
        await update.message.reply_text("Ошибка создания графика 😔")

# Обработка оценок
async def handle_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    try:
        score = float(text)
        if 0 <= score <= 10:
            score = round(score, 1)
            today = date.today().isoformat()
            mood_data[user_id][today].append(score)
            
            # Сохраняем
            save_data(mood_data)
            
            scores = mood_data[user_id][today]
            avg = np.mean(scores)
            
            await update.message.reply_text(
                f"✅ Сохранено: {score}/10\n"
                f"📊 Всего: {len(scores)} записей\n"
                f"📈 Среднее: {avg:.1f}/10\n\n"
                "Используй /mood для графика"
            )
        else:
            await update.message.reply_text("Число должно быть от 0 до 10")
    except:
        await update.message.reply_text("Отправь цифру от 0 до 10")

# Основная функция
def main():
    if not TOKEN:
        logger.error("Токен не установлен! Укажите TELEGRAM_TOKEN")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("mood", mood_graph))
    
    # Оценки (числа)
    num_filter = filters.Regex(r'^\d+(\.\d+)?$')
    app.add_handler(MessageHandler(num_filter & ~filters.COMMAND, handle_score))
    
    # Прочие сообщения
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~num_filter,
        lambda u, c: u.message.reply_text("Отправь цифру от 0 до 10 или /help")
    ))
    
    logger.info("Бот запускается...")
    app.run_polling()

if __name__ == "__main__":
    main()

