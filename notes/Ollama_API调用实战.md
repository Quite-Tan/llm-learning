\# Ollama API 调用实战笔记

\## 一、Ollama 提供两套接口

Ollama 启动后，默认服务地址是：

```text

http://localhost:11434

```

它主要提供两类接口：

| 接口类型 | 地址 | 适用场景 |

| ------ |------ |------ |

| 原生 API | `http://localhost:11434/api/chat` | 学习 Ollama 自身机制 |

| OpenAI 兼容接口 | `http://localhost:11434/v1` | 复用现有 OpenAI 代码 |

如果只是本地实验，用 \*\*原生 API\** 即可；如果以后想把代码迁移到云端模型，用 \*\*OpenAI 兼容接口\** 会更方便，因为只需要改 `base\_url`。

\## 二、方式一：使用 Ollama 官方 Python 库

先安装：

```powershell

pip install ollama

```

基础调用：

```python

import ollama



response = ollama.chat(

&#x20;   model="qwen3:8b",

&#x20;   messages=\[{"role": "user", "content": "你好"}]

)



print(response\["message"]\["content"])

```

流式输出：

```python

import ollama



stream = ollama.chat(

&#x20;   model="qwen3:8b",

&#x20;   messages=\[{"role": "user", "content": "写一首短诗"}],

&#x20;   stream=True

)



for chunk in stream:

&#x20;   print(chunk\["message"]\["content"], end="", flush=True)

```

带参数调用：

```python

response = ollama.chat(

&#x20;   model="qwen3:8b",

&#x20;   messages=\[{"role": "user", "content": "解释什么是 RAG"}],

&#x20;   options={

&#x20;       "temperature": 0.5,

&#x20;       "top\_p": 0.9,

&#x20;       "num\_predict": 512

&#x20;   }

)



print(response\["message"]\["content"])

```

\## 三、方式二：使用 OpenAI 兼容接口

先安装：

```powershell

pip install openai

```

调用示例：

```python

from openai import OpenAI



client = OpenAI(

&#x20;   base\_url="http://localhost:11434/v1",

&#x20;   api\_key="ollama"

)



response = client.chat.completions.create(

&#x20;   model="qwen3:8b",

&#x20;   messages=\[

&#x20;       {"role": "system", "content": "你是本地运行的大模型助手。"},

&#x20;       {"role": "user", "content": "用三句话介绍 Agent"}

&#x20;   ],

&#x20;   temperature=0.5,

&#x20;   max\_tokens=512

)



print(response.choices\[0].message.content)

```

注意：`api\_key` 填任意非空字符串即可，Ollama 不会真正校验。

\## 四、方式三：使用 requests 原生 HTTP 调用

先安装：

```powershell

pip install requests

```

调用示例：

```python

import requests



url = "http://localhost:11434/api/chat"



payload = {

&#x20;   "model": "qwen3:8b",

&#x20;   "messages": \[{"role": "user", "content": "你好"}],

&#x20;   "stream": False

}



response = requests.post(url, json=payload)

print(response.json()\["message"]\["content"])

```

这种方式最底层，适合理解 HTTP 请求结构，也方便后续集成到非 Python 项目中。

\## 五、常用模型管理命令

```powershell

ollama list              # 查看本地已有模型

ollama pull qwen3:8b     # 下载模型

ollama rm qwen3:8b       # 删除模型

ollama ps                # 查看正在运行的模型

```

也可以通过 API 查看：

```powershell

curl http://localhost:11434/api/tags

```

\## 六、调用方式选择建议

| 方式 | 推荐场景 |

| ------ |------ |

| `ollama` 官方库 | 日常开发、脚本实验 |

| OpenAI 兼容接口 | 已有 OpenAI 代码迁移到本地 |

| `requests` 原生调用 | 学习 API 原理、跨语言集成 |

| LangChain / LlamaIndex | 后续做 RAG、Agent 时使用 |

\## 七、后续可以继续补充

\- 流式输出在前端/终端中的展示方式

\- 多轮对话上下文维护

\- 嵌入向量 API，为 RAG 做准备

\- 工具调用 / Function Calling 实验

\- 自定义 Modelfile 和系统提示词

\---

这篇可以保存为：

```powershell

notes\\Ollama\_API调用实战.md

```

然后提交：

```powershell

git add .

git commit -m "添加 Ollama API 调用实战笔记"

git push

```

2026-10-09：llama3.2:3b 调用成功。踩坑：Ollama 服务已在后台运行，强制指定地址（绕过 localhost 解析）
有些机器 localhost 会解析成 IPv6 的 ::1，而 Ollama 只监听 127.0.0.1。改代码增加：
import os
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"
