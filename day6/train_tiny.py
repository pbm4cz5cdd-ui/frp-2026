"""Train your own tiny language model, letter by letter, on your own computer (FRP 2026, Day 6).

    python train_tiny.py abai.txt                  # 3 minutes, then it writes a text
    python train_tiny.py my_songs.txt --minutes 5  # your own text: any .txt file, at least 50 KB is best
    python train_tiny.py abai.txt --write "Мен"    # use the saved model again: it continues your start

It is the same kind of model as ChatGPT (a transformer), only about 100,000 times smaller. It learns one thing:
guess the next letter. Every 20 seconds it shows what it can write now. Watch the "loss" go down: lower = better.
"""
import argparse, math, os, time
from collections import Counter
import torch, torch.nn as nn, torch.nn.functional as F

ap = argparse.ArgumentParser()
ap.add_argument("data", help="a .txt file to learn from")
ap.add_argument("--minutes", type=float, default=3.0)
ap.add_argument("--write", help="do not train: load the saved model and continue this text")
ap.add_argument("--start", default="", help="the first letters of every sample (default: a random line start)")
a = ap.parse_args()

torch.manual_seed(0)
SAVE = os.path.splitext(a.data)[0] + "_model.pt"

from tiny_model import BATCH, CONTEXT, TinyGPT, write  # the model itself: tiny_model.py

if a.write:                                   # use a model you trained before
    saved = torch.load(SAVE)
    model = TinyGPT(len(saved["letters"])); model.load_state_dict(saved["model"]); model.eval()
    print(write(model, saved["letters"], a.write, n=400))
    raise SystemExit

text = open(a.data, encoding="utf-8").read()
letters = sorted(c for c, n in Counter(text).items() if n >= 5)          # the alphabet of YOUR text
data = torch.tensor([letters.index(c) for c in text if c in letters])
split = int(len(data) * 0.95)
train, test = data[:split], data[split:]                                  # 5 % is kept for the test
model = TinyGPT(len(letters))
opt = torch.optim.AdamW(model.parameters(), lr=2e-3)
print(f"text: {len(text):,} letters, alphabet: {len(letters)} letters, "
      f"model: {sum(p.numel() for p in model.parameters()):,} numbers to learn, time: {a.minutes} min\n")


def batch(d):
    i = torch.randint(len(d) - CONTEXT - 1, (BATCH,))
    return torch.stack([d[j:j + CONTEXT] for j in i]), torch.stack([d[j + 1:j + CONTEXT + 1] for j in i])


def start_text():
    return a.start or "\n"


t0, step, shown = time.time(), 0, -1
while True:
    elapsed = time.time() - t0
    if int(elapsed // 20) > shown or elapsed > a.minutes * 60:            # every 20 seconds: a test and a sample
        shown = int(elapsed // 20)
        model.eval()
        with torch.no_grad():                                             # the test: 5 batches of text it never saw
            test_loss = sum(F.cross_entropy(model(x).view(-1, len(letters)), y.view(-1)).item()
                            for x, y in (batch(test) for _ in range(5))) / 5
        sample = write(model, letters, start_text(), n=120).replace("\n", " / ")
        print(f"{int(elapsed) // 60}:{int(elapsed) % 60:02d}  step {step:5d}  loss {test_loss:.2f}  writes: {sample[:110]}")
        model.train()
        if elapsed > a.minutes * 60:
            break
    lr = 2e-3 * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1, elapsed / (a.minutes * 60)))))
    for g in opt.param_groups: g["lr"] = lr
    x, y = batch(train)
    loss = F.cross_entropy(model(x).view(-1, len(letters)), y.view(-1))  # how wrong were the guesses?
    opt.zero_grad(); loss.backward(); opt.step()                         # turn every knob a tiny bit
    step += 1

model.eval()
torch.save({"model": model.state_dict(), "letters": letters}, SAVE)
print(f"\nSaved: {SAVE}\n\nA longer text from your model:\n")
print(write(model, letters, start_text(), n=500))
