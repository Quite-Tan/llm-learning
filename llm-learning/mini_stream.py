import time

def word_stream(sentence):
    for ch in sentence:
        yield ch
        time.sleep(0.05)

def stream_print(gen):
    full = ""
    for piece in gen:
        full += piece
        print(piece, end="",flush=True )
    print()
    return full

def main():
    text = "本地大模型的流式输出原理并不神秘"
    result = stream_print(word_stream(text))
    print("完整文本长度：", len(result))
    print("和原句一致吗：", result == text)

if __name__ == "__main__":
    main()