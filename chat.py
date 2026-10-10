import os
import sys

# 必须在 import ollama 之前设置，否则代理会把请求转走
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

import ollama


# ============ 配置区 ============
DEFAULT_MODEL = "llama3.2:3b"
SYSTEM_PROMPT = "你是一个本地运行的 AI 助手，回答简洁准确。"


class Chat:
    """支持多轮对话、流式输出、切换模型的本地聊天客户端"""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def switch_model(self, model: str):
        """切换模型（不清空历史）"""
        self.model = model
        print(f"[模型已切换为 {model}]\n")

    def clear(self):
        """清空历史，只保留 system prompt"""
        self.history = self.history[:1]
        print("[对话历史已清空]\n")

    def send(self, user_input: str):
        """发送一条消息，流式打印回复"""
        self.history.append({"role": "user", "content": user_input})

        try:
            stream = ollama.chat(
                model=self.model,
                messages=self.history,
                stream=True,
                options={
                    "temperature": 0.6,
                    "top_p": 0.9,
                },
            )

            print(f"\n[{self.model}] ", end="", flush=True)
            full_reply = ""
            for chunk in stream:
                content = chunk["message"]["content"]
                print(content, end="", flush=True)
                full_reply += content
            print("\n")  # 流式结束后换行

            # 把完整回复记入历史，保证下一轮能接上上下文
            self.history.append({"role": "assistant", "content": full_reply})

        except ConnectionError as e:
            print(f"\n[错误] 连不上 Ollama 服务：{e}")
            print("提示：在终端执行 'ollama serve' 启动服务\n")
            # 连接失败时把刚才那条用户消息撤掉，避免历史错位
            self.history.pop()
        except Exception as e:
            print(f"\n[错误] {type(e).__name__}: {e}\n")
            self.history.pop()

    @staticmethod
    def show_help():
        print("""
可用命令：
  /help          显示此帮助
  /quit, /exit   退出程序
  /clear         清空对话历史
  /model <名字>  切换模型，例如 /model qwen3:8b
  /history       查看当前消息轮数
""")


def main():
    chat = Chat()
    print(f"本地模型对话已就绪，当前模型：{chat.model}")
    print("输入 /help 查看命令，输入 /quit 退出\n")

    while True:
        try:
            user_input = input("你> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if not user_input:
            continue

        # 处理命令
        lower = user_input.lower()
        if lower in ("/quit", "/exit"):
            print("再见！")
            break
        elif lower == "/help":
            Chat.show_help()
            continue
        elif lower == "/clear":
            chat.clear()
            continue
        elif lower == "/history":
            print(f"当前共 {len(chat.history)} 条消息（含 system）\n")
            continue
        elif lower.startswith("/model "):
            chat.switch_model(user_input.split(maxsplit=1)[1])
            continue
        elif lower.startswith("/"):
            print(f"未知命令：{user_input}，输入 /help 查看帮助\n")
            continue

        # 正常对话
        chat.send(user_input)


if __name__ == "__main__":
    main()