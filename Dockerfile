FROM python:3.7
LABEL maintainer="Ocean Protocol <devops@oceanprotocol.com>"

RUN pip install kopf
RUN pip install kubernetes
RUN apt update && apt install -y vim gcc libpq-dev && apt-get clean
RUN pip install psycopg2  
COPY operator_engine /operator_engine
WORKDIR /operator_engine
CMD kopf run --standalone /operator_engine/operator_main.py
#CMD tail -f /dev/null
