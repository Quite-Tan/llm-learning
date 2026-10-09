import os
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"

import ollama

response = ollama.chat(
    model="llama3.2:3b",
    messages=[{"role": "user", "content": "用一句话介绍什么是大语言模型"}]
)
print(response["message"]["content"])
