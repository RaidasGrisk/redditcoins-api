from fastapi.testclient import TestClient
from main import app
import datetime
import json
import time


def make_web_data(client) -> None:

    # Lets make two files: web_data_hourly and web_data_daily
    # First will store hourly, second daily data.
    # TODO: refactor this into two separate functions
    #  put this in cron to run every hour / day instead of while loop

    # lets shift one hour back because
    # the data of the current hour is not yet complete
    shift = datetime.timedelta(hours=1)
    start = datetime.datetime.utcnow() - datetime.timedelta(hours=24) - shift
    end = datetime.datetime.utcnow() - shift

    params_hourly = {
        'start': start.strftime("%Y-%m-%d %H:%M:%S"),
        'end': end.strftime("%Y-%m-%d %H:%M:%S"),
        'ups': 0,
        'submissions': True,
        'comments': True,
        'granularity': 'H'
    }

    shift = datetime.timedelta(days=1)
    start = datetime.datetime.utcnow() - datetime.timedelta(days=24) - shift
    end = datetime.datetime.utcnow() - shift

    params_daily = {
        'start': start.strftime("%Y-%m-%d %H:%M:%S"),
        'end': end.strftime("%Y-%m-%d %H:%M:%S"),
        'ups': 0,
        'submissions': True,
        'comments': True,
        'granularity': 'D'
    }

    files = ['web_data_hourly.json', 'web_data_daily.json']
    requests_params = [params_hourly, params_daily]

    for params, file in zip(requests_params, files):

        output = {}
        with client:
            subs_and_coins = client.get('/subs_and_coins').json()
            for subreddit in subs_and_coins['subreddits']:
                output[subreddit] = {}
                for coin in subs_and_coins['coins']:
                    output[subreddit][coin] = {}
                    resp = client.get(
                        f'/volume/{subreddit}/{coin}',
                        params=params
                    ).json()
                    output[subreddit][coin] = resp

        with open(file, 'w') as fp:
            json.dump(output, fp)


if __name__ == '__main__':

    # init api client
    client = TestClient(app)

    # run on init
    try:
        make_web_data(client)
    except Exception as e:
        print(e)
        for file in ['web_data_hourly.json', 'web_data_daily.json']:
            with open(file, 'w') as fp:
                json.dump({'info': 'data not ready'}, fp)

    # TODO: while loop is a waste of compute power
    #  must move this to cron inside the docker
    # every start of an hour
    # run the function
    # if not start of an hour
    # sleep for 59 secs
    while True:
        t = time.strftime('%M')
        if int(t) == 0:
            make_web_data(client)
            print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        time.sleep(59)
