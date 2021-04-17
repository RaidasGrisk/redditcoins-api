import databases
from private import db_details
import asyncio

# init db object
DATABASE_URL = f"postgresql://{db_details['user']}:{db_details['password']}@{db_details['host']}/reddit"

# update min / max size to deal with many fastapi/gunicorn workers.
# (likely not true, because with 1 CPU it will spawn 1 worker).
# else, asyncpg.exceptions.TooManyConnectionsError: sorry, too many clients already
# leave connection space for: pgadmin / make_web_data.py processes
database = databases.Database(DATABASE_URL, min_size=2, max_size=5)


# test
def test():
    async def fetch():
        await database.connect()
        print(await database.fetch_all(
            "SELECT * FROM satoshistreetbets_ LIMIT 1"
        ))
        await database.disconnect()

    print(asyncio.run(fetch()))

