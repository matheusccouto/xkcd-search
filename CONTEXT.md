# xkcd-search

Semantic search over the xkcd archive, reachable two ways: people use a web app, agents use the MCP endpoint.
A nightly-built corpus of every comic plus its explainxkcd article powers a single search tool.

## Language

**Comic**:
A single xkcd strip, identified by its `number`, with a `title`, `url`, `image_url`, `alt_text`, `transcript`, and `explanation`.
_Avoid_: result, hit, entry

**Comic card**:
A comic rendered in the search app: the image, the title, the number, a link to the comic's `url`, and the alt text as a caption. The `url` link is what carries attribution.
_Avoid_: result tile, thumbnail

**Query**:
The natural-language text a person enters to search the corpus.
_Avoid_: prompt, question

**Semantic search**:
Retrieval ranked by meaning relevance over the corpus, not by keyword match; exposed as the `search_xkcd` tool.
_Avoid_: keyword search, fuzzy match

**Top-K**:
The number of comics returned for a query (default 5, maximum 20).
_Avoid_: limit, result count

**Corpus**:
Everything indexed for search: each comic's title, transcript, and the text of its explainxkcd article.
_Avoid_: database, index

**The search app**:
The human-facing surface of the search: a web page where a person enters a query and browses comic cards.
_Avoid_: frontend, dashboard

**MCP endpoint**:
The machine-facing surface at `/mcp` where MCP clients call the search tool.
_Avoid_: API, server

**Eval set**:
A committed list of `(query, expected comic)` pairs used to measure retrieval quality; generated once from sampled comics' explanations and stored as `eval_set.json`.
_Avoid_: benchmark, test data

**Expected comic**:
The comic an eval-set query is written to retrieve; the ground truth the eval checks for.
_Avoid_: gold answer, answer

**hit@k**:
The fraction of eval-set queries whose expected comic appears in the top-k results; reported at k=1 and k=5.
_Avoid_: recall@k

**MRR**:
Mean reciprocal rank of the expected comic across the eval set; a higher-first placement is better even when the comic is not in the top-k.
_Avoid_: average rank
