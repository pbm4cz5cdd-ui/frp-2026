# Day 6: train your own tiny model

## 1. Train it (3 minutes)

```
cd ~/work/day6
python3 train_tiny.py abai.txt
```

In 3 minutes the model learns to write like Abai. Every 20 seconds it shows what it can write now.
Watch the **loss**: lower = better guesses.

## 2. Practise with a score (2 minutes each)

```
python3 rl_tiny.py abai.txt
python3 rl_tiny.py abai.txt --stay 0.5
```

The score is how many times the word "сөз" is in the text. The first run shows what happens when the score is
the only thing that counts. The second run also loses points when it moves far from the old model.
Your own word: `--word "жүрек"`. Your own score: change `reward()` in `rl_tiny.py`.

## Texts

| Text | What it is |
|---|---|
| `abai.txt` | 134 poems by Abai Qunanbaiuly (public domain, from Wikisource) |
| `kk_wiki.txt` | Kazakh Wikipedia, 2 MB (CC BY-SA 4.0) |
| `shakespeare.txt` | plays by Shakespeare (public domain) |
| your own `.txt` | song lyrics, a book, your chats: 50 KB or more is best |

## More experiments (at home): change one thing, then compare the loss

- Predict first, then test: does a bigger brain give a lower loss? In `tiny_model.py`: `WIDTH = 64` or `WIDTH = 192`.
- `--minutes 6`: more practice.
- Another text: same model, different "life".
- `python3 train_tiny.py abai.txt --write "Мен"`: your saved model continues your start.
