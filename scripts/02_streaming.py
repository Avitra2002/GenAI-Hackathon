from utils.llm import CompletionStream, print_stream

if user_input := input("Question: "):
    messages = [{"role": "user", "content": user_input}]

    with CompletionStream(messages) as stream:
        stream.completion = print_stream(stream.response)
