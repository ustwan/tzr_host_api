FROM alpine:latest
RUN apk add --no-cache rsync wget
WORKDIR /app
COPY app/ /app/
CMD ["sh", "/app/sync.sh"]
