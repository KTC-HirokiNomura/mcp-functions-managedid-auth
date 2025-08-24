import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Optional, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

# 簡易的な LLM 呼び出し抽象化 (Claude API)
@dataclass
class LLMMessage:
    role: str
    content: str

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.history: List[LLMMessage] = []

    async def connect_to_server(self, server_script_path: str):
        """指定されたスクリプト (Python or Node) を STDIO MCP サーバーとして起動し接続。"""
        is_python = server_script_path.endswith('.py')
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None,
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.packet = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.packet))
        await self.session.initialize()
        response = await self.session.list_tools()
        tools = response.tools
        print("Connected to server. Tools:", [tool.name for tool in tools])

    async def invoke_tool(self, name: str, arguments: Optional[dict] = None):
        if not self.session:
            raise RuntimeError("Not connected")
        res = await self.session.call_tool(name, arguments or {})
        return res.content

    async def process_query(self, query: str) -> str:
        """シンプルなエコー + ツール呼び出し例。LLM 連携は削除。"""
        self.history.append(LLMMessage("user", query))
        tool_summary = ""
        try:
            tool_content = await self.invoke_tool("get_current_time")
            # content list から text を抽出
            texts = []
            for c in tool_content:
                txt = getattr(c, "text", repr(c))
                texts.append(txt)
            tool_summary = " | ".join(texts)
        except Exception as e:
            tool_summary = f"(get_current_time error: {e})"
        answer = f"受信: {query}\n現在時刻ツール: {tool_summary}"
        self.history.append(LLMMessage("assistant", answer))
        return answer

    async def chat_loop(self):
        print("Type 'exit' to quit.")
        while True:
            q = input("You> ").strip()
            if q.lower() in {"exit", "quit"}:
                break
            resp = await self.process_query(q)
            print(f"Assistant> {resp}")

    async def cleanup(self):
        if self.session:
            await self.session.shutdown()
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python mcp_client.py <path_to_server_script>")
        sys.exit(1)
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
