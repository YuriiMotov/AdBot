FROM python:3.10-bookworm

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

CMD [ "python", "./src/adbot/main.py" ]