from aiogram.filters.callback_data import CallbackData


class Paginator(CallbackData, prefix="pag"):
    action: str  # 'prev' или 'next'
    current_page: int
