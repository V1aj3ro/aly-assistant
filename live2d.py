"""
live2d.py — VTube Studio WebSocket API

Документация: https://github.com/DenchiSoft/VTubeStudio
"""

import json
import asyncio
import logging
import os

import websockets

import config

logger = logging.getLogger(__name__)

PLUGIN_ID = "aly_assistant_v1"


class VTubeStudio:
    def __init__(self):
        self._ws = None
        self._token: str | None = None
        self._connected = False
        self._req_id = 0

    # ------------------------------------------------------------------
    async def connect(self):
        """Подключиться к VTube Studio и аутентифицироваться."""
        try:
            self._ws = await websockets.connect(config.VTS_HOST, ping_interval=20)
            self._connected = True
            logger.info("VTube Studio подключён: %s", config.VTS_HOST)
            await self.authenticate()
        except Exception as exc:
            logger.warning("VTube Studio недоступен: %s", exc)
            self._connected = False

    async def disconnect(self):
        if self._ws:
            await self._ws.close()
        self._connected = False

    # ------------------------------------------------------------------
    async def authenticate(self):
        """Аутентификация плагина. Первый раз — пользователь подтверждает в VTS."""
        self._token = self._load_token()

        if not self._token:
            # Запрашиваем токен (пользователь должен нажать "Allow" в VTS)
            resp = await self._request("AuthenticationTokenRequest", {
                "pluginName": config.VTS_PLUGIN_NAME,
                "pluginDeveloper": config.VTS_PLUGIN_DEV,
            })
            self._token = resp.get("data", {}).get("authenticationToken", "")
            self._save_token(self._token)
            logger.info("Получен токен VTS, сохранён в %s", config.VTS_TOKEN_FILE)

        # Используем токен
        resp = await self._request("AuthenticationRequest", {
            "pluginName": config.VTS_PLUGIN_NAME,
            "pluginDeveloper": config.VTS_PLUGIN_DEV,
            "authenticationToken": self._token,
        })

        authenticated = resp.get("data", {}).get("authenticated", False)
        if authenticated:
            logger.info("VTube Studio: аутентификация успешна")
        else:
            logger.warning("VTube Studio: аутентификация не удалась, сбрасываем токен")
            self._token = None
            self._save_token("")

    # ------------------------------------------------------------------
    async def start_talking(self):
        """Включить параметр открытия рта."""
        if not self._connected:
            return
        try:
            await self._inject_param("MouthOpen", 1.0)
            await self._inject_param("MouthSmile", 0.3)
        except Exception as exc:
            logger.debug("start_talking ошибка: %s", exc)

    async def stop_talking(self):
        """Выключить анимацию рта."""
        if not self._connected:
            return
        try:
            await self._inject_param("MouthOpen", 0.0)
            await self._inject_param("MouthSmile", 0.0)
        except Exception as exc:
            logger.debug("stop_talking ошибка: %s", exc)

    async def set_expression(self, name: str):
        """Активировать выражение (happy/sad/surprised/neutral)."""
        if not self._connected:
            return
        try:
            await self.send_hotkey(name)
        except Exception as exc:
            logger.debug("set_expression ошибка: %s", exc)

    async def send_hotkey(self, name: str):
        """Триггер хоткея в VTube Studio."""
        if not self._connected:
            return
        try:
            await self._request("HotkeyTriggerRequest", {"hotkeyID": name})
        except Exception as exc:
            logger.debug("send_hotkey ошибка: %s", exc)

    # ------------------------------------------------------------------
    async def _inject_param(self, param_id: str, value: float):
        """Установить значение параметра Live2D модели."""
        await self._request("InjectParameterDataRequest", {
            "parameterValues": [
                {"id": param_id, "value": value}
            ]
        })

    async def _request(self, msg_type: str, data: dict) -> dict:
        """Отправить запрос и получить ответ."""
        self._req_id += 1
        payload = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": str(self._req_id),
            "messageType": msg_type,
            "data": data,
        }
        await self._ws.send(json.dumps(payload))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
        return json.loads(raw)

    # ------------------------------------------------------------------
    @staticmethod
    def _load_token() -> str | None:
        if os.path.exists(config.VTS_TOKEN_FILE):
            with open(config.VTS_TOKEN_FILE, "r") as f:
                token = f.read().strip()
                return token or None
        return None

    @staticmethod
    def _save_token(token: str):
        with open(config.VTS_TOKEN_FILE, "w") as f:
            f.write(token)
