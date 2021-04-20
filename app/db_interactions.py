'''
TODO:
1. Work on indexing the db
2. Work on limiting the query results
3. Think of better db structure to lower compute cost

'''

import pandas as pd
import time
import asyncio
from typing import Union
import databases

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


async def get_mention_timeseries(
        subreddit: str,
        ticker: Union[str, None],
        start: str,
        end: str,
        ups: int,
        submissions: bool,
        comments: bool,
        granularity: str,
        database: databases.core.Database,
) -> pd.Series:

    # IMPORTANT!
    # There are two possible queries.
    # One fetching number of submissions /
    # comments with specific ticker topic.
    # One fetching total number of submissions /
    # comments irrespective of topic. So two queries.

    # two rows are not very intuitive:
    # (1) AND created_time <= 2021-04-01 + INTERVAL '1 days'
    # (2) OFFSET 1 ROWS
    # if (1) is not done, than the value of 2021-04-01 is null
    # if (2) is not done then 2021-04-02 with value of null is returned
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
            AND created_time <= TIMESTAMP '{end}' + INTERVAL '{gran_[granularity]}'
            GROUP BY tb
            ORDER BY tb DESC
            OFFSET 1 ROWS
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
            AND to_timestamp(created_utc) <= TIMESTAMP '{end}' + INTERVAL '{gran_[granularity]}'
            GROUP BY tb
            ORDER BY tb DESC
            """

    # fetch data
    data = await database.fetch_all(sql)

    # if db returned nothing return empty Series
    # this might happen if for example bad query
    # params, say start >= end time. Without this
    # the script below fails to set_index etc.
    if len(data) == 0:
        return pd.Series([])

    # the db returns an object that looks like this:
    # [{'tb': datetime.datetime(2021, 4, 1, 0, 0), 'count': 5}, ...]
    # no way to convert it to Series instead of DataFrame!?
    # So have to do squeeze() DF into Series
    df = pd.DataFrame(data)
    df = df.set_index('tb')
    df = df.squeeze()

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
    # this seems pointless at this point
    # but is important when converting Series
    # to dictionary and finally json object
    df.index = df.index.rename('time')
    df.name = 'volume'

    return df


def test() -> None:

    from database import database

    async def fetch_data():

        await database.connect()
        df = await get_mention_timeseries(
            subreddit='satoshistreetbets',
            ticker='ETH',
            start='2021-01-28',
            end='2021-04-02',
            ups=0,
            submissions=True,
            comments=True,
            granularity='D',
            database=database
        )
        await database.disconnect()
        return df

    df = asyncio.run(fetch_data())

    [print(i) for i in df.reset_index().to_dict(orient='records')]
