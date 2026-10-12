import os
import json
from pathlib import Path
from datetime import datetime

# 必须在 import ollama 之前设置
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

import ollama


# ============ 配置区 ============
DEFAULT_MODEL = "llama3.2:3b"
SYSTEM_PROMPT = "你是一个本地运行的 AI 助手，回答简洁准确。"
SESSION_DIR = Path("sessions")
SESSION_DIR.mkdir(exist_ok=True)
PARAMS_FILE = Path("params.json")
MAX_DOC_CHARS = 8000          # 文档注入的字符上限，防止小模型被撑爆


# ============ 参数管理 ============
class Params:
    """推理参数：temperature / top_p / num_predict / 是否流式"""

    DEFAULTS = {
        "temperature": 0.6,
        "top_p": 0.9,
        "num_predict": 1024,
        "stream": True,
    }

    def __init__(self):
        self.data = dict(self.DEFAULTS)
        self._load()

    def _load(self):
        if PARAMS_FILE.exists():
            try:
                saved = json.load(PARAMS_FILE.open("r", encoding="utf-8"))
                self.data.update({k: v for k, v in saved.items() if k in self.data})
            except Exception:
                pass

    def save(self):
        json.dump(self.data, PARAMS_FILE.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def set(self, key, value):
        if key not in self.DEFAULTS:
            return False, f"未知参数：{key}（可选：{', '.join(self.DEFAULTS.keys())}）"
        try:
            if key == "stream":
                value = value.lower() in ("true", "1", "yes", "on")
            else:
                value = type(self.DEFAULTS[key])(value)
        except ValueError:
            return False, f"值不合法：{value}"
        self.data[key] = value
        self.save()
        return True, f"{key} = {self.data[key]}"

    def show(self):
        lines = ["当前参数（已保存到 params.json）："]
        for k, v in self.data.items():
            lines.append(f"  {k:12s} : {v}")
        return "\n".join(lines)

    def to_ollama_options(self):
        return {k: v for k, v in self.data.items() if k != "stream"}


# ============ 会话持久化 ============
class Session:
    """把对话历史存成 JSON，退出自动保存，启动自动恢复"""

    @staticmethod
    def _path(name: str) -> Path:
        name = name.replace("\\", "").replace("/", "")
        return SESSION_DIR / f"{name}.json"

    @staticmethod
    def save(name: str, model: str, history: list, doc: str = ""):
        p = Session._path(name)
        data = {
            "name": name,
            "model": model,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "history": history,
            "doc_context": doc,
        }
        json.dump(data, p.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return p

    @staticmethod
    def load(name: str):
        p = Session._path(name)
        if not p.exists():
            return None
        data = json.load(p.open("r", encoding="utf-8"))
        # 兜底：旧会话没有 system 消息就补一个
        if not data["history"] or data["history"][0].get("role") != "system":
            data["history"].insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        return data

    @staticmethod
    def list_all():
        files = sorted(SESSION_DIR.glob("*.json"), key=lambda f: -f.stat().st_mtime)
        if not files:
            return "还没有保存的会话。"
        lines = ["已保存的会话："]
        for f in files:
            try:
                d = json.load(f.open("r", encoding="utf-8"))
                lines.append(f"  {d['name']:20s} | {d['model']:15s} | {d['created_at']} | {len(d['history'])} 条消息")
            except Exception:
                lines.append(f"  {f.name}（读取失败）")
        return "\n".join(lines)


# ============ 文档注入（最原始的 RAG）============
class DocContext:
    """读取本地 txt/md 文件，拼进上下文"""

    def __init__(self):
        self.text = ""
        self.filename = ""

    def load(self, path_str: str):
        p = Path(path_str)
        if not p.exists():
            return False, f"文件不存在：{p.absolute()}"
        if p.suffix.lower() not in (".txt", ".md", ".py", ".json", ".csv"):
            return False, "只支持 .txt / .md / .py / .json / .csv"
        try:
            raw = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw = p.read_text(encoding="gbk")      # 兼容 Windows 下的一些中文文件
        if len(raw) > MAX_DOC_CHARS:
            raw = raw[:MAX_DOC_CHARS] + "\n...（内容过长，已截断）"
        self.text = raw.strip()
        self.filename = p.name
        return True, f"已载入 {self.filename}（{len(self.text)} 字符）"

    def clear(self):
        self.text = ""
        self.filename = ""

    def build_message(self):
        if not self.text:
            return None
        return {
            "role": "system",
            "content": (
                "以下是用户提供的参考文档内容，请基于它回答问题；"
                "如果文档里没有相关信息，请明确说明，不要编造。\n\n"
                f"【文档：{self.filename}】\n{self.text}"
            ),
        }


# ============ 主聊天客户端 ============
class Chat:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.params = Params()
        self.doc = DocContext()
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.session_name = "default"

    def _rebuild_history_with_doc(self):
        """文档变化时，保证 system 层顺序正确"""
        base = [h for h in self.history if h["role"] != "system" or h.get("content") == SYSTEM_PROMPT]
        doc_msg = self.doc.build_message()
        return ([{"role": "system", "content": SYSTEM_PROMPT}] + ([doc_msg] if doc_msg else [])
                + [h for h in base if h not in ([{"role": "system", "content": SYSTEM_PROMPT}], )]) 
        # 上面写法偏啰嗦，下面 send() 里用更清晰的版本

    def switch_model(self, model: str):
        self.model = model
        print(f"[模型已切换为 {model}]\n")

    def clear(self):
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        print("[对话历史已清空]\n")

    def send(self, user_input: str):
        # 组装消息：system -> 文档(如果有) -> 历史 -> 新提问
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        doc_msg = self.doc.build_message()
        if doc_msg:
            messages.append(doc_msg)
        messages += [h for h in self.history if h["role"] != "system"]
        messages.append({"role": "user", "content": user_input})

        try:
            if self.params.data["stream"]:
                stream = ollama.chat(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    options=self.params.to_ollama_options(),
                )
                print(f"\n[{self.model}] ", end="", flush=True)
                full_reply = ""
                for chunk in stream:
                    c = chunk["message"]["content"]
                    print(c, end="", flush=True)
                    full_reply += c
                print("\n")
            else:
                resp = ollama.chat(
                    model=self.model,
                    messages=messages,
                    stream=False,
                    options=self.params.to_ollama_options(),
                )
                full_reply = resp["message"]["content"]
                print(f"\n[{self.model}]\n{full_reply}\n")

            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": full_reply})
            Session.save(self.session_name, self.model, self.history, self.doc.text)  # 自动落盘

        except ConnectionError as e:
            print(f"\n[错误] 连不上 Ollama 服务：{e}\n提示：终端执行 ollama serve\n")
        except Exception as e:
            print(f"\n[错误] {type(e).__name__}: {e}\n")

    @staticmethod
    def show_help():
        print("""
对话命令：
  /help                  显示此帮助
  /quit, /exit           退出（自动保存会话）
  /clear                 清空历史
  /model <名字>          切换模型
  /history               查看消息轮数

参数调节：
  /set <参数> <值>        例如 /set temperature 0.9
  /set num_predict 256    控制最长输出
  /set stream off         关闭流式输出
  /params                查看当前参数

会话持久化：
  /save <名字>            保存当前会话
  /load <名字>            加载已有会话
  /sessions              列出所有会话

文档注入（原始 RAG）：
  /doc load <路径>        载入本地 txt/md 文件
  /doc show              显示已载入的文档名和长度
  /doc clear             清除文档上下文
""")


def handle_doc(chat: Chat, args: list[str]):
    if not args:
        print("用法：/doc load <路径> | /doc show | /doc clear\n"); return
    cmd = args[0].lower()
    if cmd == "load" and len(args) >= 2:
        ok, msg = chat.doc.load(" ".join(args[1:]))
        print(msg + "\n")
    elif cmd == "show":
        if chat.doc.text:
            print(f"已载入：{chat.doc.filename}（{len(chat.doc.text)} 字符）\n")
        else:
            print("当前没有载入文档。\n")
    elif cmd == "clear":
        chat.doc.clear(); print("[文档上下文已清除]\n")
    else:
        print("用法：/doc load <路径> | /doc show | /doc clear\n")


def main():
    chat = Chat()
    # 尝试自动恢复上次会话
    default_path = Session._path("default")
    if default_path.exists():
        data = Session.load("default")
        if data:
            chat.history = data["history"]
            chat.model = data.get("model", DEFAULT_MODEL)
            if data.get("doc_context"):
                chat.doc.text = data["doc_context"]
            print(f"已恢复上次会话：{data['name']}（{len(chat.history)} 条消息）\n")

    print(f"本地模型对话已就绪 | 模型：{chat.model}")
    print("输入 /help 查看命令，输入 /quit 退出\n")

    while True:
        try:
            user_input = input("你> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n正在保存会话...")
            Session.save(chat.session_name, chat.model, chat.history, chat.doc.text)
            print("再见！")
            break

        if not user_input:
            continue
        lower = user_input.lower()
        parts = user_input.split()

        if lower in ("/quit", "/exit"):
            Session.save(chat.session_name, chat.model, chat.history, chat.doc.text)
            print("已保存，再见！"); break
        elif lower == "/help":
            Chat.show_help(); continue
        elif lower == "/clear":
            chat.clear(); continue
        elif lower == "/history":
            print(f"当前共 {len(chat.history)} 条消息\n"); continue
        elif lower.startswith("/model "):
            chat.switch_model(parts[1]); continue
        elif lower.startswith("/set ") and len(parts) >= 3:
            ok, msg = chat.params.set(parts[1], " ".join(parts[2:]))
            print(msg + "\n"); continue
        elif lower == "/params":
            print(chat.params.show() + "\n"); continue
        elif lower.startswith("/save "):
            name = parts[1]
            chat.session_name = name
            Session.save(name, chat.model, chat.history, chat.doc.text)
            print(f"已保存到 sessions/{name}.json\n"); continue
        elif lower.startswith("/load "):
            data = Session.load(parts[1])
            if data:
                chat.session_name = data["name"]
                chat.history = data["history"]
                chat.model = data.get("model", chat.model)
                print(f"已加载 {data['name']}（{len(chat.history)} 条消息）\n")
            else:
                print(f"找不到该会话。\n"); continue
        elif lower == "/sessions":
            print(Session.list_all() + "\n"); continue
        elif lower.startswith("/doc "):
            handle_doc(chat, parts[1:]); continue
        elif lower.startswith("/"):
            print(f"未知命令：{parts[0]}，输入 /help 查看帮助\n"); continue

        chat.send(user_input)


if __name__ == "__main__":
    main()