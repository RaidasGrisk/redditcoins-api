'''
TODO:
1. Work on indexing the db
2. Work on limiting the query results
3. Think of better db structure to lower compute cost

'''

from private import db_details
import asyncpg
import pandas as pd
import time
import asyncio
from typing import Union

# define granularity mapping from
# FastAPI input to timescaledb
# define this in outer scope so
# can import into other modules
gran_ = {
    # 'M': '1 minutes',
    # 'M5': '5 minutes',
    # 'M15': '15 minutes',
    # 'M30': '30 minutes',
    'H': '1 hours',
    '2H': '2 hours',
    '6H': '6 hours',
    '12H': '12 hours',
    'D': '1 days',
    'W': '1 week'
}


def date_string_to_timestamp(s: str) -> int:
    # using pandas instead of datetime to be able to infer str format
    tuple = pd.to_datetime(s, infer_datetime_format=True).timetuple()
    return int(time.mktime(tuple))


async def get_timeseries_df(
        subreddit: str,
        ticker: Union[str, None],
        start: str,
        end: str,
        ups: int,
        submissions: bool,
        comments: bool,
        granularity: str
) -> pd.Series:

    # IMPORTANT!
    # There are two possible queries.
    # One fetching number of submissions /
    # comments with specific ticker topic.
    # One fetching total number of submissions /
    # comments irrespective of topic. So two queries.
    if ticker:
        sql = f"""
            SELECT 
                time_bucket_gapfill('{gran_[granularity]}', created_time) AS tb, 
                COUNT(*)
            FROM {subreddit + '_'}
            WHERE UPS > {ups}
            AND topic = '{ticker}'
            {
                '' if comments and submissions else 
                'AND is_comment = true' if comments else 
                'AND is_comment = false' if submissions else ''
            }
            AND created_time >= '{start}'
            AND created_time < '{end}'
            GROUP BY tb
            ORDER BY tb DESC
            """
    else:
        # this is massively overcomplicated :/
        # but with current db structure, cant think
        # of a better approach. Pretty sure there is none.
        sql = f"""
            SELECT 
                time_bucket_gapfill(
                '{gran_[granularity]}', 
                to_timestamp(created_utc),
                '{start}',
                '{end}'
                ) AS tb, 
                COUNT(*)
            FROM {subreddit}
            WHERE UPS > {ups}
            {
                '' if comments and submissions else 
                'AND num_comments IS NULL' if comments else 
                'AND num_comments IS NOT NULL' if submissions else ''
            }
            AND to_timestamp(created_utc) >= '{start}'
            AND to_timestamp(created_utc) < '{end}'
            GROUP BY tb
            ORDER BY tb DESC
            """

    # fetch data
    # TODO: as per docs, it is recommended to use
    #  connection pool. Current implementation does
    #  not follow that pattern. Hence small time penalty.
    #  https://magicstack.github.io/asyncpg/current/usage.html#connection-pools
    #  to implement this, the db connection object
    #  has to be created together with fastapi app.
    #  The connection object should then be passed
    #  to this function to do the rest.
    conn = await asyncpg.connect(**db_details, database='reddit')
    async with conn.transaction():
        data = await conn.fetch(sql)
        df = pd.Series(dict(data))

        # modify index attributes
        # by default index values are datetime64[ns]
        # upon conversion to json (pd.to_json)
        # these values are converted to timestamps: int
        # to prevent this, lets cast these values to str
        df.index = df.index.astype(str)

        # for some reason the count values are floats
        # we want it to be ints, also how about null
        # values? Filling it with 0's seems reasonable.
        df = df.fillna(0).astype(int)

        # rename both index and series values
        df.index = df.index.rename('time')
        df.name = 'volume'

    await conn.close()

    return df


def test() -> None:

    df = asyncio.run(get_timeseries_df(
        subreddit='satoshistreetbets',
        ticker='ETH',
        start='2021-01-28',
        end='2021-04-02',
        ups=0,
        submissions=True,
        comments=True,
        granularity='D'
    ))

    [print(i) for i in df.reset_index().to_dict(orient='records')]
