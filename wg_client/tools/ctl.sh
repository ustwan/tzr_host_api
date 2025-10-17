#!/usr/bin/env bash
set -euo pipefail

# ========== Pretty TTY helpers ==========
if [[ -t 1 ]]; then
  NC="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"; IT="\033[3m"; UL="\033[4m"
  RED="\033[31m"; GREEN="\033[32m"; YELLOW="\033[33m"; BLUE="\033[34m"; MAG="\033[35m"; CYAN="\033[36m"; GRAY="\033[90m"
else
  NC=""; BOLD=""; DIM=""; IT=""; UL=""; RED=""; GREEN=""; YELLOW=""; BLUE=""; MAG=""; CYAN=""; GRAY=""
fi

banner(){
  local title="$1"; shift || true
  echo -e "${GREEN}${BOLD}┌──────────────────────────────────────────────────────────┐${NC}"
  printf "${GREEN}${BOLD}│${NC} %-56s ${GREEN}${BOLD}│${NC}\n" "${title}"
  echo -e "${GREEN}${BOLD}└──────────────────────────────────────────────────────────┘${NC}"
}

spinner(){
  local pid=$1; shift || true
  local msg="$*"; local frames=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)
  local i=0
  while kill -0 "$pid" 2>/dev/null; do
    printf "\r${CYAN}%s${NC} %s" "${frames[$((i%10))]}" "$msg"
    i=$((i+1)); sleep 0.1
  done
  printf "\r${GREEN}✔${NC} %s\n" "$msg"
}

ok(){ echo -e "${GREEN}✔${NC} $*"; }
warn(){ echo -e "${YELLOW}➜${NC} $*"; }
err(){ echo -e "${RED}✖${NC} $*" >&2; }

# ========== Project & Compose files ==========
PROJECT_PREFIX="host-api-service"
export COMPOSE_PROJECT_NAME="${PROJECT_PREFIX}"
export PROJECT_NAME="${PROJECT_PREFIX}"

INFRASTRUCTURE="HOST_API_SERVICE_INFRASTRUCTURE.yml"
FATHER_API="HOST_API_SERVICE_FATHER_API.yml"
LIGHTWEIGHT_API="HOST_API_SERVICE_LIGHT_WEIGHT_API.yml"
HEAVYWEIGHT_API="HOST_API_SERVICE_HEAVY_WEIGHT_API.yml"
WORKERS="HOST_API_SERVICE_WORKERS.yml"
XML_WORKERS="HOST_API_SERVICE_XML_WORKERS.yml"
DB_API="HOST_API_SERVICE_DB_API.yml"
MONITORING="HOST_API_SERVICE_MONITORING.yml"
DB_MONITORING="HOST_API_SERVICE_DB_MONITORING.yml"
UTILITIES="HOST_API_SERVICE_UTILITIES.yml"
SHOP_API="HOST_API_SERVICE_SHOP_API.yml"
SITE_AGENT="HOST_API_SERVICE_SITE_AGENT.yml"

DC(){ docker compose "$@"; }

need(){ command -v "$1" >/dev/null 2>&1 || { err "Не найдено: $1"; exit 1; }; }

