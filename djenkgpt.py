import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Tuple, List, Dict, Any
import prompts
import tools

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

def generate_response(user_input: str, intent_prompt: str, memory:List[Dict[str, str]], user_info: Dict[str, Any]) -> str:
    """
    Generates a response based on the user input, intent prompt, and user information.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": intent_prompt},
            {"role": "system", "content": str(memory)},
            {"role": "system", "content": user_info},
            {"role": "user", "content": user_input},
        ],
        max_tokens=500,
        temperature=0.7,
    )
    return response.choices[0].message.content.rstrip()


def gpt():
    trace: List[Tuple[str, str]] = []
    memory: List[Dict[str, str]] = []
    user_info: Dict[str, Any] = {}
    
    print("Welcome to DjenkGPT! How can I assist you today?")
    
    while True:
        user_input = input("You: ").rstrip()
        trace.append(("User", user_input))
        memory.append({"role": "user", "content": user_input})
        
        if user_input == "/quit":
                print("Thank you for using DjenkGPT! Goodbye!")
                break
            
        current_user_info = generate_user_info(user_input)
        user_info = update_user_info(current_user_info, user_info)
        
        intent = classify_intent(user_input)
        trace.append(("System", f"Classified Intent: {intent}"))
        intent_prompt = get_intent_prompt(intent)
        
        response = generate_response(user_input, intent_prompt, memory, user_info)
        
        if intent.lower() == "custom tools": # allow single tool call per user message                
            tool = tools.detect_tool_call(response)
            if tool:
                tool_response = tools.process_tool_call(tool[0], tool[1])
                user_input += f"\n\nTool Result: {tool_response['result']}"
                response = generate_response(user_input, intent_prompt, memory, user_info)
                trace.append(("Tool", f"Called Tool: {tool_response['tool_name']} with Result: {tool_response['result']}"))
                
        trace.append(("Assistant", response))
        memory.append({"role": "assistant", "content": response})
        print(f"Assistant: {response}\n")
    for role, content in trace:
        print(f"{role}: {content}\n") 
    
        
if __name__ == "__main__":
    gpt()