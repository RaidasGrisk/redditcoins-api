import databases
from private import db_details
import asyncio

# init db object
DATABASE_URL = f"postgresql://{db_details['user']}:{db_details['password']}@{db_details['host']}/reddit"
database = databases.Database(DATABASE_URL)


# test
def test():
    async def fetch():
        await database.connect()
        print(await database.fetch_all(
            "SELECT * FROM satoshistreetbets_ LIMIT 1"
        ))
        await database.disconnect()

    print(asyncio.run(fetch()))

