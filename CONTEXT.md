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
