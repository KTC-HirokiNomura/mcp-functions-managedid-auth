# Eino + Azure OpenAI minimal example (MVP)

このフォルダは Eino フレームワークを使い、Azure OpenAI（GPT-5-mini）へ Chat リクエストを送る最小実装サンプルです。

デフォルト値（サンプル）
- Endpoint: `https://dev-genai-eastus2.openai.azure.com`
- Deployment: `gpt-5-mini-nomura`
- API Key: `d673c76b7e4743c381f0c35139c49d14`

注意: 実運用では API キーをソースに置かないでください。環境変数またはシークレットストアを使用してください。

要件
- Go 1.20+

実行方法（ローカル、MVP）
1. モジュール依存を解決:

```bash
cd frontend
go mod tidy
```

2. サンプル実行（デフォルト値を使用）:

```bash
go run main.go
```

3. 環境変数やフラグで上書きできます:

```bash
# 環境変数で上書き
AZURE_OPENAI_ENDPOINT=https://your.openai.azure.com AZURE_OPENAI_DEPLOYMENT=your-deploy AZURE_OPENAI_API_KEY=yourkey go run main.go

# もしくはフラグで指定（フラグは優先）
go run main.go -endpoint https://your.openai.azure.com -deployment your-deploy -apikey yourkey -timeout 60
```

Notes
- このサンプルは net/http を使った最小実装です。Managed Identity を用いる場合や production では `azidentity`/`azopenai` を検討してください。
