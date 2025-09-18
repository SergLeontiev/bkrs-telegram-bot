#!/usr/bin/env python3
"""Сборка базы данных из частей"""

import os

def assemble_database():
    """Собирает database.sqlite из частей"""
    parts = []
    
    # Ищем все части файла
    for filename in sorted(os.listdir('.')):
        if filename.startswith('dictionary_part_'):
            parts.append(filename)
    
    if not parts:
        print("Части файла не найдены!")
        return False
        
    print(f"Найдено частей: {len(parts)}")
    
    # Собираем файл
    with open('dictionary.sqlite', 'wb') as outfile:
        for part in parts:
            print(f"Добавляем {part}...")
            with open(part, 'rb') as infile:
                outfile.write(infile.read())
    
    # Проверяем размер
    size_mb = os.path.getsize('dictionary.sqlite') / (1024*1024)
    print(f"✅ База собрана! Размер: {size_mb:.1f} MB")
    
    return True

if __name__ == "__main__":
    assemble_database()