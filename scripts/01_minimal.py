from utils.llm import get_completion

if user_input := input("Question: "):
    messages = [{"role": "user", "content": user_input}]

    response = get_completion(messages)
    print(f"Answer: {response.choices[0].message.content}")
