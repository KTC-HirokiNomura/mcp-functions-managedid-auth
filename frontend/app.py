import streamlit as st
import asyncio
import json
from typing import Dict, Any, Optional, List
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

st.set_page_config(page_title="MCP Tools Inspector (STDIO)", layout="wide")
st.title("MCP Tools Inspector (STDIO MCP Client)")

"""この UI は参照スクリプト (MCP サーバー: Python/Node) を STDIO で起動し、
list_tools / call_tool を行う PoC です。Azure Functions の HTTP ラッパーは使用しません。"""

# ----------------- MCP クライアント簡易ラッパ -----------------
class MCPClientSimple:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self.tools = []  # list of Tool (protocol objects)

    async def connect(self, server_path: str):
        if self.exit_stack:
            await self.exit_stack.aclose()
        self.exit_stack = AsyncExitStack()
        command = "python" if server_path.endswith('.py') else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_path],
            env={"PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"},
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport  # streams
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()
        response = await self.session.list_tools()
        self.tools = response.tools  # each has .name, .description, .inputSchema 等 (実装次第)
        return self.tools

    async def call_tool(self, tool_name: str, params: Dict[str, Any]):
        if not self.session:
            raise RuntimeError("Not connected")
        matches = [t for t in self.tools if t.name == tool_name]
        if not matches:
            raise ValueError(f"Tool '{tool_name}' not found")
        result = await self.session.call_tool(tool_name, params)
        return result.content  # list of TextContent / BlobContent etc.

    async def shutdown(self):
        if self.session:
            await self.session.shutdown()
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.exit_stack = None
            self.session = None
            self.tools = []


def _run_async(coro):
    """同期関数内で簡易に asyncio 実行 (PoC 用)。"""
    return asyncio.run(coro)


# ----------------- Streamlit State 初期化 -----------------
if "mcp_client" not in st.session_state:
    st.session_state.mcp_client = MCPClientSimple()
if "connected" not in st.session_state:
    st.session_state.connected = False
if "server_path" not in st.session_state:
    st.session_state.server_path = "server.py"  # 仮の初期値
if "tool_args_json" not in st.session_state:
    st.session_state.tool_args_json = "{}"


with st.sidebar:
    st.header("接続設定")
    server_path = st.text_input("MCP サーバースクリプトパス", value=st.session_state.server_path)
    col_a, col_b = st.columns(2)
    if col_a.button("Connect", type="primary"):
        try:
            tools = _run_async(st.session_state.mcp_client.connect(server_path))
            st.session_state.connected = True
            st.session_state.server_path = server_path
            st.success(f"Connected. {len(tools)} tools.")
        except Exception as e:
            st.session_state.connected = False
            st.error(f"接続失敗: {e}")
    if col_b.button("Disconnect"):
        try:
            _run_async(st.session_state.mcp_client.shutdown())
            st.session_state.connected = False
            st.success("Disconnected")
        except Exception as e:
            st.error(f"切断失敗: {e}")


st.subheader("ステータス")
st.write("Connected:" if st.session_state.connected else "Not Connected", st.session_state.server_path if st.session_state.connected else "-")

if not st.session_state.connected:
    st.info("サーバーへ接続してください。")
    st.stop()

# ----------------- ツール一覧表示 -----------------
tools = st.session_state.mcp_client.tools
if not tools:
    st.warning("ツールが取得できていません。")
else:
    with st.expander("ツール一覧", expanded=True):
        for t in tools:
            st.markdown(f"**{t.name}**  ")
            if getattr(t, "description", None):
                st.caption(t.description)

# ----------------- ツール実行 UI -----------------
tool_names = [t.name for t in tools]
selected_tool = st.selectbox("実行ツール", tool_names)

st.markdown("引数 (JSON)")
args_json = st.text_area("", value=st.session_state.tool_args_json, height=160)

col_run, col_clear = st.columns([1,1])

if col_run.button("Invoke", type="primary"):
    try:
        params = json.loads(args_json) if args_json.strip() else {}
    except Exception as e:
        st.error(f"JSON パース失敗: {e}")
    else:
        try:
            content_list = _run_async(st.session_state.mcp_client.call_tool(selected_tool, params))
            # content_list は protocol content のリスト。text を抽出。
            extracted: List[str] = []
            for c in content_list:
                # pydantic model 互換
                if hasattr(c, "text"):
                    extracted.append(c.text)
                else:
                    extracted.append(repr(c))
            st.success("実行成功")
            st.code(json.dumps({"tool": selected_tool, "raw": [getattr(c, 'model_dump', lambda: str(c))() for c in content_list]}, ensure_ascii=False, indent=2), language="json")
            if extracted:
                st.markdown("**Text Content**")
                for i, txt in enumerate(extracted, 1):
                    st.write(f"[{i}] {txt}")
        except Exception as e:
            st.error(f"呼び出し失敗: {e}")

if col_clear.button("Clear Args"):
    st.session_state.tool_args_json = "{}"
    st.experimental_rerun()

st.markdown("---")
st.caption("Streamlit UI for STDIO-based MCP server interaction. Functions 側コードは変更していません。")
