FROM python:3.12-slim

RUN apt-get update && apt-get install -y libpq-dev build-essential

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]