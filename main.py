#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import asyncio
from typing import Optional, Tuple, Dict
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, InlineQueryHandler
import uuid

# Словарь для хранения задач debouncing по пользователям
user_search_tasks: Dict[int, asyncio.Task] = {}

def assemble_database_if_needed():
    """Собирает базу из частей если нужно"""
    if os.path.exists('dictionary.sqlite'):
        return True
        
    print("База не найдена, собираем из частей...")
    
    parts = []
    for filename in sorted(os.listdir('.')):
        if filename.startswith('dictionary_part_'):
            parts.append(filename)
    
    if not parts:
        print("❌ Части базы не найдены!")
        return False
        
    print(f"Найдено частей: {len(parts)}")
    
    with open('dictionary.sqlite', 'wb') as outfile:
        for part in parts:
            print(f"Добавляем {part}...")
            with open(part, 'rb') as infile:
                outfile.write(infile.read())
    
    size_mb = os.path.getsize('dictionary.sqlite') / (1024*1024)
    print(f"✅ База собрана! Размер: {size_mb:.1f} MB")
    return True

class ChineseDictionaryBot:
    def __init__(self, db_path: str = "dictionary.sqlite"):
        self.db_path = db_path
        
    def lookup(self, chinese_word: str) -> Optional[Tuple[str, str, str]]:
        """Поиск слова в SQLite базе"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT hanzi, pinyin, translation FROM dict 
                WHERE hanzi = ?
            ''', (chinese_word,))
            
            result = cursor.fetchone()
            return result if result else None
            
        except sqlite3.Error:
            return None
        finally:
            conn.close()
        
    def format_output(self, result: Tuple[str, str, str]) -> str:
        """Форматирование вывода: иероглифы, пиньинь, перевод"""
        hanzi, pinyin, translation = result
        
        # Заменяем \n на настоящие переносы строк
        if translation:
            translation = translation.replace('\\n', '\n')
        
        return f"{hanzi}\n{pinyin}\n{translation}"

# Создание экземпляра бота
bot_dict = ChineseDictionaryBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🇨🇳 Китайско-русский словарь\n\n"
        "Отправьте иероглифы и получите:\n"
        "• Иероглифы\n"
        "• Пиньинь (транскрипция)\n" 
        "• Русский перевод\n\n"
        "Пример: 你好"
    )

async def bkrs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /bkrs для поиска в групповых чатах"""
    if not context.args:
        await update.message.reply_text(
            "Использование: /bkrs иероглифы\n"
            "Пример: /bkrs 你好"
        )
        return
    
    # Объединяем все аргументы в одну строку
    chinese_input = ' '.join(context.args).strip()
    
    result = bot_dict.lookup(chinese_input)
    
    if result:
        translation = bot_dict.format_output(result)
        await update.message.reply_text(translation)
    else:
        await update.message.reply_text(f"Слово '{chinese_input}' не найдено")

async def perform_search(query: str, inline_query_id: str, user_id: int):
    """Выполняет поиск с задержкой"""
    try:
        # Ждем 500ms перед поиском
        await asyncio.sleep(0.5)
        
        # Ищем слово в базе
        result = bot_dict.lookup(query)
        
        if result:
            hanzi, pinyin, translation = result
            # Заменяем \n на настоящие переносы строк
            if translation:
                translation = translation.replace('\\n', '\n')
            
            formatted_result = f"{hanzi}\n{pinyin}\n{translation}"
            
            results = [
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=f"{hanzi}",
                    description=f"{pinyin} - {translation[:50]}{'...' if len(translation) > 50 else ''}",
                    input_message_content=InputTextMessageContent(formatted_result)
                )
            ]
        else:
            # Пустой результат если не найдено
            results = []
        
        # Отправляем результат (может не сработать если запрос устарел)
        try:
            from telegram import Bot
            bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
            await bot.answer_inline_query(inline_query_id, results)
        except:
            # Игнорируем ошибки (запрос мог устареть)
            pass
            
    except asyncio.CancelledError:
        # Задача была отменена (пользователь продолжил печатать)
        pass
    finally:
        # Убираем задачу из словаря
        if user_id in user_search_tasks:
            del user_search_tasks[user_id]

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка inline запросов (@bkrs_leo_bot слово) с debouncing"""
    query = update.inline_query.query.strip()
    user_id = update.inline_query.from_user.id
    inline_query_id = update.inline_query.id
    
    # Отменяем предыдущую задачу поиска для этого пользователя
    if user_id in user_search_tasks:
        user_search_tasks[user_id].cancel()
    
    if not query:
        # Пустой запрос - очищаем результаты
        await update.inline_query.answer([])
        return
    
    # Создаем новую задачу поиска с задержкой
    search_task = asyncio.create_task(
        perform_search(query, inline_query_id, user_id)
    )
    user_search_tasks[user_id] = search_task

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений (только в личных чатах)"""
    # Работает только в личных сообщениях
    if update.message.chat.type != 'private':
        return
        
    chinese_input = update.message.text.strip()
    
    result = bot_dict.lookup(chinese_input)
    
    if result:
        translation = bot_dict.format_output(result)
        await update.message.reply_text(translation)
    else:
        await update.message.reply_text("Слово не найдено")

def main():
    """Запуск бота"""
    # Собираем базу если нужно
    if not assemble_database_if_needed():
        print("❌ Не удалось собрать базу данных")
        return
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("Установите переменную TELEGRAM_BOT_TOKEN")
        return
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bkrs", bkrs_command))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()