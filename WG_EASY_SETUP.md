# 🌐 WireGuard Easy - Веб-админка для VPN

## 🎯 Что это?

**WG-Easy** - красивая веб-админка для управления WireGuard пользователями:

- ✅ Создание/удаление пользователей VPN
- ✅ QR коды для мобильных устройств
- ✅ Просмотр статистики (трафик, последняя активность)
- ✅ Скачивание конфигов
- ✅ Простой веб-интерфейс

**GitHub:** https://github.com/wg-easy/wg-easy

---

## 🚀 Установка WG-Easy на HOST_SERVER

### Вариант 1: Docker Compose (рекомендуется)

Создайте файл на сервере где WireGuard:

```bash
# На сервере с WireGuard (например 172.16.16.117)
sudo mkdir -p /opt/wg-easy
cd /opt/wg-easy
sudo nano docker-compose.yml
```

```yaml
version: '3.8'

services:
  wg-easy:
    image: ghcr.io/wg-easy/wg-easy:latest
    container_name: wg-easy
    restart: unless-stopped
    
    # Важно! CAP_ADD для управления WireGuard
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    
    # Системные настройки
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1
    
    # Порты
    ports:
      - "51820:51820/udp"  # WireGuard VPN
      - "51821:51821/tcp"  # Веб-админка
    
    # Переменные
    environment:
      # Общие настройки
      - WG_HOST=172.16.16.117      # Ваш публичный IP или домен
      - PASSWORD=ваш_пароль_админки # Пароль для входа в веб-админку
      
      # Настройки VPN
      - WG_PORT=51820
      - WG_DEFAULT_ADDRESS=10.8.0.x
      - WG_DEFAULT_DNS=1.1.1.1,8.8.8.8
      - WG_ALLOWED_IPS=10.8.0.0/24
      
      # Опционально
      - WG_MTU=1420
      - WG_PERSISTENT_KEEPALIVE=25
    
    # Volumes
    volumes:
      - wg-easy-data:/etc/wireguard
    
    # Логи
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  wg-easy-data:
```

### Запуск:

```bash
cd /opt/wg-easy
sudo docker compose up -d

# Проверить логи
sudo docker logs -f wg-easy
```

### Доступ к веб-админке:

```
http://172.16.16.117:51821
```

**Логин:** (нет, только пароль)  
**Пароль:** тот что указали в `PASSWORD=...`

---

## 🎮 Использование WG-Easy

### 1. Открыть админку

```
Браузер → http://172.16.16.117:51821
Ввести пароль → Войти
```

### 2. Создать нового VPN пользователя

- Нажать **"+ New"**
- Ввести имя (например: `laptop`, `phone`, `friend1`)
- Нажать **"Create"**

### 3. Получить конфиг

- **QR код** - для мобильных (отсканировать в WireGuard приложении)
- **Download** - скачать `.conf` файл для компьютера
- **Copy** - скопировать текст конфига

### 4. Удалить пользователя

- Нажать на пользователя
- Кнопка **"Delete"**

### 5. Просмотр статистики

- **Latest Handshake** - когда последний раз подключался
- **Transfer** - сколько трафика использовал
- **Status** - онлайн/офлайн

---

## 🔄 Миграция с peer_admin.sh → WG-Easy

Если у вас уже есть пользователи через `peer_admin.sh`:

### Вариант A: Использовать существующий wg0.conf

```bash
# Копировать существующий конфиг
sudo cp /opt/wg-hub/config/wg_confs/wg0.conf /opt/wg-easy/wg0.conf

# В docker-compose.yml добавить:
volumes:
  - ./wg0.conf:/etc/wireguard/wg0.conf

# Запустить WG-Easy
sudo docker compose up -d
```

### Вариант B: Начать с чистого листа

```bash
# Просто запустить WG-Easy
# Он создаст новый wg0.conf
# Старых пользователей добавить заново через веб-админку
```

