# DB Bridge Production Setup Guide

## Развертывание на HOST_SERVER

### 1. Установка Nginx

```bash
# На HOST_SERVER
sudo apt-get update
sudo apt-get install -y nginx
```

### 2. Копирование сертификатов

```bash
# Создать директорию для сертификатов
sudo mkdir -p /etc/nginx/certs/{ca,server,client_register,client_readonly,client_admin}

# Скопировать сертификаты с HOST_API (или сгенерировать на месте)
sudo cp ca/ca.{crt,key} /etc/nginx/certs/ca/
sudo cp server/server.{crt,key} /etc/nginx/certs/server/
sudo cp client_register/client.{crt,key} /etc/nginx/certs/client_register/
sudo cp client_readonly/client.{crt,key} /etc/nginx/certs/client_readonly/
sudo cp client_admin/client.{crt,key} /etc/nginx/certs/client_admin/

# Установить правильные права
sudo chmod 644 /etc/nginx/certs/*/*.crt
sudo chmod 600 /etc/nginx/certs/*/*.key
sudo chown -R root:root /etc/nginx/certs
```

### 3. Конфигурация Nginx

Создать `/etc/nginx/nginx.conf`:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

stream {
    # Логирование
    log_format mtls '$remote_addr [$time_local] '
                    '$protocol $status $bytes_sent $bytes_received '
                    '$session_time "$ssl_client_s_dn"';
    
    access_log /var/log/nginx/db_bridge_access.log mtls;
    error_log /var/log/nginx/db_bridge_error.log;

    # DB Bridge mTLS proxy
    server {
        listen 3307 ssl;
        proxy_pass 127.0.0.1:3306;  # Локальный MySQL
        
        # Сертификаты сервера
        ssl_certificate /etc/nginx/certs/server/server.crt;
        ssl_certificate_key /etc/nginx/certs/server/server.key;
        
        # Требование клиентских сертификатов
        ssl_client_certificate /etc/nginx/certs/ca/ca.crt;
        ssl_verify_client on;
        ssl_verify_depth 2;
        
        # Настройки SSL
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # Прокси настройки
        proxy_connect_timeout 10s;
        proxy_timeout 300s;
        proxy_buffer_size 16k;
    }
}
```

### 4. Создание БД-пользователей

```bash
# Подключиться к MySQL
mysql -u root -p

# Выполнить скрипт создания пользователей
source /path/to/002_mtls_users.sql;
```

### 5. Настройка файрвола

```bash
# Разрешить порт 3307 только из VPN сети
sudo ufw allow from 10.8.0.0/24 to any port 3307 proto tcp
sudo ufw reload
```

### 6. Запуск и проверка

```bash
# Проверить конфигурацию
sudo nginx -t

# Запустить Nginx
sudo systemctl enable nginx
sudo systemctl restart nginx

# Проверить логи
sudo tail -f /var/log/nginx/db_bridge_access.log
sudo tail -f /var/log/nginx/db_bridge_error.log
```

## Интеграция с HOST_API

### Переменные окружения для продакшн

В `wg_client/.env` на HOST_API:

```bash
# DB Bridge (продакшн)
DB_BRIDGE_HOST=10.8.0.20  # IP HOST_SERVER в VPN
DB_BRIDGE_PORT=3307
DB_BRIDGE_VERIFY_SSL=true

# Сертификаты (монтировать в контейнеры)
DB_CA_CERT=/certs/ca/ca.crt

# api_father (регистрация)
DB_FATHER_USER=api_register
DB_FATHER_PASSWORD=register_pass_change_me
DB_FATHER_CERT=/certs/client_register/client.crt
DB_FATHER_KEY=/certs/client_register/client.key

# api_1, api_2 (чтение)
DB_READONLY_USER=api_readonly
DB_READONLY_PASSWORD=readonly_pass_change_me
DB_READONLY_CERT=/certs/client_readonly/client.crt
DB_READONLY_KEY=/certs/client_readonly/client.key

# api_4, api_mother (админ)
DB_ADMIN_USER=api_admin
DB_ADMIN_PASSWORD=admin_pass_change_me
DB_ADMIN_CERT=/certs/client_admin/client.crt
DB_ADMIN_KEY=/certs/client_admin/client.key
```

### Монтирование сертификатов в compose

Добавить в `HOST_API_SERVICE_FATHER_API.yml`:

```yaml
services:
  api_father:
    volumes:
      - ./mock_host_server/certs/ca:/certs/ca:ro
      - ./mock_host_server/certs/client_register:/certs/client_register:ro
    environment:
      - DB_BRIDGE_HOST=${DB_BRIDGE_HOST:-mock_db_bridge}
      - DB_BRIDGE_PORT=${DB_BRIDGE_PORT:-3307}
      - DB_USER=${DB_FATHER_USER:-api_register}
      - DB_PASSWORD=${DB_FATHER_PASSWORD:-register_pass_change_me}
      - DB_CA_CERT=${DB_CA_CERT:-/certs/ca/ca.crt}
      - DB_CLIENT_CERT=${DB_FATHER_CERT:-/certs/client_register/client.crt}
      - DB_CLIENT_KEY=${DB_FATHER_KEY:-/certs/client_register/client.key}
```

## Мониторинг

### Логи Nginx

```bash
# Просмотр подключений по пользователям
sudo tail -f /var/log/nginx/db_bridge_access.log | grep "CN=api_"

# Подсчет подключений по типам
sudo cat /var/log/nginx/db_bridge_access.log | grep -oP 'CN=\K[^"]+' | sort | uniq -c
```

### Метрики MySQL

```sql
-- Подключения по пользователям
SELECT user, host, COUNT(*) as connections 
FROM information_schema.processlist 
GROUP BY user, host;

-- Активность по пользователям
SELECT user, command, COUNT(*) 
FROM information_schema.processlist 
GROUP BY user, command;
```

## Безопасность

1. **Ротация сертификатов**: Обновлять раз в год или при компрометации
2. **Мониторинг неудачных подключений**: Алерты на `ssl_verify_client failed`
3. **Аудит прав**: Регулярно проверять права пользователей БД
4. **Сетевая изоляция**: db_bridge доступен только из VPN

## Troubleshooting

### Ошибка: "SSL routines:ssl3_read_bytes:tlsv1 alert unknown ca"

```bash
# Проверить CA сертификат
openssl verify -CAfile /etc/nginx/certs/ca/ca.crt \
  /etc/nginx/certs/client_register/client.crt
```

### Ошибка: "Access denied for user 'api_register'@'host'"

```sql
-- Проверить права пользователя
SHOW GRANTS FOR 'api_register'@'%';

-- Пересоздать пользователя
DROP USER IF EXISTS 'api_register'@'%';
source /path/to/002_mtls_users.sql;
```

### Ошибка: "Connection timed out"

```bash
# Проверить файрвол
sudo ufw status

# Проверить что Nginx слушает порт
sudo ss -tlnp | grep 3307

# Проверить доступность из HOST_API
nc -zv 10.8.0.20 3307
```










