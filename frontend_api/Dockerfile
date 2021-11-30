FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --upgrade -r /code/requirements.txt

COPY . /code/app

EXPOSE 8000

CMD ["uvicorn", "app.frontendApp:app", "--host", "0.0.0.0", "--port", "80"]

