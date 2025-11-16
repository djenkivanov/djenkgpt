import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Tuple, List
import prompts
import tools

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
model = "gpt-4.1"

# FLOW: USER INPUT -> INTENT CLASSIFICATION -> INTENT-SPECIFIC PROMPT -> RESPONSE 


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


def generate_response(user_input: str, intent_prompt: str) -> str:
    """
    Generates a response based on user input and the intent-specific prompt.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": intent_prompt},
            {"role": "user", "content": user_input},
        ],
        max_tokens=500,
        temperature=0.7,
    )
    return response.choices[0].message.content.rstrip()


def gpt():
    trace: List[Tuple[str, str]] = []
    print("Welcome to DjenkGPT! How can I assist you today?")
    while True:
        user_input = input("You: ").rstrip()
        trace.append(("User", user_input))
        if user_input == "/quit":
                print("Thank you for using DjenkGPT! Goodbye!")
                break
        for iteration in range(2): # allow single tool call per user message
            if iteration == 0:
                intent = classify_intent(user_input)
                trace.append(("System", f"Classified Intent: {intent}"))
            intent_prompt = get_intent_prompt(intent)
            if intent.lower() == "custom tools" and iteration == 0:
                response = generate_response(user_input, intent_prompt)
                tool = tools.detect_tool_call(response)
                if tool:
                    tool_response = tools.process_tool_call(tool[0], tool[1])
                    user_input += f"\n\nTool Result: {tool_response['result']}"
                    trace.append(("Tool", f"Called Tool: {tool_response['tool_name']} with Result: {tool_response['result']}"))
                    continue
            response = generate_response(user_input, intent_prompt)
            trace.append(("Assistant", response))
            print(f"Assistant: {response}\n")
            break
    for role, content in trace:
        print(f"{role}: {content}") 
    
        
if __name__ == "__main__":
    gpt()