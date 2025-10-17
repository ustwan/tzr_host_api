# ⚠️ Проблема интеграции WG_HUB с API

## 🔴 Текущая проблема

**WG_HUB и API сервисы НЕ интегрированы правильно!**

### Что сейчас:

```
WG-Easy (network_mode: host)
  ↓ создает wg0 на хосте
  ↓ VPN сеть: 10.8.0.0/24
  ↓ Клиенты VPN: 10.8.0.2, 10.8.0.3, ...
  
Traefik (в Docker bridge сети)
  ↓ порт 1010
  ↓ сеть: host-api-network
  
API сервисы (в Docker bridge сети)
  ↓ порты 8081-8085, 9000
  ↓ сеть: host-api-network
```

**Проблема:** Клиенты VPN (10.8.0.x) **НЕ смогут** достучаться до API сервисов!

---

## ✅ Решения

### Решение 1: Публиковать порты на 0.0.0.0 (ПРОСТОЕ)

**Суть:** API сервисы слушают на всех интерфейсах хоста (включая wg0)

#### Изменения в compose файлах:

```yaml
# HOST_API_SERVICE_LIGHT_WEIGHT_API.yml
services:
  api_1:
    ports:
      - "0.0.0.0:8081:8081"  # Вместо просто "8081:8081"
  
  api_2:
    ports:
      - "0.0.0.0:8082:8082"

# HOST_API_SERVICE_FATHER_API.yml
services:
  api_father:
    ports:
      - "0.0.0.0:9000:9000"  # Вместо "8080:9000"

# HOST_API_SERVICE_INFRASTRUCTURE.yml
services:
  traefik:
    ports:
      - "0.0.0.0:1010:1010"
```

**После этого:**
```
VPN клиент (10.8.0.2)
  ↓ http://172.16.16.117:8081
  ↓ http://172.16.16.117:9000
  ✅ РАБОТАЕТ!
```

**Плюсы:**
- ✅ Просто
- ✅ Работает сразу

**Минусы:**
- ⚠️ Порты открыты на всех интерфейсах (нужен firewall)

---

### Решение 2: Traefik в host mode (ПРАВИЛЬНОЕ по WG_HUB логике)

**Суть:** Traefik слушает напрямую на wg0 интерфейсе (10.8.0.1:8081)

#### Изменения:

```yaml
# HOST_API_SERVICE_INFRASTRUCTURE.yml
services:
  traefik:
    image: traefik:v3.1
    network_mode: "host"  # ← Вместо bridge сети
    command:
      - "--entrypoints.vpn.address=10.8.0.1:8081"  # ← Слушаем на VPN IP
    # ports: убрать (host mode не нужны)
```

**API сервисы остаются в bridge сети**, но Traefik их видит через Docker provider.

**После этого:**
```
VPN клиент (10.8.0.2)
  ↓ http://10.8.0.1:8081/api/...
  ↓ Traefik маршрутизирует в Docker bridge
  ✅ РАБОТАЕТ!
```

**Плюсы:**
- ✅ Безопасно (доступ только из VPN)
- ✅ Соответствует Mode A из WG_HUB документации

**Минусы:**
- ⚠️ Нужно включить Docker provider в Traefik
- ⚠️ API должны быть в apinet сети

---

### Решение 3: Гибридное (РЕКОМЕНДУЮ)

**Суть:** API публикуются на хост IP, но защищены firewall

#### 1. Публикуем API на хост

```yaml
# Порты на 0.0.0.0 (все интерфейсы)
ports:
  - "0.0.0.0:8081:8081"
  - "0.0.0.0:8082:8082"
  - "0.0.0.0:9000:9000"
  - "0.0.0.0:1010:1010"
```

#### 2. Защищаем firewall

