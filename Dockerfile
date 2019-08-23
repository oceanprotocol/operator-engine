FROM python:3.7
LABEL maintainer="Ocean Protocol <devops@oceanprotocol.com>"

RUN pip install kopf
RUN pip install kubernetes
COPY operator /operator
WORKDIR /operator
CMD kopf run --standalone /operator/operator_main.py
