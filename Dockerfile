# docker build -t eu.gcr.io/reddit-app-308612/api -f Dockerfile .
# docker run -t -p 80:80 --network host eu.gcr.io/reddit-app-308612/api
# docker push eu.gcr.io/reddit-app-308612/api
# gcloud run deploy --image eu.gcr.io/reddit-app-308612/api --port 80 --add-cloudsql-instances reddit-app-308612:us-central1:db-postgres --set-env-vars INSTANCE_UNIX_SOCKET="/cloudsql/reddit-app-308612:us-central1:db-postgres"

FROM python:3.11
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./ /code
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
