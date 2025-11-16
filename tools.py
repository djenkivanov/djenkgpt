import python_weather
from typing import Dict, Any, Callable
import re, json
import asyncio

async def get_weather(city: str) -> Dict[str, Any]:
    async with python_weather.Client(unit=python_weather.METRIC) as client:
        weather = await client.get(city)
        return {
            "temp_c": weather.temperature,
            "condition": weather.description
        }
        

TOOLS: Dict[str, Callable[..., Any]] = {
    "get_weather": get_weather,
}

TOOL_INV = [
    {"name": "get_weather", "args": {"city": "str"}, "returns": {"temp_c": "int", "condition": "str"},
     "desc": "Returns current weather for a specific city."},
]


TOOL_CALL_REGEX = re.compile(r"^\$TOOL:(\w+)\s({.*})\$$", re.MULTILINE)


def detect_tool_call(text: str):
    """
    Returns (tool_name, args_dict) or None.
    """
    tools = TOOL_CALL_REGEX.search(text.strip())
    if not tools:
        return None
    tool_name = tools.group(1)
    try:
        tool_args = json.loads(tools.group(2))
    except json.JSONDecodeError:
        return None
    return tool_name, tool_args


def process_tool_call(tool_name, tool_args) -> Dict[str, Any] | None:
    tool_name, tool_args
    response = asyncio.run(TOOLS[tool_name](**tool_args))
    return {"tool_name": tool_name, "result": json.dumps(response)}


if __name__ == "__main__":
    city = "Belgium"
    weather_info = asyncio.run(TOOLS["get_weather"](city))
    print(f"Current weather in {city}: {weather_info['temp_c']}°C, {weather_info['condition']}")