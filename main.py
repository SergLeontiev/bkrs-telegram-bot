#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
from typing import Optional, Tuple
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()