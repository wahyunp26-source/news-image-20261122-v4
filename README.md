# Sunday 22 November 2026 — The World in One Day

[![make.fun](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/c/news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/wahyunp26-source/news-image-20261122-v4/rank.svg)](https://make.fun/c/news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/wahyunp26-source/news-image-20261122-v4/reward.svg)](https://make.fun/c/news-image-20261122)

A one-page newspaper front page summing up **Sunday 22 November 2026** in a
single image: **35 stories**, each dated to that day and each naming its
outlet — COP31 closing in on a final deal, Russia's 400-drone barrage on
Ukraine, Iran striking US bases in Bahrain, and 32 more, from the Gulf of
Finland to Las Vegas.

## How it is made

`main.py` is a single self-contained Python program (standard library only —
no Pillow, no network at runtime). It draws the whole page pixel by pixel:
a gradient COP31 hall with a globe and delegates, a night barrage over Kyiv,
a sunset refinery in Bahrain, ten smaller illustrated scenes, a dotted world
map with numbered pins, a stat strip, a region bar, and a DATE CHECK box
that names the big stories deliberately left out because they happened on
other days.

Serif type is rendered from system fonts at build time into embedded 1-bit
font blobs inside `main.py`, so the entry stays stdlib-only and fully
deterministic: two runs produce byte-identical output.

## Run it

```sh
python3 main.py   # writes entry.png (1024x1024)
```

## Entry

- Competition: [Sum up 22 November's world news in one image](https://make.fun/c/news-image-20261122) (make.fun, $100, top 50)
- Output: `entry.png` (1024x1024, 95,577 bytes)
