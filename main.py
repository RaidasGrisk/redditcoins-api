from fastapi import FastAPI, Query, Path, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import List
import json
import datetime
from database import database

tags_metadata = [
    {
        'name': 'info',
        'description': 'Ping / get all available coins',
    },
    {
        'name': 'volume',
        'description': 'Get mention volume',
    },
    {
        'name': 'sentiment',
        'description': 'Upcoming'
    }
]


# limit timespan to prevent huge db load
def validate_time(start, end):
    time_format = '%Y-%m-%d %H:%M:%S'
    start_ = datetime.datetime.strptime(start, time_format).replace(tzinfo=datetime.timezone.utc).timestamp()
    end_ = datetime.datetime.strptime(end, time_format).replace(tzinfo=datetime.timezone.utc).timestamp()
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    difference = end_ - start_
    if end_ > now:
        raise ValueError('Invalid end date. End date cannot be later than the current UTC time.')
    if start_ > end_:
        raise ValueError('Invalid dates.')
    if difference > (2592000 * 12):  # 12 months
        raise ValueError('Difference between start and end is too long. Max is 12 months.')


app = FastAPI(
    title='redditcoins.app',
    description='r/cryptocurrency coin mentions',
    openapi_tags=tags_metadata
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
async def startup():
    await database.connect()


@app.on_event('shutdown')
async def shutdown():
    await database.disconnect()


@app.get('/', tags=['info'])
def ping():
    return {'message': 'Hey there!'}


@app.get('/coins', tags=['info'])
async def get_coins():
    sql = f"""
    SELECT DISTINCT topic FROM cryptocurrency_
    """
    coins = await database.fetch_all(sql)
    coins_ = [coin['topic'] for coin in coins]
    return {'coins': coins_}


# the output data model example and validator
class DataModelOut(BaseModel):
    data: List[dict] = [
        {'time': '2023-01-01', 'volume': 1},
        {'time': '2023-01-02', 'volume': 2}
    ]


@app.get('/volume/{coin}', response_model=DataModelOut, tags=['volume'])
async def vol(
        coin: str = Path(
            ...,
            title='coin',
            description='Coin, e.g BTC, ETH, USDT. '
                        '<a href=./coins target="_blank">Check this for more</a>.<br><br> '
                        'There is a special case: when coin is set to NONE '
                        'total number of submissions / comments is returned '
                        'irrespective of coin mentions. Useful for data scaling.',
        ),
        start: str = Query(
            ...,
            description='e.g. 2023-01-01 00:00:00'
        ),
        end: str = Query(
            ...,
            description='e.g. 2023-02-01 00:00:00'
        ),
        granularity: str = Query(
            'day',
            description='Granularity of the data. E.g hour, day, week, month',
            regex=f'(hour|day|week|month)',
        )
) -> dict:

    try:
        validate_time(start=start, end=end)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=jsonable_encoder({'error': str(err)}))

    time_format = '%Y-%m-%d %H:%M:%S'
    start_ = int(datetime.datetime.strptime(start, time_format).replace(tzinfo=datetime.timezone.utc).timestamp())
    end_ = int(datetime.datetime.strptime(end, time_format).replace(tzinfo=datetime.timezone.utc).timestamp())

    query = f"""
        WITH data_ AS (
            SELECT * FROM cryptocurrency_
            WHERE
            created_utc < {end_} AND
            created_utc > {start_} AND
            {f"topic = '{coin}'" if coin else ''}
         )

        SELECT 
            DATE_TRUNC('{granularity}', TIMESTAMP 'epoch' + created_utc * INTERVAL '1 second') AS gran,
            COUNT(*) AS count
        FROM data_
        GROUP BY gran
        ORDER BY gran DESC
        """

    data = await database.fetch_all(query=query)
    data_ = []
    for row in data:
        date, count = row.values()
        date = date.strftime(time_format)
        data_.append({'time': date, 'volume': count})

    return {'data': data_}


# this endpoint is purely to decrease the load
# on db and have a ready to output summary for web
# for details see make_web_data.py
@app.get('/volume/market_summary', tags=['volume'], include_in_schema=False)
async def volume_market_summary(
        gran: str = Query(
            ...,
            title='granularity',
            regex=f'{"|".join(["daily", "hourly"])}'
        ),
):
    with open(f'web_data_{gran}.json') as json_file:
        data = json.load(json_file)
    return data


@app.get('/sentiment/{coin}', tags=['sentiment'])
async def sentiment():
    pass
