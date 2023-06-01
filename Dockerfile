# docker build -t eu.gcr.io/reddit-app/api -f Dockerfile .
# docker run -t -p 80:80 --network host eu.gcr.io/reddit-app/api
# docker push eu.gcr.io/reddit-app/api
# gcloud run deploy --image eu.gcr.io/reddit-app/api --port 80

FROM python:3.11
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./ /code
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
