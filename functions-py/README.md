# Azure Functions Python アプリ README

## 概要
本リポジトリは Azure Functions (Python) で実装されたサンプルです。以下 3 種類の Function を含みます。

1. HTTP トリガー `http_trigger`  
   - `GET/POST /api/http_trigger` でアクセス可能。`name` パラメータを受け取り挨拶を返します。
2. 汎用 (Generic) トリガー ツール: `get_current_time`  
   - 現在の UTC 時刻を ISO8601 形式で返す **MCP (Model Context Protocol) ツール想定** の関数。
3. 汎用 (Generic) トリガー ツール: `get_weather`  
   - 都市名と基準時刻を入力として簡易な天気情報を返す関数（現在は外部 API を呼ばないダミー実装）。

> `mcpToolTrigger` は Extension Bundle Experimental を利用した汎用トリガー定義です。通常の HTTP ルートは公開されません (カスタム バインディング / 拡張経由で呼び出される想定)。

---
## ディレクトリ構成 (抜粋)
```
function_app.py        # すべての関数定義 (FunctionApp オブジェクト)
host.json              # Functions ホスト設定 (拡張バンドル Experimental 利用)
local.settings.json    # ローカル実行用設定 (Azurite をストレージとして使用)
requirements.txt       # Python 依存パッケージ
__azurite_db_*         # Azurite ローカルエミュレーター データ
```

## 依存関係
- Python 3.11+ (開発環境では 3.12 想定)
- Azure Functions Core Tools v4 以降
- Azurite (ローカル ストレージ エミュレーター) — VS Code 拡張や `npm install -g azurite` で利用可能
- 外部 API: `https://wttr.in` (天気取得)

`requirements.txt`:
```
azure-functions
requests
types-requests
```

## 開発環境 (Dev Container 利用)
本リポジトリは **VS Code Dev Containers** (または GitHub Codespaces) 上での実行を前提としています。ローカルへ Python / Azure Functions Core Tools / Azurite を個別インストールする必要はありません。

### 前提ツール (ローカルマシン)
- Docker Desktop もしくは互換ランタイム
- VS Code + Dev Containers 拡張 (または Codespaces)

### 手順
1. リポジトリ取得
   ```bash
   git clone <THIS_REPO_URL>
   cd functions-py
   ```
2. VS Code でフォルダを開き、右下のポップアップまたはコマンドパレットから「Reopen in Container」を選択。
3. コンテナ構築完了後、自動タスクで `pip install -r requirements.txt` → `func host start` が起動します。バックグラウンド ターミナルにホストログが表示されます。
4. HTTP 関数へアクセス:
   ```bash
   curl "http://localhost:7071/api/http_trigger?name=DevContainer"
   ```

> もしホストが起動していない場合は VS Code のターミナルで `func start` を実行、またはタスク「func: host start」を再実行してください。

### 依存パッケージ追加
コンテナ内で `pip install <package>` 後、`requirements.txt` に追記してください。

### ローカル (Dev Container 非利用) で動かしたい場合
従来の Python venv + Functions Core Tools セットアップでも動作しますが、本 README では詳細手順を省略しています (一般的な Azure Functions Python 手順に準拠)。

## HTTP 関数の利用例
### クエリ パラメータ
```bash
curl "http://localhost:7071/api/http_trigger?name=Azure"
```
レスポンス例:
```
こんにちは、Azure さん。この HTTP トリガー関数は正常に実行されました。
```

### POST ボディ
```bash
curl -X POST "http://localhost:7071/api/http_trigger" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Taro"}'
```

## 汎用トリガー (MCP ツール) 関数について
`function_app.py` では `@app.generic_trigger(... type="mcpToolTrigger" ...)` を用いて 2 つのツール関数を定義しています。これらは以下のメタデータを持ち、外部のオーケストレーター (例: MCP サーバー / エージェント) から呼び出される想定です。

### 1. get_current_time
- 説明: 現在の UTC 時刻を取得
- 入力: なし
- 返却例:
```json
{"utcTime": "2025-08-20T12:34:56.789012+00:00"}
```

### 2. get_weather
- 説明: 指定都市の現在の簡易天気を取得
- 入力プロパティ:
  - `city` (string, 必須): 都市名 (例: "Tokyo")
  - `time` (string, 任意): ISO8601 時刻。省略時は関数内で現在 UTC を採用
- 返却例:
```json
{
  "city": "Tokyo",
  "time": "2025-08-20T12:35:00.000000+00:00",
  "weather": {
    "tempC": "30",
    "tempF": "86",
    "weatherDesc": "Partly cloudy",
    "windspeedKmph": "12",
    "humidity": "70"
  }
}
```
- エラー例:
```json
{"error": "city が指定されていません"}
```

### テスト呼び出し (簡易)
直接 Python から関数ロジックを呼ぶことで挙動確認できます。
```python
from function_app import get_current_time, get_weather
print(get_current_time(None))
print(get_weather({"city": "Tokyo", "time": "2025-08-20T00:00:00Z"}))
```
> 実際の Generic Trigger バインディング経由の呼び出し方法は、利用する拡張機能 / ホスト (MCP サーバー等) 側の実装に依存します。

## 実装上のポイント
- `ToolProperty` クラスでツールの引数メタデータを定義し JSON 化。
- `get_weather` では受信 `context` が文字列 JSON / dict どちらでも安全にパースする防御的実装。
- 現在の `get_weather` は外部 API を呼ばず、ランダム生成されたダミーの天気情報を返します（テスト用）。将来的に外部 API を戻す場合は retry ロジック（既に一部実装済）を活用できます。
- 文字列化には `json.dumps(..., ensure_ascii=False)` を一部使用し日本語保持。
- Extension Bundle: `Microsoft.Azure.Functions.ExtensionBundle.Experimental` を利用 (将来的な互換性変更に留意)。

## 環境変数 / 設定
`local.settings.json` (ローカルのみ) に以下が設定:
- `AzureWebJobsStorage`: `useDevelopmentStorage=true` (Azurite 利用)
- `FUNCTIONS_WORKER_RUNTIME`: `python`

本番デプロイ時はポータルまたは `az functionapp config appsettings set` で適切なストレージ接続文字列を設定してください。

Dev Container / Codespaces では同梱の `local.settings.json` がそのまま使用され、Azurite データはワークスペース内の `__azurite_db_*` / `__blobstorage__` 等に格納されます。

## トラブルシュート
| 症状 | 対処 |
|------|------|
| `AzureWebJobsStorage` 関連エラー | Azurite が起動しているか、接続文字列が正しいか確認 |
| `No module named 'azure.functions'` | 依存インストール漏れ。`pip install -r requirements.txt` |
| 天気 API でタイムアウト | ネットワーク疎通 / プロキシ設定を確認。`timeout` 値の調整検討 |
| Generic Trigger が呼べない | 拡張バンドルのバージョン確認。対応する拡張がデプロイ先にあるか確認 |
