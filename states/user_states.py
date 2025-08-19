from aiogram.fsm.state import State, StatesGroup


class MovieSearch(StatesGroup):
    browsing = State()
    listing = State()
