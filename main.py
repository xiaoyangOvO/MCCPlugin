import asyncio
import json
import uuid
import websockets
from pkg.plugin.context import register, llm_func, BasePlugin, APIHost

MCC_WS_ADDRESS = "ws://localhost:8043"  # 替换为实际的 MCC WebSocket 地址
MCC_WS_PASSWORD = "81931f63a23b49c3af2c254cc2e55eb4"  # 如果设置了密码，请替换

@register(name="MCServerQuery", description="Query Minecraft server status via MCC", version="0.2", author="Assistant")
class MCServerQueryPlugin(BasePlugin):

    def __init__(self, host: APIHost):
        super().__init__(host)
        self.ws = None
        self.authenticated = False

    async def initialize(self):
        await self.connect_to_mcc()

    async def connect_to_mcc(self):
        self.ws = await websockets.connect(MCC_WS_ADDRESS)
        if MCC_WS_PASSWORD:
            await self.authenticate()

    async def authenticate(self):
        auth_command = {
            "command": "Authenticate",
            "requestId": str(uuid.uuid4()),
            "parameters": [MCC_WS_PASSWORD]
        }
        await self.ws.send(json.dumps(auth_command))
        response = await self.ws.recv()
        self.authenticated = json.loads(response)["success"]

    async def send_command(self, command, params=None):
        if not self.ws or not self.authenticated:
            await self.connect_to_mcc()
        
        request_id = str(uuid.uuid4())
        command_data = {
            "command": command,
            "requestId": request_id,
            "parameters": params or []
        }
        await self.ws.send(json.dumps(command_data))
        
        response = await asyncio.wait_for(self.ws.recv(), timeout=10)
        return json.loads(response)

    @llm_func(name="get_online_players")
    async def get_online_players(self):
        """
        Get the list of online players on the Minecraft server.

        Returns:
            str: A string containing the list of online players.
        """
        response = await self.send_command("SendText", ["/list"])
        return response.get("result", "Failed to get online players")

    @llm_func(name="get_server_tps")
    async def get_server_tps(self):
        """
        Get the TPS (Ticks Per Second) of the Minecraft server.

        Returns:
            str: A string containing the server's TPS information.
        """
        response = await self.send_command("SendText", ["/tps"])
        return response.get("result", "Failed to get server TPS")

    @llm_func(name="send_chat_message")
    async def send_chat_message(self, message: str):
        """
        Send a chat message to the Minecraft server.

        Args:
            message (str): The message to send.

        Returns:
            str: A confirmation message.
        """
        response = await self.send_command("SendText", [message])
        return "Message sent successfully" if response.get("success") else "Failed to send message"

    def __del__(self):
        if self.ws:
            asyncio.get_event_loop().run_until_complete(self.ws.close())

