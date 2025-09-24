#!/usr/bin/env bash
set -euo pipefail
cmd=${1:-}
case "$cmd" in
  up)
    shift
    docker compose -f compose.base.yml -f compose.apis.yml "$@" up -d
    ;;
  up-testdb)
    shift
    docker compose -f compose.base.yml -f compose.apis.yml -f compose.db.test.yml --profile testdb "$@" up -d
    ;;
  down)
    docker compose -f compose.base.yml -f compose.apis.yml down
    ;;
  down-all)
    docker compose -f compose.base.yml -f compose.apis.yml -f compose.db.test.yml down -v
    ;;
  restart-api1)
    docker compose -f compose.apis.yml restart api_1
    ;;
  restart-api2)
    docker compose -f compose.apis.yml restart api_2
    ;;
  restart-api3)
    docker compose -f compose.apis.yml restart api_3
    ;;
  logs)
    docker compose -f compose.base.yml -f compose.apis.yml logs -f
    ;;
  migrate-prod)
    docker run --rm --network ${PROJECT_NAME}_apinet \
      -v "$PWD/db/migrations:/flyway/sql:ro" flyway/flyway:10 \
      -url="jdbc:mysql://${DB_PROD_HOST}:${DB_PROD_PORT}/${DB_PROD_NAME}" \
      -user="${DB_PROD_USER}" -password="${DB_PROD_PASSWORD}" migrate
    ;;
  *)
    echo "usage: $0 {up|up-testdb|down|down-all|restart-api1|restart-api2|restart-api3|logs|migrate-prod}"
    exit 1
esac
