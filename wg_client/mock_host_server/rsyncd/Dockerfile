FROM alpine:latest

RUN apk add --no-cache rsync

COPY rsyncd.conf /etc/rsyncd.conf

EXPOSE 873

CMD ["rsync", "--daemon", "--no-detach", "--port=873", "--config=/etc/rsyncd.conf"]