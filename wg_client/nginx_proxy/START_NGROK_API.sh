#!/bin/bash

echo "🌐 Запуск ngrok туннеля для API..."
echo ""
echo "⚠️ ВАЖНО: Сохраните URL который выдаст ngrok"
echo "   Он понадобится для настройки сайта!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Запуск ngrok для порта 8090 (Nginx API proxy)
ngrok http 8090
