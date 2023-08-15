FROM python:3.8-slim-buster
LABEL maintainer="Ocean Protocol <devops@oceanprotocol.com>"

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        apt-utils \
        build-essential \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install kopf \
       kubernetes \
       web3 \
       psycopg2 \
       eth_account \
       coloredlogs

COPY operator_engine /operator_engine
WORKDIR /operator_engine
ENV OPERATOR_PRIVATE_KEY='0x95c716e9df3bc4ffd7299e7861ce401de810e8d245d3127b8e7b430f4ca7fd27'
#CMD kopf run --standalone /operator_engine/operator_main.py
CMD python3.8 /operator_engine/operator_main.py
#CMD tail -f /dev/null
