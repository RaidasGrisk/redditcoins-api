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

Deploy on google cloud run
```
appName='reddit-ticker-api'
projectName='reddit-app-308612'
docker build --tag gcr.io/$projectName/$appName -f Dockerfile .
docker push gcr.io/$projectName/$appName
gcloud config set project $projectName
gcloud run deploy --image gcr.io/$projectName/$appName --platform managed --region europe-north1 --max-instances 2
```


# MongoDB* connection 

Credentials are stored inside ```./app/private.py``` (make this file before running anything).

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

