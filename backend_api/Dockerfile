FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --upgrade -r /code/requirements.txt

COPY . /code/app

EXPOSE 5001

CMD ["python3", "app/backendApp.py"]