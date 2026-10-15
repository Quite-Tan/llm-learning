class MiniChat:
    shared_log = []          # 类属性：所有实例共用一份（反面教材）

    def __init__(self, name, model="llama3.2:3a"):
        self.name = name
        self.model = model
        self.logs = []       # 实例属性：各自独立

    def send(self, msg):
        self.logs.append({"role": "user", "content": msg})
        reply = f"收到：{msg}"
        self.logs.append({"role": "assistant", "content": reply})
        MiniChat.shared_log.append(f"{self.name}: {msg}")   # 注意这里
        print(f"[{self.model}] {reply}")

    def clear(self):
        self.logs.clear()
        print("[历史已清空]")

    def show(self):
        print(f"{self.name} | {self.model} | {len(self.logs)} 条消息")


def main():
    name = input("给你的助手起个名字> ").strip() or "bot"
    chat = MiniChat(name)
    print(f"[{name}] 已启动，模型 {chat.model}\n")

    while True:
        try:
            text = input("你> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！"); break
        if not text:
            continue
        if text == "/quit":
            print("再见！"); break
        elif text == "/clear":
            chat.clear()
        elif text == "/show":
            chat.show()
        else:
            chat.send(text)

    # 验证环节
    c2 = MiniChat("bob")
    c2.send("hi")
    print("\n--- 验证坑 ---")
    print("alice 的 logs:", chat.logs)
    print("bob 的 logs  :", c2.logs)
    print("shared_log   :", MiniChat.shared_log)   # 两个人的都在这


if __name__ == "__main__":
    main()