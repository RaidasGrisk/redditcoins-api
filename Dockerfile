FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY ./app /app
RUN pip install -r requirements.txt
RUN python3 make_web_data.py &

# --- manual deployment ---
#FROM python:3.8-slim
#
#COPY ./app /app
#RUN pip install -r app/requirements.txt
#
#EXPOSE 80
#CMD uvicorn app.main:app --host 0.0.0.0 --port 80