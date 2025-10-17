FROM nginx:alpine

# Копируем конфигурацию
COPY nginx.conf /etc/nginx/nginx.conf

# Создаем директории для логов
RUN mkdir -p /var/log/nginx && \
    touch /var/log/nginx/game_bridge_access.log && \
    touch /var/log/nginx/game_bridge_error.log

# Проверка конфигурации при сборке НЕ выполняется
# т.к. nginx не может резолвить game_server_mock во время build
# Проверка будет выполнена при запуске контейнера

EXPOSE 5191

# Запуск nginx с проверкой конфигурации
CMD ["sh", "-c", "nginx -t && nginx -g 'daemon off;'"]

