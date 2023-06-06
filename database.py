import databases
from private import db_details
import asyncio
import os

# init db object
DATABASE_URL = f"postgresql://{db_details['user']}:{db_details['password']}@{db_details['host']}/reddit"

# This part is specifically for Google cloud RUN deployment.
# https://cloud.google.com/sql/docs/mysql/connect-instance-cloud-run#gcloud_6
# https://blog.devgenius.io/deploy-a-flask-app-with-docker-google-cloud-run-and-cloud-sql-for-postgresql-6dc9e7f4c434
if 'INSTANCE_UNIX_SOCKET' in os.environ:
    unix_socket_path = os.environ['INSTANCE_UNIX_SOCKET']  # e.g. '/cloudsql/project:region:instance'
    DATABASE_URL = f"postgresql+pg8000://{db_details['user']}:{db_details['password']}@/reddit" \
                   f"?unix_sock={unix_socket_path}/.s.PGSQL.5432"

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
            "SELECT * FROM cryptocurrency_ LIMIT 1"
        ))
        await database.disconnect()

    print(asyncio.run(fetch()))
