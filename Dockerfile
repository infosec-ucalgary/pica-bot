FROM alpine

RUN apk add --update python3 py3-pip sqlite &&\
    adduser -h /home/app app --disabled-password &&\
    mkdir -p /home/app

COPY bot.py /home/app/
COPY requirements.txt /home/app/
COPY .env /home/app/

RUN chown -R app:app /home/app/ /home/app/* &&\
    pip3 install -r /home/app/requirements.txt

WORKDIR /home/app/
USER app

CMD ["python3", "/home/app/bot.py"]
