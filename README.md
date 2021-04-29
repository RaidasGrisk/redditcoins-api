# Run
````
# make sure to run this from app dir
uvicorn main:app --host 0.0.0.0 --port 8080
````

# Build and deploy API

Build and run FastAPI server in docker container
```
appName='reddit-coin-api'
docker build --tag $appName -f Dockerfile .
docker run --network="host" -d -p 80:8080 -e PORT="8080" $appName
```

# DB connection

Credentials are stored inside ```./app/private.py``` (make this file before running anything).

```
db_details = {
    'host': '0.0.0.0',
    'port': 5432,
    'user': 'admin',
    'password': 'temp-pass',
}
```

*The app is dependent on the following db (repo)  
```https://github.com/RaidasGrisk/reddit-to-db```
