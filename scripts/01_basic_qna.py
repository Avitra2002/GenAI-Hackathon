from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()
client = AzureOpenAI()

if user_input := input("Question: "):
    messages = [{"role": "user", "content": user_input}]
    response = client.chat.completions.create(
        model="gpt-35-turbo-16k", messages=messages
    )
    print(f"Answer: {response.choices[0].message.content}\n")
