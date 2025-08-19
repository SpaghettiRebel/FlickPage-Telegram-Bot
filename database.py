# database.py
import aiosqlite

DB_NAME = 'db1.db'


async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS watchlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                movie_data TEXT NOT NULL
            )
        ''')
        await db.commit()


async def add_movie_to_watchlist(user_id: int, movie_id: int, movie_data: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO watchlists (user_id, movie_id, movie_data) VALUES (?, ?, ?)",
            (user_id, movie_id, str(movie_data))
        )
        await db.commit()


async def check_movie(user_id: int, movie_id: int) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM watchlists WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id)
        )
        (count,) = await cursor.fetchone()
        await cursor.close()
        return count > 0


async def get_user_watchlist(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT movie_id, movie_data FROM watchlists WHERE user_id = ?",
            (user_id,)
        )
        return await cursor.fetchall()


async def remove_movie_from_watchlist(user_id: int, movie_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM watchlists WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id)
        )
        await db.commit()