usage(){
  cat <<USAGE
${BOLD}${CYAN}HOST_API_SERVICE ctl.sh${NC}

${BOLD}Режимы работы:${NC}
  ./tools/ctl.sh ${GREEN}start-test${NC}             — запустить тестовый режим (тестовая БД, ограниченные ресурсы)
  ./tools/ctl.sh ${GREEN}start-prod${NC}             — запустить продакшн режим (продакшн БД, полные ресурсы)
  ./tools/ctl.sh ${GREEN}start-all${NC}              — запустить все сервисы (по умолчанию)
  ./tools/ctl.sh ${GREEN}start-with-agent${NC}       — запустить всё + Site Agent для сайта

${BOLD}Управление:${NC}
  ./tools/ctl.sh ${GREEN}stop-all${NC}               — остановить всё (без удаления volume)
  ./tools/ctl.sh ${GREEN}down-all${NC}               — остановить и удалить с volume
  ./tools/ctl.sh ${GREEN}status${NC}                 — таблица статусов контейнеров
  ./tools/ctl.sh ${GREEN}logs [svc]${NC}             — логи (всех или конкретного сервиса)
  ./tools/ctl.sh ${GREEN}restart [svc]${NC}          — перезапуск сервиса
  ./tools/ctl.sh ${GREEN}migrate${NC}                — применить миграции БД

${BOLD}Диагностика:${NC}
  ./tools/ctl.sh ${GREEN}doctor${NC}                 — диагностика окружения
  ./tools/ctl.sh ${GREEN}networks${NC}               — показать/создать внешние сети
  ./tools/ctl.sh ${GREEN}prune${NC}                  — очистить dangling images, кеши и неиспользуемые сети

${BOLD}Site Agent (для сайта):${NC}
  ./tools/ctl.sh ${GREEN}site-agent${NC}             — запустить Site Agent
  ./tools/ctl.sh ${GREEN}site-agent-logs${NC}        — логи Site Agent
  ./tools/ctl.sh ${GREEN}site-agent-restart${NC}     — перезапустить Site Agent

${BOLD}Низкоуровневые:${NC}
  ./tools/ctl.sh ${GREEN}config${NC} | ${GREEN}ps${NC} | ${GREEN}images${NC} | ${GREEN}validate${NC}
  ./tools/ctl.sh ${GREEN}infrastructure${NC} | ${GREEN}father${NC} | ${GREEN}lightweight${NC} | ${GREEN}xml-workers${NC} | ${GREEN}heavyweight${NC} | ${GREEN}workers${NC} | ${GREEN}db${NC} | ${GREEN}monitoring${NC} | ${GREEN}site-agent${NC}
USAGE
}

ensure_networks(){
  banner "Сети проекта"
  
  # Основные сети проекта (с префиксом)
  for net in apinet backnet dbnet; do
    if ! docker network inspect "${PROJECT_PREFIX}_${net}" >/dev/null 2>&1; then
      warn "Создаю сеть ${PROJECT_PREFIX}_${net}"
      docker network create "${PROJECT_PREFIX}_${net}" >/dev/null &
      spinner $! "create network ${PROJECT_PREFIX}_${net}"
    else
      ok "${PROJECT_PREFIX}_${net} существует"
    fi
  done
  
  # Дополнительные сети (без префикса)
  for net in host-api-network monitoring; do
    if ! docker network inspect "${net}" >/dev/null 2>&1; then
      warn "Создаю сеть ${net}"
      docker network create "${net}" >/dev/null &
      spinner $! "create network ${net}"
    else
      ok "${net} существует"
    fi
  done
}

stack_up(){
  local title="$1"; shift; local files=("$@")
  banner "Запуск: ${title}"
  DC -f ${files[*]} up -d &
  spinner $! "docker compose up -d (${title})"
}

stack_down(){
  local title="$1"; shift; local files=("$@")
  banner "Остановка: ${title}"
  DC -f ${files[*]} down &
  spinner $! "docker compose down (${title})"
}

cmd=${1:-help}; shift || true

