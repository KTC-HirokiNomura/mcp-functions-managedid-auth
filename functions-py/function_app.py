import azure.functions as func
import logging
import json
from datetime import datetime, timezone
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# ツールのプロパティを表すクラス
class ToolProperty:
    def __init__(self, property_name: str, property_type: str, description: str):
        self.propertyName = property_name
        self.propertyType = property_type
        self.description = description

    def to_dict(self):
        return {
            "propertyName": self.propertyName,
            "propertyType": self.propertyType,
            "description": self.description,
        }

# ---- 現在時刻取得ツール用設定 ----
tool_properties_now_object = []  # 引数なし
tool_properties_now_json = json.dumps([prop.to_dict() for prop in tool_properties_now_object])

# ---- 天気取得ツール用設定 ----
_WEATHER_CITY_PROPERTY_NAME = "city"
_WEATHER_TIME_PROPERTY_NAME = "time"
tool_properties_weather_object = [
    ToolProperty(_WEATHER_CITY_PROPERTY_NAME, "string", "都市名 (例: Tokyo)。"),
    ToolProperty(_WEATHER_TIME_PROPERTY_NAME, "string", "基準となる現在時刻 (ISO8601)。"),
]
tool_properties_weather_json = json.dumps([prop.to_dict() for prop in tool_properties_weather_object])

# 現在時刻 (UTC) を返すツール
@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_current_time",
    description="現在の UTC 時刻を ISO8601 で返します。",
    toolProperties=tool_properties_now_json,
)
def get_current_time(context) -> str:  # context には入力引数 (今回は無し) が含まれる
    now = datetime.now(timezone.utc).isoformat()
    logging.info(f"現在時刻(UTC): {now}")
    return json.dumps({"utcTime": now})


# 都市と現在時刻を受け取り天気情報を返すツール
@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_weather",
    description="都市と現在時刻を基に簡易な天気情報を返します。",
    toolProperties=tool_properties_weather_json,
)
def get_weather(context) -> str:
    """無料 API (wttr.in) を利用しシンプルな天気を取得。

    戻り値は JSON 文字列。
    例: {"city": "Tokyo", "time": "...", "weather": { ... }}
    """
    # context が文字列(JSON)で渡る場合と dict の場合に対応
    raw_context = context
    args: dict = {}
    try:
        if isinstance(raw_context, str):
            parsed = json.loads(raw_context)
        else:
            parsed = raw_context
        if isinstance(parsed, dict):
            # arguments / mcpToolArgs / 直接 の順で探索
            if isinstance(parsed.get("arguments"), dict):
                args = parsed.get("arguments")
            elif isinstance(parsed.get("mcpToolArgs"), dict):
                args = parsed.get("mcpToolArgs")
            else:
                # 直接含まれている可能性
                args = parsed
        else:
            logging.warning(f"get_weather: context が dict ではありません: {type(parsed)}")
    except Exception as e:
        logging.error(f"get_weather: context パース失敗: {e}; raw={raw_context}")
        return json.dumps({"error": "context の解析に失敗しました", "details": str(e)})

    city = args.get(_WEATHER_CITY_PROPERTY_NAME)
    time_value = args.get(_WEATHER_TIME_PROPERTY_NAME)

    if not city:
        return json.dumps({"error": "city が指定されていません"})
    if not time_value:
        # time が無い場合は現在 UTC
        time_value = datetime.now(timezone.utc).isoformat()

    # wttr.in の JSON (v2) API 利用
    url = f"https://wttr.in/{city}?format=j1"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        # シンプルに現在条件のみ抽出
        current = data.get("current_condition", [{}])[0]
        simplified = {
            "tempC": current.get("temp_C"),
            "tempF": current.get("temp_F"),
            "weatherDesc": current.get("weatherDesc", [{}])[0].get("value"),
            "windspeedKmph": current.get("windspeedKmph"),
            "humidity": current.get("humidity"),
        }
        result = {
            "city": city,
            "time": time_value,
            "weather": simplified,
        }
        logging.info(f"天気取得成功: {result}")
        return json.dumps(result, ensure_ascii=False)
    except requests.RequestException as e:
        logging.error(f"天気取得失敗: {e}")
        return json.dumps({"error": "天気情報取得に失敗しました", "details": str(e), "city": city})


# HTTP トリガーの定義
@app.route(route="http_trigger")
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function がリクエストを処理しました。')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"こんにちは、{name} さん。この HTTP トリガー関数は正常に実行されました。")
    else:
        return func.HttpResponse(
             "この HTTP トリガー関数は正常に実行されました。クエリ文字列またはリクエストボディに name を渡すと、個別の応答が得られます。",
             status_code=200
        )