```bash
# Разрешить только VPN и локальную сеть
sudo ufw allow from 10.8.0.0/24 to any port 8081  # API_1
sudo ufw allow from 10.8.0.0/24 to any port 8082  # API_2
sudo ufw allow from 10.8.0.0/24 to any port 9000  # API_Father
sudo ufw allow from 10.8.0.0/24 to any port 1010  # Traefik

sudo ufw allow from 172.16.16.0/24 to any port 8081
sudo ufw allow from 172.16.16.0/24 to any port 8082
sudo ufw allow from 172.16.16.0/24 to any port 9000
sudo ufw allow from 172.16.16.0/24 to any port 1010

# Запретить остальным
sudo ufw default deny incoming
sudo ufw enable
```

**После этого:**
```
VPN клиент (10.8.0.2)
  ↓ http://172.16.16.117:8081  ✅ Разрешено firewall
  ↓ http://172.16.16.117:9000  ✅ Разрешено firewall

Внешний злоумышленник
  ↓ http://172.16.16.117:8081  ❌ Заблокировано firewall
```

---

## 🎯 Что нужно сделать

### Быстрое решение (для теста):

```bash
# На сервере включить IP forwarding (если еще не включено)
sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv4.conf.all.forwarding=1

# Добавить правило iptables для доступа из VPN к хосту
sudo iptables -A INPUT -i wg0 -j ACCEPT
sudo iptables -A FORWARD -i wg0 -j ACCEPT
sudo iptables -A FORWARD -o wg0 -j ACCEPT

# Сохранить правила
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

**После этого VPN клиенты смогут достучаться до портов на хосте!**

---

## 📋 Проверка работы VPN → API

### После запуска:

**1. На сервере:**
```bash
# Запустить WG_HUB
sudo bash tools/ctl.sh wg-hub

# Запустить API
sudo bash tools/ctl.sh start-all

# Проверить что wg0 создался
ip addr show wg0

# Должно показать:
# wg0: inet 10.8.0.1/24
```

**2. Создать VPN пользователя:**
```
http://172.16.16.117:2019
→ Создать пользователя
→ Скачать конфиг
→ Подключиться к VPN
```

**3. После подключения к VPN:**
```bash
# С вашего компьютера (в VPN)
ping 10.8.0.1          # Должен отвечать
ping 172.16.16.117     # Должен отвечать

# Проверить доступ к API
curl http://172.16.16.117:8082/health
curl http://172.16.16.117:9000/internal/health
curl http://172.16.16.117:1010
```

---

## ⚡ Правильная архитектура

### Сейчас нужна такая схема:

```
┌─────────────────────────────────────────┐
│ VPN Клиент (10.8.0.2)                   │
└───────────────┬─────────────────────────┘
                │ WireGuard VPN
                ↓
┌─────────────────────────────────────────┐
│ Сервер (172.16.16.117)                  │
├─────────────────────────────────────────┤
│                                         │
│ wg0 интерфейс: 10.8.0.1/24             │
│   ↓ iptables FORWARD                   │
│   ↓                                     │
│ Docker bridge (host-api-network)       │
│   ├─ Traefik :1010                     │
│   ├─ API_Father :9000                  │
│   ├─ API_1 :8081                       │
│   └─ API_2 :8082                       │
│                                         │
│ Порты опубликованы на 0.0.0.0          │
│ Firewall разрешает 10.8.0.0/24         │
│                                         │
└─────────────────────────────────────────┘
```

---

## ✅ Итоговый план действий

### 1. Обновить compose файлы (я это сделаю)

Изменить порты на `0.0.0.0:XXXX` для доступа из VPN

### 2. На сервере настроить firewall

```bash
# Включить IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1

# Разрешить VPN → хост
sudo iptables -A INPUT -i wg0 -j ACCEPT
sudo iptables -A FORWARD -i wg0 -j ACCEPT

# Сохранить
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

### 3. Запустить

```bash
sudo bash tools/ctl.sh start-full
```

---

**Сейчас я исправлю compose файлы чтобы API были доступны из VPN!**

