FROM alpine:3.17.0

LABEL org.opencontainers.image.source https://github.com/bitprocessor/atlassian-cloud-backup

COPY backup.py /opt/backup.py
COPY requirements.txt /opt/requirements.txt

RUN apk update && apk upgrade && \
    apk add --update --no-cache git py3-pip && \
    rm -rf /var/cache/apk/* && \
    pip3 install --upgrade pip && \
    pip3 install -r /opt/requirements.txt

WORKDIR /opt

ENTRYPOINT /usr/bin/python3 /opt/backup.py