import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Tuple, List
import prompts

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
    prompt = f'{intent.upper()}_SYSTEM_PROMPT'
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
        intent = classify_intent(user_input)
        trace.append(("System", f"Classified Intent: {intent}"))
        intent_prompt = get_intent_prompt(intent)
        response = generate_response(user_input, intent_prompt)
        trace.append(("Assistant", response))
        print(f"Assistant: {response}\n")
    for role, content in trace:
        print(f"{role}: {content}\n\n") 
    
        
if __name__ == "__main__":
    gpt()