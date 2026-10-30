"""Practice with a score: teach YOUR trained tiny model with a reward (FRP 2026, Day 6). The same idea as GRPO.

    python3 rl_tiny.py abai.txt                    # uses abai_model.pt from train_tiny.py, 3 minutes
    python3 rl_tiny.py abai.txt --word "жүрек"     # reward: how often the line has this word

Every round: the model writes 16 short texts. Each text gets a score (the reward below). Texts better than the
group average become more likely, worse ones less likely. Nobody shows it a good text: only the score.
Change the reward() function to teach it something else. Watch out: it learns exactly what you score, not what
you mean.
"""
import argparse, os, time
import torch, torch.nn.functional as F
from tiny_model import CONTEXT, TinyGPT, write

ap = argparse.ArgumentParser()
ap.add_argument("data", help="the .txt file you trained on (its model file is used)")
ap.add_argument("--word", default="сөз", help="the reward counts this word")
ap.add_argument("--minutes", type=float, default=2.0)
ap.add_argument("--stay", type=float, default=0.0, help="penalty for moving away from the old model (try 0.05)")
a = ap.parse_args()
SAVE = os.path.splitext(a.data)[0] + "_model.pt"
saved = torch.load(SAVE)
letters = saved["letters"]
model = TinyGPT(len(letters)); model.load_state_dict(saved["model"])
old = TinyGPT(len(letters)); old.load_state_dict(saved["model"]); old.eval()   # the model before practice
opt = torch.optim.Adam(model.parameters(), lr=3e-4)
TRIES, LENGTH = 16, 80


def reward(text):
    """The score of one text. Change me! Now: how many times the word appears."""
    return text.lower().count(a.word)


def sample():
    """16 tries: each writes LENGTH letters after a new line. Returns the letter numbers."""
    idx = torch.full((TRIES, 1), letters.index("\n"))
    with torch.no_grad():
        for _ in range(LENGTH):
            probs = F.softmax(model(idx[:, -CONTEXT:])[:, -1], dim=-1)
            idx = torch.cat([idx, torch.multinomial(probs, 1)], dim=1)
    return idx


print(f"reward: how many times “{a.word}” is in the text" + (f", stay close to the old model: {a.stay}" if a.stay else "") + ". Before practice, the model writes:\n")
print("   " + write(model, letters, "\n", n=LENGTH).replace("\n", " / ") + "\n")
t0, step, shown = time.time(), 0, -1
while time.time() - t0 < a.minutes * 60:
    idx = sample()
    texts = ["".join(letters[i] for i in row[1:].tolist()) for row in idx]
    r = torch.tensor([reward(t) for t in texts], dtype=torch.float)
    logp = F.log_softmax(model(idx[:, :-1]), dim=-1).gather(2, idx[:, 1:, None]).squeeze(2).sum(1)
    score = r.clone()
    if a.stay:                                                # --stay: lose points for texts the old model finds strange
        with torch.no_grad():
            logp_old = F.log_softmax(old(idx[:, :-1]), dim=-1).gather(2, idx[:, 1:, None]).squeeze(2).sum(1)
        score = r - a.stay * (logp.detach() - logp_old)
    adv = (score - score.mean()) / (score.std() + 1e-6)      # better or worse than the group average?
    loss = -(adv * logp).mean()                               # more of the good tries, less of the bad ones
    opt.zero_grad(); loss.backward(); opt.step()
    step += 1
    elapsed = time.time() - t0
    if int(elapsed // 20) > shown:
        shown = int(elapsed // 20)
        best = texts[int(r.argmax())].replace("\n", " / ")
        print(f"{int(elapsed) // 60}:{int(elapsed) % 60:02d}  round {step:4d}  average score {r.mean():.2f}  best: {best[:70]}")

torch.save({"model": model.state_dict(), "letters": letters}, SAVE.replace("_model.pt", "_rl_model.pt"))
print("\nAfter practice, the model writes:\n")
for _ in range(3):
    print("   " + write(model, letters, "\n", n=LENGTH).replace("\n", " / "))
