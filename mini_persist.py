import json
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
FILE = DATA_DIR / "tasks.json"


def save_tasks(path, tasks):
    with path.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def load_tasks(path):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        bak = path.with_suffix(".bak")
        path.rename(bak)
        print(f"[警告] 存档损坏，已备份为 {bak.name}，从空清单开始。")
        return []


def main():
    tasks = load_tasks(FILE)
    print(f"已载入 {len(tasks)} 条待办\n")

    while True:
        try:
            cmd = input("todo> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not cmd:
            continue

        parts = cmd.split(maxsplit=1)
        op = parts[0].lower()

        if op == "quit":
            break
        elif op == "list":
            if not tasks:
                print("（空）")
            for i, t in enumerate(tasks, 1):
                mark = "✔" if t.get("done") else " "
                print(f"  [{mark}] {i}. {t['title']}")
        elif op == "add" and len(parts) > 1:
            tasks.append({"id": len(tasks) + 1, "title": parts[1], "done": False})
            print(f"已添加：{parts[1]}")
        elif op == "done" and len(parts) > 1:
            try:
                idx = int(parts[1]) - 1
                tasks[idx]["done"] = True
                print(f"已完成：{tasks[idx]['title']}")
            except (ValueError, IndexError):
                print("无效的序号")
        else:
            print("用法：list / add <内容> / done <序号> / quit")

        print()

    save_tasks(FILE, tasks)
    print("已保存，再见！")


if __name__ == "__main__":
    main()