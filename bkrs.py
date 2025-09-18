#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from typing import Optional, Tuple

class ChineseDictionary:
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
        return f"{hanzi}\n{pinyin}\n{translation}"

def main():
    """Главная программа"""
    dict_app = ChineseDictionary("dictionary.sqlite")
    
    print("Китайско-русский словарь")
    print("Введите 'quit' для выхода")
    print("-" * 30)
    
    while True:
        chinese_input = input("Ввод: ").strip()
        
        if chinese_input.lower() == 'quit':
            break
            
        if not chinese_input:
            continue
            
        result = dict_app.lookup(chinese_input)
        
        if result:
            print("Вывод:")
            print(dict_app.format_output(result))
        else:
            print("Слово не найдено")
            
        print("-" * 30)

if __name__ == "__main__":
    main()