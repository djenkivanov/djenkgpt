import python_weather
from typing import Dict, Any, Callable
import re, json
import asyncio
from ollama import Client
import os
from dotenv import load_dotenv
load_dotenv()

# https://python-weather.readthedocs.io/en/latest/
async def get_weather(city: str) -> Dict[str, Any]:
    async with python_weather.Client(unit=python_weather.METRIC) as client:
        weather = await client.get(city)
        return {
            "temp_c": weather.temperature,
            "condition": weather.description
        }
        
# https://docs.ollama.com/capabilities/web-search#web-search-api
def web_search(query: str) -> Dict[str, Any]:
    client = Client(headers={"Authorization": f"Bearer {os.getenv('OLLAMA_KEY')}"})
    response = client.web_search(query)
    formatted_results = []
    for result in response['results']:
        formatted_results.append({
            "title": result["title"],
            "url": result["url"],
            "content": result["content"]
        })
    return formatted_results


TOOLS: Dict[str, Callable[..., Any]] = {
    "get_weather": get_weather,
    "web_search": web_search,
}

TOOL_INV = [
    {"name": "get_weather", "args": {"city": "str"}, "returns": {"temp_c": "int", "condition": "str"},
     "desc": "Returns current weather for a specific city."},
    
    {"name": "web_search", "args": {"query": "str"}, "returns": {"results": "list"},
     "desc": "Searches the web for the given query and returns a list of results."},
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
    if tool_name == 'get_weather':
        response = asyncio.run(TOOLS[tool_name](**tool_args))
    else:
        response = TOOLS[tool_name](**tool_args)
    return {"tool_name": tool_name, "result": response}


if __name__ == "__main__":
    # ob = {
    #     "preferences": {
    #         "<preference_key>": "<preference_value>",
    #     },
    #     "facts": [
    #         "<fact_1>",
    #         "<fact_2>",
    #     ]
    # }
    
    # print(ob)
    # print(str(ob))
    response = process_tool_call('web_search', {'query':'AI news'})
    # response = {
    #     "tool_name": 'web_search',
    #     "result": [
    #         {'title': 'Sample Title', 'url': 'http://example.com', 'content': 'Sample content about AI news.'},
    #         {'title': 'Another Title', 'url': 'http://example2.com', 'content': 'More sample content about AI news.'},
    #         {'title': 'Third Title', 'url': 'http://example3.com', 'content': 'Additional sample content about AI news.'},
    #     ],
    # }
    print(json.dumps(response['result'], indent=2))
    # for r in json.loads(response["result"]):
    #     print(f'Title: {r["title"]}\nURL: {r["url"]}')
    
        