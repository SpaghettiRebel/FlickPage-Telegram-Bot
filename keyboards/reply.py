from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton


def get_main_menu():
    builder = ReplyKeyboardBuilder()

    # Добавляем кнопки
    builder.button(text="📚 Мой список")
    builder.button(text="❓ Помощь")
    builder.button(text="⚡️ Быстрый список")

    # Выстраиваем кнопки по 2 в ряд
    builder.adjust(3)

    # Возвращаем объект клавиатуры с важными параметрами
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Выберите действие из меню или введите название фильма.")