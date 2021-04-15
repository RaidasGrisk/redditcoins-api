'''
https://pydantic-docs.helpmanual.io/usage/schema/#schema-customization
'''

from fastapi import FastAPI, Query, Path
from pydantic import BaseModel
from typing import List, Optional
from database import database

from db_interactions import get_mention_timeseries, gran_

# ok we need to parse ticker names and validate
# that provided ticker is indeed valid and exists in db
# TODO: this is too long and rendered docs are fucked
valid_tickers = '|'.join(['TSLA', 'GOOGL'] + ['None'])

# list of tickers of corresponding subreddit
subreddits_and_tickers = {
    'wallstreetbets': ['TSLA', 'GOOGL', 'GME'] + ['NONE'],
    'satoshistreetbets': ['ETH', 'ADA', 'BTC'] + ['NONE']
}
tickers = [
    ticker for subreddit in subreddits_and_tickers.values() for ticker in subreddit
]

# valid subreddits
subreddits = ['wallstreetbets', 'satoshistreetbets']
valid_subreddits = '|'.join(subreddits)

tags_metadata = [
    {
        "name": "info",
        "description": "Get all subreddits and corresponding tickers",
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
    title='Reddit ticker',
    description='Get ticker mention counts / sentiment from reddit subs',
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


@app.get('/subs_and_tickers', tags=['info'])
def get_subs_and_tickers():
    return {
        'info': 'keys are subreddits, values are valid tickers',
        'data': subreddits_and_tickers
    }


# the output data model example and validator
class DataModelOut(BaseModel):
    data: List[dict] = [
        {'time': '2021-01-01', 'volume': 1},
        {'time': '2021-01-02', 'volume': 2}
    ]


@app.get('/volume/{subreddit}/{ticker}', response_model=DataModelOut, tags=['volume'])
async def vol(
        ticker: str = Path(
            ...,
            title='ticker',
            description='Name of the ticker, e.g ETH, TSLA. '
                        '<a href=./subs_and_tickers target="_blank">Check this for more</a>.<br><br>'
                        'There is a special case: when ticker is set to NONE <br>'
                        'total number of submissions / comments is returned <br>'
                        'irrespective of ticker mentions. Useful for data scaling.',
            # regex=f'{"|".join(tickers)}',
            include_in_schema=False
        ),
        subreddit: str = Path(
            'wallstreetbets',
            description='The subreddit to fetch data from',
            regex=f'{"|".join(subreddits_and_tickers.keys())}'
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
        ticker=None if ticker == 'NONE' else ticker,
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


@app.get('/sentiment/{subreddit}/{ticker}', tags=['sentiment'])
async def sentiment():
    pass