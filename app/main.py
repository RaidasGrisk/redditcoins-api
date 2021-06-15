'''
https://pydantic-docs.helpmanual.io/usage/schema/#schema-customization
'''

from fastapi import FastAPI, Query, Path, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, validator, ValidationError
from typing import List, Optional
from database import database
from db_interactions import get_mention_timeseries, gran_
import json
import datetime
import pandas as pd

coins = [
    'ALGO', 'DASH', 'OXT', 'ATOM', 'KNC', 'XRP', 'REP', 'MKR', 'CGLD',
    'COMP', 'NMR', 'OMG', 'BAND', 'UMA', 'XLM', 'EOS', 'ZRX', 'BAT',
    'LOOM', 'UNI', 'YFI', 'LRC', 'CVC', 'DNT', 'MANA', 'GNT', 'REN',
    'LINK', 'BTC', 'BAL', 'LTC', 'ETH', 'BCH', 'ETC', 'USDC', 'ZEC',
    'XTZ', 'DAI', 'WBTC', 'NU', 'FIL', 'AAVE', 'SNX', 'BNT', 'GRT',
    'SUSHI', 'MATIC', 'ADA', 'ANKR', 'CRV', 'STORJ', 'SKL', '1INCH',
    'ENJ', 'NKN', 'OGN', 'DOGE', 'DOT', 'NEO', 'CEL', 'NANO', 'IOTA',
    'XMR', 'USDT', 'BNB', 'NEM', 'TRON', 'BTG', 'VET', 'SHIB', 'ICP',
    'MIR', 'RLC', 'FORTH', 'TRB', 'CTSI', 'LTO', 'SOL', 'MOON',
    'THETA', 'KSM', 'CAKE', 'KLAY',
]  # 'MLN', 'AMP', 'GTC' are in the topics and db, but not here

db_metadata = {
    'subreddits': ['cryptocurrency', 'satoshistreetbets'],
    'coins': coins
}

tags_metadata = [
    {
        "name": "info",
        "description": "Get all subreddits and corresponding coins",
    },
    {
        "name": "volume",
        "description": "Get mention volume",
    },
    {
        'name': 'sentiment',
        'description': 'Upcoming'
    }
]


# add validators to validate time inputs
# and prevent using too distant dates
# both back in time and further in time :D
# this is to prevent unnecessary load in db.
class EndTimeValidator(BaseModel):
    end: str

    @validator('end')
    def validate_end_time(cls, end):
        # using pandas to infer date string format
        # other libs require me to specify this
        # not sure of the format the user will give
        if pd.to_datetime(end) > datetime.datetime.utcnow():
            raise ValueError('Invalid end date. '
                             'End date can not be later than current UTC time.')
        return end


class StartTimeValidator(BaseModel):
    start: str

    @validator('start')
    def validate_end_time(cls, start):
        if pd.to_datetime(start) < pd.to_datetime('2021-01-01'):
            raise ValueError('Invalid start date. '
                             'Try a date >= 2021-01-01')
        return start


app = FastAPI(
    # tricky part here with root_path.
    # more info here:
    # https://fastapi.tiangolo.com/advanced/behind-a-proxy/
    # the thing is, we need this api to be https.
    # so nginx server will proxy_pass redditcoins.app/api
    # to this fastapi service. But unforch, the /docs
    # will look for openapi.json in root instead of
    # /api/openapi.json this causes confusion and errors.
    # hence the root_path /api. With this the docs
    # are accessible only through the proxy, but not
    # directly, say 0.0.0.0/docs. Crap this is complicated.
    root_path='/api',
    title='Reddit coins',
    description='Get coin mention counts / sentiment from reddit subs',
    version='0.0.1',
    openapi_tags=tags_metadata
)

# this to let comunicate with
# vuejs dev server from localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get('/', tags=['info'])
def ping():
    return {'message': 'Hey there!'}


@app.get('/subs_and_coins', tags=['info'])
def get_subs_and_coins():
    return db_metadata


# the output data model example and validator
class DataModelOut(BaseModel):
    data: List[dict] = [
        {'time': '2021-01-01', 'volume': 1},
        {'time': '2021-01-02', 'volume': 2}
    ]


@app.get('/volume/{subreddit}/{coin}', response_model=DataModelOut, tags=['volume'])
async def vol(
        coin: str = Path(
            ...,
            title='coin',
            description='Coin, e.g ETH, SUSHI, BTC. '
                        '<a href=./subs_and_coins target="_blank">Check this for more</a>.<br><br>'
                        'There is a special case: when coin is set to NONE <br>'
                        'total number of submissions / comments is returned <br>'
                        'irrespective of coin mentions. Useful for data scaling.',
            # regex=f'{"|".join(coins)}',
            include_in_schema=False
        ),
        subreddit: str = Path(
            'satoshistreetbets',
            description='The subreddit to fetch data from',
            regex=f'{"|".join(db_metadata["subreddits"])}'
        ),
        start: str = Query(
            ...,
            description='The start of the time range to fetch data for, e.g. 2021-01-01'
        ),
        end: str = Query(
            ...,
            description='The end of the time range to fetch data for, e.g. 2021-02-01'
        ),
        ups: Optional[int] = Query(
            0,
            description='Include subs/comments with more than specified number of ups'
        ),
        submissions: bool = Query(
            True,
            description='Include submissions'
        ),
        comments: bool = Query(
            True,
            description='Include comments'
        ),
        granularity: str = Query(
            'D',
            description='Granularity of the data fetched',
            regex=f'({"|".join(gran_.keys())})',
        )
) -> dict:

    # TODO: add a limit to date range so that
    #  no mare than X data-points are queried
    #  to limit the load on db.
    #  for example if:
    #  start=2021-04-01 end=2021-04-10 granularity=H
    #  then data-points = 10 * 24 = 240
    #  so limit this to say 200 by shifting end
    #  to earlier date / shifting start to later

    try:
        StartTimeValidator(start=start, end=end)
        EndTimeValidator(start=start, end=end)
    except ValidationError as err:
        raise HTTPException(status_code=422, detail=jsonable_encoder(err.errors()))

    df = await get_mention_timeseries(
        # okay, why do we need this NONE thing?
        # the thing is, we want to be able to get the
        # volume of all the tickers combined together.
        # This let us scale the data: NVDA_vol / NONE_vol.
        # Now we can know that NVDA subs account for X%
        # of total subs during a period. This info is way
        # more valuable in ML models than raw counts NVDA_vol.
        ticker=None if coin == 'NONE' else coin,
        subreddit=subreddit,
        start=start,
        end=end,
        ups=ups,
        submissions=submissions,
        comments=comments,
        granularity=granularity,
        database=database
    )

    return {
        'data': df.reset_index().to_dict(orient='records')
    }


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


@app.get('/sentiment/{subreddit}/{coin}', tags=['sentiment'], include_in_schema=False)
async def sentiment():
    pass
