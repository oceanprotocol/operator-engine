FROM python:3.7
LABEL maintainer="Ocean Protocol <devops@oceanprotocol.com>"

RUN pip install kopf
RUN pip install kubernetes
RUN apt update && apt install -y vim && apt-get clean
COPY operator /operator
WORKDIR /operator
CMD kopf run --standalone /operator/operator_main.py
