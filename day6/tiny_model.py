"""The tiny language model for the Day 6 workshop (used by train_tiny.py and rl_tiny.py). FRP 2026."""
import os
import torch, torch.nn as nn, torch.nn.functional as F


def cpus():                                   # the CPUs this computer gives us (a container can have fewer)
    try:
        quota, period = open("/sys/fs/cgroup/cpu.max").read().split()
        if quota != "max": return max(1, int(int(quota) / int(period)))
    except OSError:
        pass
    return len(os.sched_getaffinity(0))


torch.set_num_threads(cpus())


LAYERS, HEADS, WIDTH, CONTEXT, BATCH = 4, 4, 128, 128, 32   # the size of the brain: try WIDTH 64 or 192


class Block(nn.Module):                       # one layer: look back at the earlier letters, then think
    def __init__(s):
        super().__init__()
        s.ln1, s.ln2 = nn.LayerNorm(WIDTH), nn.LayerNorm(WIDTH)
        s.qkv, s.proj = nn.Linear(WIDTH, 3 * WIDTH), nn.Linear(WIDTH, WIDTH)
        s.mlp = nn.Sequential(nn.Linear(WIDTH, 4 * WIDTH), nn.GELU(), nn.Linear(4 * WIDTH, WIDTH))

    def forward(s, x):
        b, t, _ = x.shape
        q, k, v = (z.view(b, t, HEADS, -1).transpose(1, 2) for z in s.qkv(s.ln1(x)).split(WIDTH, dim=2))
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(b, t, WIDTH)
        x = x + s.proj(y)
        return x + s.mlp(s.ln2(x))


class TinyGPT(nn.Module):
    def __init__(s, n_letters):
        super().__init__()
        s.letter, s.place = nn.Embedding(n_letters, WIDTH), nn.Embedding(CONTEXT, WIDTH)
        s.blocks = nn.Sequential(*[Block() for _ in range(LAYERS)])
        s.ln, s.out = nn.LayerNorm(WIDTH), nn.Linear(WIDTH, n_letters)

    def forward(s, idx):                      # letters in -> a score for every possible next letter
        x = s.letter(idx) + s.place(torch.arange(idx.shape[1]))
        return s.out(s.ln(s.blocks(x)))


def write(model, letters, start, n=200, temperature=0.8):
    idx = torch.tensor([[letters.index(c) for c in start if c in letters] or [0]])
    with torch.no_grad():
        for _ in range(n):
            probs = F.softmax(model(idx[:, -CONTEXT:])[0, -1] / temperature, dim=-1)
            idx = torch.cat([idx, torch.multinomial(probs, 1).view(1, 1)], dim=1)
    return "".join(letters[i] for i in idx[0].tolist())


