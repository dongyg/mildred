FROM python:alpine

RUN apk add --update curl bash && rm -rf /var/cache/apk/*

RUN cd /tmp/ && \
        wget --no-check-certificate -q -O /etc/apk/keys/sgerrand.rsa.pub https://alpine-pkgs.sgerrand.com/sgerrand.rsa.pub && \
        wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.31-r0/glibc-2.31-r0.apk && \
        wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.31-r0/glibc-bin-2.31-r0.apk && \
        wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.31-r0/glibc-i18n-2.31-r0.apk && \
        apk add glibc-2.31-r0.apk glibc-bin-2.31-r0.apk glibc-i18n-2.31-r0.apk && \
        /usr/glibc-compat/bin/localedef -i en_US -f UTF-8 en_US.UTF-8 && \
        rm -rf /tmp/* && \
        cd - && \
    curl -L "https://github.com/docker/compose/releases/download/1.26.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose && \
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

RUN pip install --no-cache-dir web.py==0.51 pyyaml==5.3.1 rsa==4.0 docker==4.2.0;

# RUN pip install --no-cache-dir web.py==0.51 pyyaml==5.3.1 rsa==4.0 docker==4.2.0 docker-compose==1.26.0;
ENV RUNNING_INSIDE_CONTAINER 1
# COPY code /mildred/code/
WORKDIR /mildred/code

