from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()
client = AzureOpenAI()

messages = [{"role": "user", "content": "Hi"}]
print(f'User: {messages[0]["content"]}')
response = client.chat.completions.create(model="gpt-35-turbo-16k", messages=messages)
print(f"LLM: {response.choices[0].message.content}")
