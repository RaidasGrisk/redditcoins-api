# Run
````
# make sure to run this from app dir
uvicorn main:app --host 0.0.0.0 --port 80
````

# Build and deploy API

Build and run FastAPI server in docker container
```
appName='reddit-ticker-api'
docker build --tag $appName -f Dockerfile .
docker run -d -p 80:80 $appName
```


# MongoDB* connection 

Credentials are stored inside ```./private.py``` (make this file before running anything).

```
mongo_details = {
    'host': '0.0.0.0',
    'port': 27017,
    'username': 'admin',
    'password': 'pass',
}
```

*The app is dependent on the following db (repo)  
```https://github.com/RaidasGrisk/reddit-to-db```

