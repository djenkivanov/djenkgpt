import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Tuple, List, Dict, Any
import prompts
import tools
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
model = "gpt-4.1"

def classify_intent(user_input: str) -> str:
    """
    Classifies the user's intent using the classification system prompt.
    """
    intent = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompts.CLASSIFY_INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        max_tokens=50,
        temperature=0.0, # T = 0 for deterministic output
    )
    return intent.choices[0].message.content.strip()
    
    
def get_intent_prompt(intent: str) -> str:
    """
    Retrieves the system prompt for the given intent.
    """
    prompt = f'{'_'.join(intent.upper().split())}_INTENT_SYSTEM_PROMPT'
    return getattr(prompts, prompt, prompts.GENERAL_SYSTEM_PROMPT)


def generate_user_info(user_input: str) -> str:
    """
    Generates user information based on the user input.
    """
    user_info = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompts.MEMORY_PROMPT},
            {"role": "user", "content": user_input},
        ],
        max_tokens=300,
        temperature=0.0,
    )
    return user_info.choices[0].message.content.rstrip()


def update_user_info(memory_info: str, existing_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates the user information based on new memory information.
    """
    updated_info = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompts.USER_INFO_PROMPT},
            {"role": "system", "content": str(existing_info)},
            {"role": "user", "content": memory_info},
        ],
        max_tokens=300,
        temperature=0.0,
    )
    return updated_info.choices[0].message.content.rstrip()


def get_memory_block(short_term_memory:List[Dict[str, str]], long_term_memory, user_info: Dict[str, Any]):
    formatted_memory = "\n".join(f"{m['role']}: {m['content']}" for m in short_term_memory)
    memory_block = (
        f"USER INFORMATION:\n{json.dumps(user_info, indent=2)}"
        f"\n\nLONG-TERM MEMORY:\n{long_term_memory}\n\nSHORT-TERM MEMORY:\n{formatted_memory}" 
    )
    return memory_block


def generate_tool_response(user_input: str, intent_prompt: str, tool, tool_call_id, tool_response) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": intent_prompt},
            {"role": "user", "content": user_input},
            {"role": "assistant", "tool_calls": [
                {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": tool[0], "arguments": tool[1]}
                }
            ]},
            {"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps(tool_response)},
        ]
    )
    return response.choices[0].message


def generate_response(user_input: str, intent_prompt: str, memory_block: str) -> str:
    """
    Generates a response based on the user input, intent prompt, and user information.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": intent_prompt},
            {"role": "system", "content": memory_block},
            {"role": "user", "content": user_input},
        ],
        tool_choice="auto",
        tools=tools.TOOLS,
        max_tokens=500,
        temperature=0.7,
    )
    return response.choices[0].message


def update_long_term_memory(short_term_memory: List[Dict[str, str]], long_term_memory: str) -> str:
    chunk_size = 6
    formatted_memory = "\n".join(f"{m['role']}: {m['content']}" for m in short_term_memory[:chunk_size])
    summary = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompts.MEMORY_SUMMARIZATION_PROMPT},
            {"role": "user", "content": f"Existing Summary: {long_term_memory}\n\nChat History:\n{formatted_memory}"},
        ],
        max_tokens=300,
        temperature=0.0,
    )
    del short_term_memory[:chunk_size]
    return summary.choices[0].message.content.rstrip()

def gpt():
    trace: List[Tuple[str, str]] = []
    short_term_memory: List[Dict[str, str]] = []
    long_term_memory: str = ""
    user_info: Dict[str, Any] = {}
    
    print("Welcome to DjenkGPT! How can I assist you today?")
    
    while True:
        # summarize memory if it exceeds 16 exchanges (8 user-assistant pairs, messages), summarize by chunks of 3 after 5 pairs
        if len(short_term_memory) >= 16: 
            long_term_memory = update_long_term_memory(short_term_memory, long_term_memory)
            trace.append(("System", "Memory summarized to maintain context length."))
        user_input = input("You: ").rstrip()
        trace.append(("User", user_input))
        short_term_memory.append({"role": "user", "content": user_input})
        
        if user_input == "/quit":
            print("Thank you for using DjenkGPT! Goodbye!")
            break
            
        current_user_info = generate_user_info(user_input)
        user_info = update_user_info(current_user_info, user_info)
        
        intent = classify_intent(user_input)
        trace.append(("System", f"Classified Intent: {intent}"))
        intent_prompt = get_intent_prompt(intent)
        memory_block = get_memory_block(short_term_memory, long_term_memory, user_info)
        
        response = generate_response(user_input, intent_prompt, memory_block)
        tool_call = response.tool_calls
        if tool_call:
            tool_call_id = tool_call[0].id
            tool_call = tool_call[0].function
            tool = (tool_call.name, tool_call.arguments)
            # short_term_memory.append({"role": "tool", "content": f"Calling Tool: {tool[0]} with Args: {tool[1]}"})
            tool_response = tools.process_tool_call(tool[0], tool[1])
            # short_term_memory.append({"role": "tool", "content": tool_response['result'], "tool_call_id": tool_call_id})
            # response = generate_response(user_input, intent_prompt)
            response = generate_tool_response(user_input, intent_prompt, tool, tool_call_id, tool_response)
            trace.append(("Tool", f"Called Tool: {tool_response['tool_name']} with Result: {tool_response['result']}"))
        
        response = response.content.rstrip()     
        trace.append(("Assistant", response))
        short_term_memory.append({"role": "assistant", "content": response})
        print(f"Assistant: {response}\n")
        
    # Debug trace
    for role, content in trace:
        print(f"{role}: {content}\n") 
    
        
if __name__ == "__main__":
    gpt()