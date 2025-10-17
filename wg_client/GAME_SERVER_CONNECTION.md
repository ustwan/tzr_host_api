# 🎮 Кто обращается к Game Server :5190?

## ✅ ОТВЕТ: API Father (с HOST_API)

**КТО:** API Father  
**ОТКУДА:** HOST_API (контейнер api_father)  
**КУДА:** HOST_SERVER (Game Server :5190)  
**КАК:** Socket TCP через VPN  
**ЧТО:** XML <ADDUSER>

## 📋 Резюме

api_father (HOST_API) → socket → Game Server (HOST_SERVER)

Код: wg_client/api_father/app/adapters/socket_game_server_client.py