case "$cmd" in
  help|-h|--help)
    usage ;;

  start-test)
    banner "Запуск тестового режима"
    if [[ -f "env.test" ]]; then
      export $(cat env.test | grep -v '^#' | xargs)
      ok "Загружены переменные из env.test"
    else
      export DB_MODE=test
      export BATCH_SIZE=10
      export MAX_WORKERS=2
      warn "Используются переменные по умолчанию"
    fi
    need docker; ensure_networks
    stack_up "INFRASTRUCTURE" "$INFRASTRUCTURE"
    stack_up "DB"            "$DB_API"
    stack_up "FATHER"        "$FATHER_API"
    stack_up "LIGHTWEIGHT"   "$LIGHTWEIGHT_API"
    stack_up "XML WORKERS"   "$XML_WORKERS"
    stack_up "HEAVYWEIGHT"   "$HEAVYWEIGHT_API"
    stack_up "WORKERS"       "$WORKERS"
    stack_up "MONITORING"    "$MONITORING"
    ok "Тестовый режим запущен (DB_MODE=$DB_MODE, BATCH_SIZE=$BATCH_SIZE, MAX_WORKERS=$MAX_WORKERS)" ;;

  start-prod)
    banner "Запуск продакшн режима"
    if [[ -f "env.prod" ]]; then
      export $(cat env.prod | grep -v '^#' | xargs)
      ok "Загружены переменные из env.prod"
    else
      export DB_MODE=prod
      export BATCH_SIZE=100
      export MAX_WORKERS=8
      warn "Используются переменные по умолчанию"
    fi
    need docker; ensure_networks
    stack_up "INFRASTRUCTURE" "$INFRASTRUCTURE"
    stack_up "DB"            "$DB_API"
    stack_up "FATHER"        "$FATHER_API"
    stack_up "LIGHTWEIGHT"   "$LIGHTWEIGHT_API"
    stack_up "XML WORKERS"   "$XML_WORKERS"
    stack_up "HEAVYWEIGHT"   "$HEAVYWEIGHT_API"
    stack_up "WORKERS"       "$WORKERS"
    stack_up "MONITORING"    "$MONITORING"
    ok "Продакшн режим запущен (DB_MODE=$DB_MODE, BATCH_SIZE=$BATCH_SIZE, MAX_WORKERS=$MAX_WORKERS)" ;;

  start-all)
    banner "Запуск всех сервисов (по умолчанию)"
    export DB_MODE=test
    export BATCH_SIZE=50
    export MAX_WORKERS=4
    need docker; ensure_networks
    stack_up "INFRASTRUCTURE" "$INFRASTRUCTURE"
    stack_up "DB"            "$DB_API"
    stack_up "FATHER"        "$FATHER_API"
    stack_up "LIGHTWEIGHT"   "$LIGHTWEIGHT_API"
    stack_up "XML WORKERS"   "$XML_WORKERS"
    stack_up "HEAVYWEIGHT"   "$HEAVYWEIGHT_API"
    stack_up "WORKERS"       "$WORKERS"
    stack_up "MONITORING"    "$MONITORING"
    ok "Все сервисы запущены (включая XML Workers для параллельной загрузки логов)" ;;

  start-with-agent)
    banner "Запуск всех сервисов + Site Agent"
    export DB_MODE=test
    export BATCH_SIZE=50
    export MAX_WORKERS=4
    need docker; ensure_networks
    stack_up "INFRASTRUCTURE" "$INFRASTRUCTURE"
    stack_up "DB"            "$DB_API"
    stack_up "FATHER"        "$FATHER_API"
    stack_up "LIGHTWEIGHT"   "$LIGHTWEIGHT_API"
    stack_up "XML WORKERS"   "$XML_WORKERS"
    stack_up "HEAVYWEIGHT"   "$HEAVYWEIGHT_API"
    stack_up "WORKERS"       "$WORKERS"
    stack_up "MONITORING"    "$MONITORING"
    if [[ -f "$SITE_AGENT" ]]; then
      stack_up "SITE AGENT"  "$SITE_AGENT"
      ok "Все сервисы запущены (включая Site Agent для связи с сайтом)"
    else
      warn "Site Agent config не найден, пропущен"
      ok "Все сервисы запущены (без Site Agent)"
    fi ;;

  stop-all)
    # Добавляем SITE_AGENT в остановку (если есть)
    if [[ -f "$SITE_AGENT" ]]; then
      stack_down "ALL" "$INFRASTRUCTURE" "$FATHER_API" "$LIGHTWEIGHT_API" "$XML_WORKERS" "$HEAVYWEIGHT_API" "$WORKERS" "$DB_API" "$MONITORING" "$SITE_AGENT"
    else
      stack_down "ALL" "$INFRASTRUCTURE" "$FATHER_API" "$LIGHTWEIGHT_API" "$XML_WORKERS" "$HEAVYWEIGHT_API" "$WORKERS" "$DB_API" "$MONITORING"
    fi ;;
  down-all)
    banner "Полная остановка и очистка volume"
    # Добавляем SITE_AGENT в полную очистку (если есть)
    if [[ -f "$SITE_AGENT" ]]; then
      DC -f "$INFRASTRUCTURE" -f "$FATHER_API" -f "$LIGHTWEIGHT_API" -f "$XML_WORKERS" -f "$HEAVYWEIGHT_API" -f "$WORKERS" -f "$DB_API" -f "$MONITORING" -f "$UTILITIES" -f "$SITE_AGENT" down -v &
    else
      DC -f "$INFRASTRUCTURE" -f "$FATHER_API" -f "$LIGHTWEIGHT_API" -f "$XML_WORKERS" -f "$HEAVYWEIGHT_API" -f "$WORKERS" -f "$DB_API" -f "$MONITORING" -f "$UTILITIES" down -v &
    fi
    spinner $! "compose down -v" ;;

  migrate)
    banner "Применение миграций БД"
    if docker ps | grep -q host-api-service-api_4_db; then
      warn "Применяю миграции к тестовой БД..."
      docker exec host-api-service-api_4_db-1 psql -U api4_user -d api4_battles -f /docker-entrypoint-initdb.d/V1__create_tables_complete.sql || {
        warn "Копирую миграцию в контейнер..."
        docker cp /Users/ii/Documents/code/WG_HUB/wg_client/api_4/migrations/V1__create_tables_complete.sql host-api-service-api_4_db-1:/tmp/
        docker exec host-api-service-api_4_db-1 psql -U api4_user -d api4_battles -f /tmp/V1__create_tables_complete.sql
      }
      ok "Миграции применены успешно"
    else
      err "БД не запущена. Запустите сначала: ./tools/ctl.sh start-test или ./tools/ctl.sh start-prod"
    fi ;;

  status)
    banner "Статус контейнеров (${PROJECT_PREFIX})"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep host-api-service || true ;;

  logs)
    banner "Логи"
    ALL_FILES=("$INFRASTRUCTURE" "$FATHER_API" "$LIGHTWEIGHT_API" "$XML_WORKERS" "$HEAVYWEIGHT_API" "$WORKERS" "$MONITORING")
    [[ -f "$SITE_AGENT" ]] && ALL_FILES+=("$SITE_AGENT")
    if [[ $# -gt 0 ]]; then 
      DC "${ALL_FILES[@]/#/-f }" logs -f "$1"
    else 
      DC "${ALL_FILES[@]/#/-f }" logs -f
    fi ;;

  restart)
    if [[ $# -lt 1 ]]; then err "Нужно указать сервис"; exit 1; fi
    banner "Перезапуск: $1"
    DC -f "$INFRASTRUCTURE" -f "$FATHER_API" -f "$LIGHTWEIGHT_API" -f "$XML_WORKERS" -f "$HEAVYWEIGHT_API" -f "$WORKERS" -f "$DB_API" -f "$MONITORING" restart "$1" ;;

  doctor)
    banner "Диагностика"
    need docker
    ok "Docker: $(docker --version)"
    ok "Compose: $(docker compose version | head -1)"
    warn "Диски:"
    docker system df || true ;;

  networks)
    ensure_networks ;;

  prune)
    banner "Очистка Docker"
    docker system prune -af --volumes &
    spinner $! "docker system prune" ;;

  # Существующие команды ниже (сохранены)
  config)
    DC -f "$INFRASTRUCTURE" -f "$FATHER_API" -f "$LIGHTWEIGHT_API" -f "$XML_WORKERS" -f "$HEAVYWEIGHT_API" -f "$WORKERS" -f "$DB_API" config ;;
  ps)
    DC -f "$INFRASTRUCTURE" -f "$FATHER_API" -f "$LIGHTWEIGHT_API" -f "$XML_WORKERS" -f "$HEAVYWEIGHT_API" -f "$WORKERS" -f "$DB_API" ps ;;
  images)
    DC -f "$INFRASTRUCTURE" -f "$FATHER_API" -f "$LIGHTWEIGHT_API" -f "$XML_WORKERS" -f "$HEAVYWEIGHT_API" -f "$WORKERS" -f "$DB_API" images ;;
  validate)
    if DC -f "$INFRASTRUCTURE" -f "$FATHER_API" -f "$LIGHTWEIGHT_API" -f "$XML_WORKERS" -f "$HEAVYWEIGHT_API" -f "$WORKERS" -f "$DB_API" config >/dev/null; then ok "OK"; else err "INVALID"; fi ;;

  infrastructure)
    DC -f "$INFRASTRUCTURE" up -d ;;
  father)
    DC -f "$FATHER_API" up -d ;;
  lightweight)
    DC -f "$LIGHTWEIGHT_API" up -d ;;
  heavyweight)
    DC -f "$HEAVYWEIGHT_API" up -d ;;
  workers)
    DC -f "$WORKERS" up -d ;;
  xml-workers)
    DC -f "$XML_WORKERS" up -d ;;
  db)
    DC -f "$DB_API" up -d ;;
  monitoring)
    DC -f "$MONITORING" up -d ;;
  
  site-agent)
    banner "Site Agent: запуск"
    if [[ -f "$SITE_AGENT" ]]; then
      DC -f "$SITE_AGENT" up -d
    else
      err "Site Agent config не найден: $SITE_AGENT"
      exit 1
    fi ;;
  
  site-agent-logs)
    banner "Site Agent: логи"
    DC -f "$SITE_AGENT" logs -f site_agent ;;
  
  site-agent-restart)
    banner "Site Agent: перезапуск"
    DC -f "$SITE_AGENT" restart site_agent ;;

  # API 5 - Shop Parser
  api5-up)
    banner "API 5 - Shop Parser: запуск"
    need docker; ensure_networks
    DC -f "$SHOP_API" up -d ;;
  
  api5-up-db)
    banner "API 5 - Shop Parser: запуск с БД"
    need docker; ensure_networks
    DC -f "$SHOP_API" up -d api_5_db api_5_migrator
    sleep 5
    DC -f "$SHOP_API" up -d api_5 ;;
  
  api5-down)
    banner "API 5 - Shop Parser: остановка"
    DC -f "$SHOP_API" down ;;
  
  api5-logs)
    banner "API 5 - Shop Parser: логи"
    DC -f "$SHOP_API" logs -f api_5 ;;
  
  api5-restart)
    banner "API 5 - Shop Parser: перезапуск"
    DC -f "$SHOP_API" restart api_5 ;;
  
  api5-migrate)
    banner "API 5 - Shop Parser: миграции"
    DC -f "$SHOP_API" up api_5_migrator ;;
  
  api5-status)
    banner "API 5 - Shop Parser: статус"
    DC -f "$SHOP_API" ps ;;

  *)
    usage; exit 1 ;;
