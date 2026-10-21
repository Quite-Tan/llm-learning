class MiniRepl:
    def __init__(self):
        self.history = []
        self.echo = True

    def run(self):
        print("MiniREPL 启动。输入 /help 查看帮助。\n")
        while True:
            try:
                text = input(">>> ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not text:
                continue
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if cmd == "/quit":
                break
            elif cmd == "/help":
                print("/echo on|off  切换回显\n/history      查看历史\n/quit         退出")
            elif cmd == "/history":
                for i, h in enumerate(self.history, 1):
                    print(f"  {i}. {h}")
            elif cmd == "/echo" and args:
                self.echo = args.lower() == "on"
                print(f"回显已{'开启' if self.echo else '关闭'}")
            else:
                self.history.append(text)
                if self.echo:
                    print(f"[{len(self.history)}] {text}")
        print(f"\n再见！本次共 {len(self.history)} 条输入。")


if __name__ == "__main__":
    MiniRepl().run()