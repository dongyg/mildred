FROM python:3.8-slim-buster

RUN pip install --no-cache-dir web.py==0.51 pyyaml==5.3.1 rsa==4.0 image==1.5.32 qrcode==6.1 docker==4.2.0 docker-compose==1.26.0;
ENV RUNNING_INSIDE_CONTAINER 1
WORKDIR /mildred/code