esac

# ========== Interactive Matrix Menu ==========
matrix_type(){
  local text="$1"; shift || true
  local delay="${1:-0.02}"
  while IFS= read -r -n1 ch; do
    printf "%s" "$ch"; sleep "$delay"
  done <<< "$text"
  echo
}

matrix_menu(){
  clear
  matrix_rain 1.2
  echo -e "${GREEN}${BOLD}wake up, neo...${NC}"; sleep 0.4
  echo -e "${GREEN}${BOLD}the HOST_API_SERVICE has you...${NC}"; sleep 0.4
  echo -e "${GREEN}${BOLD}follow the white rabbit.${NC}"; sleep 0.5
  echo
  matrix_type "1) start-all    — запустить всё"
  matrix_type "2) status       — статус контейнеров"
  matrix_type "3) logs         — логи всех сервисов"
  matrix_type "4) doctor       — диагностика"
  matrix_type "5) networks     — сети проекта"
  matrix_type "6) stacks       — управление стеком (up/down/logs)"
  matrix_type "7) prune        — очистка Docker"
  matrix_type "8) stop-all     — остановить всё"
  matrix_type "9) down-all     — удалить всё (с volume)"
  matrix_type "10) exit        — выход"
  echo
  read -p "${CYAN}neo@host_api> ${NC}" choice
  case "$choice" in
    1) "$0" start-all ;;
    2) "$0" status ;;
    3) "$0" logs ;;
    4) "$0" doctor ;;
    5) "$0" networks ;;
    6) stacks_menu ;;
    7) "$0" prune ;;
    8) "$0" stop-all ;;
    9) "$0" down-all ;;
    10|q|quit|exit) echo "${GREEN}goodbye, neo.${NC}"; exit 0 ;;
    *) echo -e "${YELLOW}неизвестный выбор${NC}" ;;
  esac
}

