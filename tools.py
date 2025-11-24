import python_weather
from typing import Dict, Any, Callable, List
import re, json
import asyncio
from ollama import Client
import os
from dotenv import load_dotenv
from openai import OpenAI
import prompts
from scipy.spatial import distance
import numpy as np


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

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
    ollama_client = Client(headers={"Authorization": f"Bearer {os.getenv('OLLAMA_KEY')}"})
    response = ollama_client.web_search(query)
    formatted_results = []
    for result in response['results']:
        formatted_results.append({
            "title": result["title"],
            "url": result["url"],
            "content": result["content"]
        })
        
    summaries = summarize_search(formatted_results)
    relevant_summary = get_most_relevant_result(summaries, query)
    return relevant_summary


def calculate_expression(expression: str) -> str:
    try:
        allowed_chars = "0123456789+-*/(). "
        if any(char not in allowed_chars for char in expression):
            return "Error: Invalid characters in expression."
        result = eval(expression)
        return result
    except Exception as e:
        return f"Error: {str(e)}"


CALL_TOOL: Dict[str, Callable[..., Any]] = {
    "get_weather": get_weather,
    "web_search": web_search,
    "calculate_expression": calculate_expression,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a specific location."
                            "Use this function to answer any weather-related questions from the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city to get the weather for."
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Searches the web for the given query and returns a list of results."
                            "Only use this function if no tool can answer the user's question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_expression",
            "description": "Calculator tool to compute mathematical expressions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression to calculate."
                    },
                },
                "required": ["expression"],
            },
        },
    }
]


def process_tool_call(tool_name, tool_args) -> Dict[str, Any] | None:
    tool_args = json.loads(tool_args)
    if tool_name == 'get_weather':
        response = asyncio.run(CALL_TOOL[tool_name](**tool_args))
    else:
        response = CALL_TOOL[tool_name](**tool_args)
    return {"tool_name": tool_name, "result": response}


def summarize_search(results: List[Dict[str, str]]):
    summaries = []
    for r in results:
        summary = client.chat.completions.create(
            model="gpt-4.1-mini", # cheaper model for summarization, better results, cheaper than gpt-4.1
            messages=[
                {"role": "system", "content": prompts.SUMMARY_PROMPT},
                {"role": "user", "content": f"Summarize the following search result:\nTitle: {r['title']}\nURL: {r['url']}\nContent: {r['content']}"}
            ],
            max_tokens=300,
            temperature=0.5,
        )
        summaries.append(summary.choices[0].message.content.rstrip())
    return summaries


def get_most_relevant_result(summaries: List[str], query: str) -> str:
    summary_embeddings = []
    for summary in summaries:
        embedding = client.embeddings.create(
            model="text-embedding-3-small",
            input=summary
        ).model_dump()['data'][0]['embedding']
        summary_embeddings.append(embedding)
        
    search_embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).model_dump()['data'][0]['embedding']
    distances = [
        distance.cosine(search_embedding, summary_embedding) for summary_embedding in summary_embeddings
    ]
    closest_index = np.argmin(distances)
    return summaries[closest_index]
    
    

if __name__ == "__main__":
    response = process_tool_call('web_search', {'query':'AI news'})
    summary = summarize_search(response['result'])
    relevant_summary = get_most_relevant_result(summary, 'latest advancements in AI technology')
    print(relevant_summary)

    
        