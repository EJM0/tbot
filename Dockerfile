FROM python:3.11.4-slim

RUN pip install --upgrade pip==23.3.2

RUN apt-get update && apt-get install -y libpq-dev build-essential ffmpeg

RUN apt-get install streamlink -y

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]