if [[ ${INTERACTIVE_MENU:-1} -eq 1 && $# -eq 0 ]]; then
  matrix_menu
  exit 0
fi
BASH


stacks_menu(){
  clear
  banner "Stacks"
  echo -e "${BOLD}Выберите стек:${NC}"
  echo "  1) infrastructure"
  echo "  2) db"
  echo "  3) father"
  echo "  4) lightweight"
  echo "  5) heavyweight"
  echo "  6) xml-workers (параллельная загрузка)"
  echo "  7) workers"
  echo "  8) monitoring"
  echo "  9) utilities"
  echo "  10) back"
  read -p "stack> " s
  case "$s" in
    1) st=INFRASTRUCTURE; file="$INFRASTRUCTURE" ;;
    2) st=DB;             file="$DB_API" ;;
    3) st=FATHER;         file="$FATHER_API" ;;
    4) st=LIGHTWEIGHT;    file="$LIGHTWEIGHT_API" ;;
    5) st=HEAVYWEIGHT;    file="$HEAVYWEIGHT_API" ;;
    6) st=XML_WORKERS;    file="$XML_WORKERS" ;;
    7) st=WORKERS;        file="$WORKERS" ;;
    8) st=MONITORING;     file="$MONITORING" ;;
    9) st=UTILITIES;      file="$UTILITIES" ;;
    10|q|exit) return 0 ;;
    *) echo -e "${YELLOW}неизвестный выбор${NC}"; return 0 ;;
  esac
  echo -e "${BOLD}Действие для ${CYAN}$st${NC}:${NC}"
  echo "  a) up -d"
  echo "  b) down"
  echo "  c) restart (файл)"
  echo "  d) logs -f"
  echo "  e) back"
  read -p "action> " a
  case "$a" in
    a) stack_up "$st" "$file" ;;
    b) stack_down "$st" "$file" ;;
    c) banner "Restart $st"; DC -f "$file" restart ;;
    d) banner "Logs $st"; DC -f "$file" logs -f ;;
    e|q|exit) : ;;
    *) echo -e "${YELLOW}неизвестное действие${NC}" ;;
  esac
}


matrix_rain(){
  local seconds="${1:-1.5}"
  local end=$(python3 -c "import time; print(time.time()+$seconds)")
  local cols=$(tput cols 2>/dev/null || echo 80)
  while python3 -c "import time; print('OK' if time.time() < $end else '')" 2>/dev/null | grep -q .; do
    line=""
    for i in $(seq 1 $cols); do
      line+="$(printf '\\033[32m' && printf %s "$(printf '%x' $RANDOM | head -c1)" && printf '\\033[0m')"
    done
    printf "%s\r" "$line"
    sleep 0.03
  done
  echo
}
