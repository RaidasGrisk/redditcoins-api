FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY ./app /app
RUN pip install -r requirements.txt

# making this background py script run was way too hard
# lets not run this as a background tas or as cron
# simply add it to prestart.sh
RUN echo "python3 /app/make_web_data.py &" >> prestart.sh