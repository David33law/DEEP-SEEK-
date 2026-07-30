#!/usr/bin/env python3
"""Talk to DeepSeek interactively from the terminal — a real back-and-forth conversation.

    python deepseek_chat.py                        # plain chat (asks for your key, then start)
    python deepseek_chat.py --context goal.md      # load a file as background it should know
    python deepseek_chat.py --model deepseek-reasoner   # deeper (pricier) model

Type your message and press Enter. It keeps the WHOLE conversation, so it remembers what you
said (that is all "talking to an LLM over API" is: you resend the growing list of messages each
turn). Commands:  /exit  /reset  /save <file>  /system <text>  /cost

DeepSeek API model names:  deepseek-chat (the V3 chat model) · deepseek-reasoner (the R1 reasoning
model). Only the Python standard library is used.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

PRICE = {"deepseek-reasoner": (0.55, 2.19), "deepseek-chat": (0.27, 1.10)}   # EUR per 1M tok (est.)


def ask_key():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        try:
            key = input("Επικόλλησε το DeepSeek API key σου (ξεκινά με sk-) και πάτα Enter: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit("\nΑκυρώθηκε.")
    key = (key or "").strip()
    if not key or key.endswith("...") or key == "sk-...":
        sys.exit("Δεν δόθηκε πραγματικό κλειδί. Πάρ' το από https://platform.deepseek.com → API keys.")
    return key


def send(endpoint, model, key, messages, max_tokens, timeout):
    body = {"model": model, "messages": messages, "temperature": 0.3, "max_tokens": max_tokens}
    req = urllib.request.Request(
        endpoint, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        obj = json.loads(r.read().decode("utf-8"))
    return obj["choices"][0]["message"].get("content") or "", obj.get("usage", {})


def main():
    ap = argparse.ArgumentParser(description="Interactive DeepSeek chat over the API")
    ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--endpoint",
                    default=os.environ.get("DEEPSEEK_ENDPOINT", "https://api.deepseek.com/chat/completions"))
    ap.add_argument("--system", default=None, help="an initial system instruction")
    ap.add_argument("--context", default=None, help="a file whose content is given as background")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args()

    key = ask_key()
    pin, pout = PRICE.get(a.model, PRICE["deepseek-chat"])
    messages, spent = [], 0.0

    if a.system:
        messages.append({"role": "system", "content": a.system})
    if a.context:
        try:
            with open(a.context, "r", encoding="utf-8", errors="replace") as f:
                ctx = f.read()
        except OSError as e:
            sys.exit(f"could not read --context: {e}")
        messages.append({"role": "system",
                         "content": f"Background the user may refer to (from {a.context}):\n\n{ctx}"})
        print(f"[loaded {len(ctx):,} chars of context from {a.context} — note: it is resent each turn]")

    print(f"\nΣυνομιλία με {a.model}. Γράψε μήνυμα + Enter. Εντολές: /exit /reset /save <file> /cost\n")
    while True:
        try:
            user = input("Εσύ ▶ ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user == "/exit":
            break
        if user == "/reset":
            messages = [m for m in messages if m["role"] == "system"]
            print("[history cleared, context kept]")
            continue
        if user == "/cost":
            print(f"[σύνολο μέχρι τώρα ≈ €{spent:.4f}]")
            continue
        if user.startswith("/save"):
            path = (user.split(None, 1) + ["deepseek-conversation.md"])[1]
            with open(path, "w", encoding="utf-8") as f:
                for m in messages:
                    f.write(f"### {m['role']}\n{m['content']}\n\n")
            print(f"[saved → {path}]")
            continue
        if user.startswith("/system "):
            messages = [{"role": "system", "content": user[8:]}] + [m for m in messages if m["role"] != "system"]
            print("[system instruction set]")
            continue

        messages.append({"role": "user", "content": user})
        try:
            reply, usage = send(a.endpoint, a.model, key, messages, a.max_tokens, a.timeout)
        except urllib.error.HTTPError as e:
            print(f"[HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}]")
            messages.pop()
            continue
        except urllib.error.URLError as e:
            print(f"[network error: {e.reason}]")
            messages.pop()
            continue
        messages.append({"role": "assistant", "content": reply})
        turn = usage.get("prompt_tokens", 0) / 1e6 * pin + usage.get("completion_tokens", 0) / 1e6 * pout
        spent += turn
        print(f"\nDeepSeek ▶ {reply}\n[αυτή η απάντηση ≈ €{turn:.4f} · σύνολο ≈ €{spent:.4f}]\n")

    print(f"Τέλος. Συνολικό κόστος συνομιλίας ≈ €{spent:.4f}")


if __name__ == "__main__":
    main()
