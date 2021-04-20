from fastapi.testclient import TestClient
from main import app
import datetime
import json
import time


def make_web_data(client) -> None:

    # lets shift one hour back because
    # the data of the current hour is not yet complete
    shift = datetime.timedelta(hours=1)
    start = datetime.datetime.utcnow() - datetime.timedelta(hours=24) - shift
    end = datetime.datetime.utcnow() - shift

    params = {
        'start': start.strftime("%Y-%m-%d %H:%M:%S"),
        'end': end.strftime("%Y-%m-%d %H:%M:%S"),
        'ups': 0,
        'submissions': True,
        'comments': True,
        'granularity': 'H'
    }

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

    with open('web_summary.json', 'w') as fp:
        json.dump(output, fp)


if __name__ == '__main__':

    # init api client
    client = TestClient(app)

    # run on init
    try:
        make_web_data(client)
    except Exception as e:
        print(e)
        with open('web_summary.json', 'w') as fp:
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
