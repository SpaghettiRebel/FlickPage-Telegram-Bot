import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, types

from config import bot_token
from handlers import common, movie
from database import create_table


bot = Bot(token=bot_token)
dp = Dispatcher()


async def main():
    logging.basicConfig(level=logging.INFO)
    dp.include_routers(common.router, movie.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await create_table()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
