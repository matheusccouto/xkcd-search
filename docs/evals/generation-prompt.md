# Eval set generation prompt

Generate the committed retrieval eval set for xkcd-search: a list of about 40
`(query, expected comic)` pairs used to measure hit@k and MRR.

You are working in the xkcd-search-mcp repo. The corpus lives in a local SQLite
index at `~/.cache/xkcd-search/index.sqlite` (read-only). You must never modify
it, never rebuild it, and never hit the network. Sample only comics that have an
explanation, so every generated query is answerable.

## 1. Sample 40 comics deterministically

Run this exact snippet (adjust `INDEX` if the local index lives elsewhere):

```bash
uv run python - <<'PY'
import json, random, sqlite3
from pathlib import Path

INDEX = Path.home() / ".cache" / "xkcd-search" / "index.sqlite"
SEED = 20260809

conn = sqlite3.connect(f"file:{INDEX}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT number, title, explanation FROM comics WHERE explained_at IS NOT NULL"
).fetchall()
print("comics with explanation:", len(rows))
assert len(rows) >= 40

rng = random.Random(SEED)
sampled = rng.sample([int(r["number"]) for r in rows], 40)
by_number = {int(r["number"]): r for r in rows}
with open("eval_sample.json", "w") as f:
    json.dump([dict(by_number[n]) for n in sampled], f, indent=2)
print("sampled:", sorted(sampled))
PY
```

This writes `eval_sample.json` in the repo root, a list of 40 dicts, each with
`number`, `title`, and `explanation`. The seed fixes the sample, so the set is
regenerable.

**Never use `/tmp` (it is blocked).** Write any scratch files into the repo
root and delete them before finishing.

## 2. Read each explanation and write one query

`eval_sample.json` holds long explanations that may be truncated when read
directly. First render a friendly, bounded-width copy in the repo root:

```bash
uv run python - <<'PY'
import json, textwrap
from pathlib import Path

with open("eval_sample.json") as f:
    sample = json.load(f)

blocks = []
for s in sample:
    body = textwrap.fill(s["explanation"], width=100) or "(empty explanation)"
    blocks.append(f"===== NUMBER {s['number']} | TITLE: {s['title']} =====\n{body}")
Path("eval_full.md").write_text("\n\n".join(blocks))
print("wrote", len(blocks), "blocks")
PY
```

Then read `eval_full.md`. For each comic, write exactly one query that a
person would type to find that comic. Every query must:

- be **paraphrased from that comic's explanation** — same subject, your own
  words, phrased like a real search (usually 2-8 words);
- **never quote more than 3 consecutive words** verbatim from the explanation,
  title, or transcript — check each query against its source before finalising;
- clearly point at the comic's subject matter, so the expected comic is a strong
  retrieval target (aim for hit@1 on the live index).

The comic's `expected_number` is its `number`.

## 3. Emit the eval set

Write the result to `eval_set.json` at the repo root, in exactly this shape:

```json
{
  "queries": [
    {"query": "...", "expected_number": 3230}
  ]
}
```

Include all 40 pairs. Do not invent fields; do not add comics that were not in
the sample. Then delete `eval_sample.json` and `eval_full.md` from the repo
root, leaving only `eval_set.json` as the new file.

## 4. Report

When done, reply with the list of `expected_number`s you used, so the generation
document can record them.
