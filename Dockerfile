FROM python:3.8.3-buster

ENV path="scripts:${PATH}"

COPY ./requirements.txt /requirements.txt
#RUN apk add  --update --no-cache --virtual .tmp gcc libc-dev linux-headers
RUN python -m pip install --upgrade pip
RUN pip install -r /requirements.txt

RUN mkdir /invoices
COPY ./invoices /invoices
COPY ./api /api
COPY ./helpers /helpers
WORKDIR /invoices
COPY ./manage.py /manage.py
COPY ./worker.py /worker.py
COPY ./scripts /scripts


RUN chmod +x /scripts/*

RUN mkdir -p /vol/web/media
RUN mkdir -p /vol/web/static

RUN adduser user
RUN chown -R user:user /vol
RUN chmod -R 755 /vol/web
USER user

CMD ["entrypoint.sh"]