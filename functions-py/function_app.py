import azure.functions as func
import logging
import json
from datetime import datetime, timezone
import requests
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Configure a requests Session with retries to make external API calls more resilient
_SESSION = requests.Session()
_RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=["GET"],
)
_ADAPTER = HTTPAdapter(max_retries=_RETRY_STRATEGY)
_SESSION.mount("https://", _ADAPTER)
_SESSION.mount("http://", _ADAPTER)

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
def get_current_time(context):  # context には入力引数 (今回は無し) が含まれる
    now = datetime.now(timezone.utc).isoformat()
    logging.info(f"現在時刻(UTC): {now}")
    # Return a Python dict so the host serializes to JSON (prevents double-encoding)
    return {"utcTime": now}


# 都市と現在時刻を受け取り天気情報を返すツール
@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_weather",
    description="都市と現在時刻を基に簡易な天気情報を返します。",
    toolProperties=tool_properties_weather_json,
)
def get_weather(context):
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
        return {"error": "city が指定されていません"}
    if not time_value:
        # time が無い場合は現在 UTC
        time_value = datetime.now(timezone.utc).isoformat()

    # 仮の天気情報をランダムで生成（外部 API を使用しない）
    try:
        tempC = random.randint(-10, 35)
        tempF = round(tempC * 9 / 5 + 32, 1)
        weather_choices = [
            "Sunny",
            "Partly cloudy",
            "Cloudy",
            "Rain",
            "Light rain",
            "Thunderstorm",
            "Snow",
            "Fog",
        ]
        weatherDesc = random.choice(weather_choices)
        wind = random.randint(0, 40)
        humidity = random.randint(20, 100)
        simplified = {
            "tempC": str(tempC),
            "tempF": str(tempF),
            "weatherDesc": weatherDesc,
            "windspeedKmph": str(wind),
            "humidity": str(humidity),
        }
        result = {
            "city": city,
            "time": time_value,
            "weather": simplified,
        }
        logging.info(f"天気(仮)生成成功: {result}")
        return result
    except Exception as e:
        logging.error(f"天気(仮)生成失敗: {e}")
        return {"error": "天気情報生成に失敗しました", "details": str(e), "city": city}


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