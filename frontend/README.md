# Frontend (Streamlit) - MCP Tools Inspector (STDIO)

STDIO ベースで起動する MCP サーバー (Python / Node) に接続し `list_tools` / `call_tool` を行うための簡易インスペクタ UI。
Azure Functions 側コードは変更しない要件のため、HTTP ラッパーは利用せず **純粋な MCP STDIO プロトコル** の PoC です。

## 機能
- 指定スクリプトを MCP サーバーとして STDIO 起動し接続
- ツール一覧表示 (name / description)
- 任意 JSON 引数でツール呼び出し・結果コンテンツ表示 (text 抽出)
- 参考: 対話型クライアント `mcp_client.py` も同梱

## 起動手順 (ローカル)
1. (任意) 仮想環境作成
   ```powershell
   python -m venv .venv; .\.venv\Scripts\Activate.ps1
   ```
2. 依存インストール
   ```powershell
   pip install -r requirements.txt
   ```
3. Streamlit 起動
   ```powershell
   streamlit run app.py
   ```
4. ブラウザ (自動 or http://localhost:8501) を開き、サイドバーの "MCP サーバースクリプトパス" に STDIO MCP サーバー (例: `server.py`) を入力して Connect

> 注意: ここで接続するスクリプトは Azure Functions ではなく STDIO MCP サーバー (独立プロセス) です。Functions の generic trigger ツールは直接 STDIO では動作しません。

### 対話型 MCP STDIO クライアント (`mcp_client.py`)
```powershell
python mcp_client.py path\to\server.py
```
`exit` / `quit` で終了。LLM 連携コードは含めていません (必要なら別途追加してください)。

## 設定
画面上部の "Functions ホスト ベース URL" に Functions のベース (通常 `http://localhost:7071/api`) を指定。

## 備考
- この UI は HTTP 経由の Functions ツール呼び出しを行いません。
- STDIO MCP サーバー実装例 (server.py など) のツールスキーマ内容に応じて引数 JSON を手動入力します。
- `mcp_client.py` は同等操作をコンソールで行う参考コードです。
- プロダクション用途ではプロセス管理 / エラーリカバリ / 認証などを強化してください。