---

## 🌐 Доступ из локальной сети

### С вашего компьютера (172.16.16.x):

```
http://172.16.16.117:51821
```

### Если firewall блокирует:

```bash
# На сервере с WG-Easy
sudo ufw allow from 172.16.16.0/24 to any port 51821
```

---

## 🎯 Полная схема с WG-Easy

```
┌────────────────────────────────────────────────────────┐
│ Ваш компьютер (172.16.16.x)                            │
│   Браузер → http://172.16.16.117:51821                 │
│                  ↓                                     │
│            WG-Easy Web UI                              │
│                  ↓                                     │
│   • Создать пользователя VPN                          │
│   • Скачать QR код или конфиг                         │
│   • Просмотр статистики                               │
└────────────────────────────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────┐
│ Сервер (172.16.16.117)                                 │
├────────────────────────────────────────────────────────┤
│                                                        │
│ WG-Easy Container :51821                              │
│   ↓ управляет                                         │
│ WireGuard :51820/udp                                  │
│   Сеть: 10.8.0.0/24                                   │
│   Пиры: автоматически назначаются 10.8.0.2, 10.8.0.3...│
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 🔐 Безопасность

### Для production:

**1. Сильный пароль:**
```yaml
PASSWORD=Безопасный_Пароль_123!@#
```

**2. Ограничить доступ по IP:**
```yaml
ports:
  - "172.16.16.117:51821:51821"  # Только локальная сеть
```

**3. Или через обратный прокси с SSL:**
```nginx
# Nginx на сервере
server {
    listen 443 ssl;
    server_name wg-admin.example.com;
    
    ssl_certificate /etc/letsencrypt/...;
    ssl_certificate_key /etc/letsencrypt/...;
    
    location / {
        proxy_pass http://127.0.0.1:51821;
    }
}
```

---

## 📋 Команды управления

```bash
# Запустить WG-Easy
cd /opt/wg-easy
sudo docker compose up -d

# Логи
sudo docker logs -f wg-easy

# Перезапустить
sudo docker compose restart

# Остановить
sudo docker compose down

# Обновить
sudo docker compose pull
sudo docker compose up -d
```

---

## 🆚 WG-Easy vs peer_admin.sh

| Функция | peer_admin.sh | WG-Easy |
|---------|---------------|---------|
| **Интерфейс** | CLI | Веб-админка ✅ |
| **QR коды** | ❌ Нет | ✅ Да |
| **Статистика** | ❌ Нет | ✅ Да |
| **Удобство** | ⚠️ Сложно | ✅ Просто |
| **Автоматизация** | ✅ Скрипты | ⚠️ Ручная |

**Рекомендация:** Используйте WG-Easy для удобства! 🎉

---

## ⚡ Быстрая установка (копипаста)

```bash
# На сервере с WireGuard (172.16.16.117)
sudo mkdir -p /opt/wg-easy && cd /opt/wg-easy

# Создать docker-compose.yml
sudo tee docker-compose.yml > /dev/null <<'EOF'
version: '3.8'
services:
  wg-easy:
    image: ghcr.io/wg-easy/wg-easy:latest
    container_name: wg-easy
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1
    ports:
      - "51820:51820/udp"
      - "51821:51821/tcp"
    environment:
      - WG_HOST=172.16.16.117
      - PASSWORD=change_me_secure_password
      - WG_PORT=51820
      - WG_DEFAULT_ADDRESS=10.8.0.x
      - WG_DEFAULT_DNS=1.1.1.1
      - WG_ALLOWED_IPS=10.8.0.0/24
    volumes:
      - wg-easy-data:/etc/wireguard
volumes:
  wg-easy-data:
EOF

# Запустить
sudo docker compose up -d

# Открыть в браузере
# http://172.16.16.117:51821
```

**Готово!** Теперь у вас красивая веб-админка для VPN! 🎉

