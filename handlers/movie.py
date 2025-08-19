import requests
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import movie_token

from keyboards.inline import Paginator
from states.user_states import MovieSearch
from database import add_movie_to_watchlist, check_movie

router = Router()


def search(query: str):
    headers = {'X-API-KEY': movie_token,
               'Content-Type': 'application/json'}
    response = requests.get(f"https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword?keyword={query}&page=1", headers=headers)
    if response.status_code != 200:
        return None
    return response.json()['films']


def get_pagination_keyboard(current_page: int, total_pages: int):
    builder = InlineKeyboardBuilder()

    if current_page > 0:
        builder.button(
            text="⬅️ Назад",
            callback_data=Paginator(action="prev", current_page=current_page).pack()
        )

    builder.button(text="➕ Добавить",
                   callback_data=Paginator(action="add", current_page=current_page).pack())

    if current_page < total_pages - 1:
        builder.button(
            text="Вперед ➡️",
            callback_data=Paginator(action="next", current_page=current_page).pack()
        )

    builder.adjust(3)
    return builder.as_markup()


@router.message()
async def search_movie(msg: types.Message, state: FSMContext):
    movies = ""
    if msg.text:
        movies = search(msg.text)

    if not movies:
        await msg.answer(
            text="Для поиска просто отправьте название фильма. Например – 'Гарри Поттер'.")

    await state.update_data(results=movies, total=len(movies))

    await state.set_state(MovieSearch.browsing)

    movie = movies[0]
    caption = f"<b>{movie['nameRu'] if 'nameRu' in movie.keys() else movie['nameEn']}, {movie['year']}</b> (1/{len(movies)})"
    keyboard = get_pagination_keyboard(
        current_page=0,
        total_pages=len(movies),
    )

    await msg.answer_photo(
        photo=movie['posterUrlPreview'],
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(MovieSearch.browsing, Paginator.filter(F.action == "add"))
async def add_to_watchlist_handler(callback: types.CallbackQuery, callback_data: Paginator, state: FSMContext):
    data = await state.get_data()
    search_results = data.get('results', [])
    movie_data = search_results[callback_data.current_page]
    movie_id = movie_data['filmId']
    user_id = callback.from_user.id

    if not movie_id or not movie_data:
        await callback.message.answer(text="Что-то пошло не так, попробуйте снова.")
        await state.clear()
        return
    if not await check_movie(user_id, movie_id):
        await add_movie_to_watchlist(user_id, movie_id, movie_data)

        await callback.message.answer(
            text=f"Фильм «<b>{movie_data['nameRu'] if 'nameRu' in movie_data.keys() else movie_data['nameEn']}</b>» "
                 f"успешно добавлен в ваш список!",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            text=f"Фильм «<b>{movie_data['nameRu'] if 'nameRu' in movie_data.keys() else movie_data['nameEn']}</b>» "
                 f"уже есть в вашем списке.",
            parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(MovieSearch.browsing, Paginator.filter())
async def pagination_handler(callback: types.CallbackQuery, callback_data: Paginator, state: FSMContext):
    # Получаем данные из состояния FSM
    data = await state.get_data()
    search_results = data.get('results', [])
    total_pages = data.get('total', 0)

    current_page = callback_data.current_page

    # Определяем новую страницу
    if callback_data.action == "next":
        new_page = current_page + 1
    elif callback_data.action == "prev":
        new_page = current_page - 1
    else:
        # На всякий случай
        new_page = current_page

    # Проверяем, что не вышли за границы
    if 0 <= new_page < total_pages:
        # Обновляем данные в состоянии
        await state.update_data(current_page=new_page)

        # Получаем данные нового фильма
        movie = search_results[new_page]
        caption = f"<b>{movie['nameRu'] if 'nameRu' in movie.keys() else movie['nameEn']}, {movie['year']}</b> ({new_page + 1}/{total_pages})"
        keyboard = get_pagination_keyboard(
            current_page=new_page,
            total_pages=total_pages
        )

        await callback.message.edit_media(
            media=types.InputMediaPhoto(
                media=movie['posterUrlPreview'],
                caption=caption,
                parse_mode="HTML"
            ),
            reply_markup=keyboard
        )

    await callback.answer()
