# Eval set generation

`eval_set.json` at the repo root is a committed, seed-deterministic retrieval
eval set: 40 `(query, expected comic)` pairs, each query paraphrased from its
comic's explainxkcd explanation. This document records exactly how the set was
generated so it can be regenerated as the corpus grows.

## How it was generated

The set was generated once by running the pinned `opencode run` command with the
deepseek v4 flash model against the local index. The model sampled 40 comics
from the index with a fixed seed, read each comic's explanation, and wrote one
paraphrased query per comic. A deterministic seed makes the sample — not the
wording — reproducible; queries are model output and are expected to differ on
regeneration.

### Exact command

Run from the repo root, with the local index at `~/.cache/xkcd-search/index.sqlite`:

```bash
opencode run --model opencode-go/deepseek-v4-flash \
  --dir "$(pwd)" \
  "$(cat docs/evals/generation-prompt.md)"
```

`--model opencode-go/deepseek-v4-flash` pins the model. The prompt is
`docs/evals/generation-prompt.md`, which is the committed generation prompt.
The prompt itself embeds the sampling snippet, including the seed
(`SEED = 20260809` in `random.Random(SEED)`). The local index must be a
current full build: every comic in the index has an explanation
(`explained_at IS NOT NULL`), so all 40 sampled comics exist at generation time.

### Seed

The seed is `20260809`, fixed inside the prompt's sampling snippet. The sampled
comic numbers are:

```
117, 168, 286, 369, 403, 428, 495, 638, 721, 791, 843, 858, 869, 873,
981, 997, 1081, 1145, 1290, 1341, 1431, 1450, 1460, 1464, 1485, 1559,
1591, 1718, 2011, 2026, 2030, 2095, 2133, 2143, 2148, 2170, 2487, 3112,
3120, 3246
```

### Generation-time conditions

- Index: `~/.cache/xkcd-search/index.sqlite`, a full build of 3281 comics, all
  with explanations.
- Corpus snapshot: latest xkcd plus explainxkcd as of the 2026-08-09 nightly
  release asset.

## Constraints the generation prompt enforces

- **Paraphrase, don't quote**: every query must be a paraphrase of its comic's
  explanation and must never quote more than 3 consecutive words verbatim from
  the explanation, title, or transcript.
- **Answerable**: only comics with an explanation are sampled, so every expected
  comic is a valid retrieval target.
- **Shape**: output is exactly `{"queries": [{"query", "expected_number"}]}`,
  one pair per sampled comic, written to `eval_set.json`.

## Verification

After generation the committed set was checked two ways:

1. **Paraphrase rule**: for every query, the longest run of words that also
   appears as a contiguous run in the comic's title + explanation + transcript
   is at most 3. Checked programmatically against the local index; 0
   violations.
2. **Answerability**: `uv run evals --index ~/.cache/xkcd-search/index.sqlite`
   against the committed set, on the generation-time index:

   ```
   hit@1    1.000
   hit@5    1.000
   MRR      1.000
   total    40
   run      40
   skipped  0
   ```

   `skipped = 0` confirms every expected comic exists in the index; every
   expected comic ranks first. These numbers are a snapshot against the
   2026-08-09 corpus — they will drift as the corpus grows and the set is
   regenerated, which is expected.

## Regenerating

1. Build or download a current full index to `~/.cache/xkcd-search/index.sqlite`
   (`uv run python -m xkcd_search.builder`, or fetch the latest
   `index.sqlite` Release asset).
2. Run the exact command above. The committed prompt writes a new
   `eval_set.json`. The seed fixes the sample *for a given index snapshot*:
   the same seed over a grown corpus (more comics with explanations) yields a
   different 40-comic sample, so the set changes as the corpus grows — that is
   the intended regeneration path.
3. Re-run the two checks above; report the resulting metrics.
