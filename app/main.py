'''
https://pydantic-docs.helpmanual.io/usage/schema/#schema-customization
'''

from fastapi import FastAPI, Query, Path
from pydantic import BaseModel
from typing import List, Optional
from database import database
from db_interactions import get_mention_timeseries, gran_

coins = [
    'ALGO', 'DASH', 'OXT', 'ATOM', 'KNC', 'XRP', 'REP',
    'MKR', 'CGLD', 'COMP', 'NMR', 'OMG', 'BAND', 'UMA',
    'XLM', 'EOS', 'ZRX', 'BAT', 'LOOM', 'UNI', 'YFI',
    'LRC', 'CVC', 'DNT', 'MANA', 'GNT', 'REN', 'LINK',
    'BTC', 'BAL', 'LTC', 'ETH', 'BCH', 'ETC', 'USDC', 'ZEC',
    'XTZ', 'DAI', 'WBTC', 'NU', 'FIL', 'AAVE', 'SNX', 'BNT',
    'GRT', 'SUSHI', 'MATIC', 'ADA', 'ANKR', 'CRV', 'STORJ',
    'SKL', '1INCH', 'ENJ', 'NKN', 'OGN'
]

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


app = FastAPI(
    title='Reddit coins',
    description='Get coin mention counts / sentiment from reddit subs',
    version='0.0.1',
    openapi_tags=tags_metadata
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


@app.get('/sentiment/{subreddit}/{coin}', tags=['sentiment'])
async def sentiment():
    pass