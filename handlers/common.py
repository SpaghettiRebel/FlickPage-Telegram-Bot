from aiogram import F, Router, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.inline import Paginator
from keyboards.reply import get_main_menu
from database import get_user_watchlist, remove_movie_from_watchlist
from states.user_states import MovieSearch

router = Router()


@router.message(CommandStart())
async def cmd_start(msg: types.Message):
    await msg.answer(text='Привет! FlickPage – это бот для быстрого поиска фильмов, сериалов и мультфильмов, '
                          'а также создания списков с ними. \n\nДля поиска просто отправьте название фильма.',
                     reply_markup=get_main_menu())


@router.message(Command("help"))
async def cmd_help(msg: types.Message):
    await msg.answer(text='Для поиска фильма, сериала или мультфильма просто отправьте его название.\n/help – '
                          'помощь\n/list – открыть список\n/fast_list – просмотреть текстовую версию списка без '
                          'возможности редактирования\n\nПо иным вопросам: @Spaghettireb31')


@router.message(F.text == "❓ Помощь")
async def help_button_handler(msg: types.Message):
    await cmd_help(msg)


@router.message(Command("list"))
async def cmd_lists(msg: types.Message, state: FSMContext):
    movies = await get_user_watchlist(msg.from_user.id)
    if not movies:
        await msg.answer(text="Вы пока ничего не добавили в свой список(")
        return
    await state.set_state(MovieSearch.listing)
    await msg.answer(text='Вот что вы хотели посмотреть: ')
    await state.update_data(results=movies, total=len(movies))
    movie = eval(movies[0][1])
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


def get_pagination_keyboard(current_page: int, total_pages: int):
    builder = InlineKeyboardBuilder()

    if current_page > 0:
        builder.button(
            text="⬅️ Назад",
            callback_data=Paginator(action="prev", current_page=current_page).pack()
        )

    builder.button(text="❌ Удалить",
                   callback_data=Paginator(action="del", current_page=current_page).pack())

    if current_page < total_pages - 1:
        builder.button(
            text="Вперед ➡️",
            callback_data=Paginator(action="next", current_page=current_page).pack()
        )

    builder.adjust(3)
    return builder.as_markup()


@router.callback_query(MovieSearch.listing, Paginator.filter(F.action == "del"))
async def delete_handler(callback: types.CallbackQuery, callback_data: Paginator, state: FSMContext):
    data = await state.get_data()
    movies = data.get('results', [])
    total_pages = data.get('total', 0)
    current_page = callback_data.current_page

    # достаём данные о фильме
    movie_data = eval(movies[current_page][1])
    movie_id = movie_data['filmId']
    user_id = callback.from_user.id

    if not movie_id or not movie_data:
        await callback.message.answer("Что-то пошло не так, попробуйте снова.")
        await state.clear()
        return

    # удаляем фильм из базы
    await remove_movie_from_watchlist(user_id, movie_id)

    # удаляем фильм из локального списка
    movies.pop(current_page)
    total_pages -= 1

    # если после удаления мы оказались "за пределами", смещаем страницу
    if current_page >= total_pages and total_pages > 0:
        current_page = total_pages - 1

    # обновляем состояние
    await state.update_data(results=movies, total=total_pages, current_page=current_page)

    await callback.message.answer(
        text=f"Фильм «<b>{movie_data.get('nameRu') or movie_data.get('nameEn')}</b>» успешно удалён!",
        parse_mode="HTML"
    )

    # если фильмы ещё остались, показываем следующий
    if total_pages > 0:
        await pagination_handler(
            callback=callback,
            callback_data=Paginator(action="show", current_page=current_page),
            state=state
        )
    else:
        # если список пуст
        await callback.message.edit_caption("Список пуст 🎬", reply_markup=None)

    await callback.answer()


@router.callback_query(MovieSearch.listing, Paginator.filter())
async def pagination_handler(callback: types.CallbackQuery, callback_data: Paginator, state: FSMContext):
    data = await state.get_data()
    movies = data.get('results', [])
    total_pages = data.get('total', 0)
    current_page = data.get('current_page', 0)

    # обновляем страницу в зависимости от действия
    if callback_data.action == "next":
        current_page = min(current_page + 1, total_pages - 1)
    elif callback_data.action == "prev":
        current_page = max(current_page - 1, 0)
    elif callback_data.action == "show":
        # "show" используется после удаления — страница уже обновлена
        pass
    else:
        # если пришёл неизвестный action, просто выходим
        await callback.answer()
        return

    # если список пуст
    if total_pages == 0 or not movies:
        await callback.message.edit_caption("Список пуст 🎬", reply_markup=None)
        await state.update_data(current_page=0)
        await callback.answer()
        return

    # обновляем состояние
    await state.update_data(current_page=current_page)

    # показываем текущий фильм
    movie = eval(movies[current_page][1])
    caption = (
        f"<b>{movie.get('nameRu') or movie.get('nameEn')}, {movie['year']}</b> "
        f"({current_page + 1}/{total_pages})"
    )
    keyboard = get_pagination_keyboard(
        current_page=current_page,
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


@router.message(F.text == "📚 Мой список")
async def lists_button_handler(msg: types.Message, state: FSMContext):
    await cmd_lists(msg, state)


@router.message(Command("fast_list"))
async def cmd_fast_list(msg: types.Message):
    movies = await get_user_watchlist(msg.from_user.id)
    if not movies:
        await msg.answer(text="Вы пока ничего не добавили в свой список(")
        return
    ans = ""
    for i in range(len(movies)):
        ans += f"{i+1}. <b>{eval(movies[i][1])['nameRu'] if 'nameRu' in eval(movies[i][1]).keys() else eval(movies[i][1])['nameEn']}</b>, {eval(movies[i][1])['year']}\n"
    await msg.answer(text=ans, parse_mode="HTML")


@router.message(F.text == "⚡️ Быстрый список")
async def lists_button_handler(msg: types.Message):
    await cmd_fast_list(msg)