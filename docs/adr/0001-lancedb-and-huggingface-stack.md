# ADR 0001: Migration to LanceDB and Hugging Face Stack

## Status

Accepted

## Context

The original implementation of `xkcd-search-mcp` relied on:
1. `sqlite-vec` with raw C extensions, virtual tables (`vec0`), manual binary packing of float arrays, and custom SQL join logic.
2. Local PyTorch (`torch` CPU wheels) and `sentence-transformers` for embedding generation, imposing over 2.5 GB of container dependencies.
3. GitHub Releases as the database artifact distribution mechanism, requiring download and temporary file manipulation on boot.
4. Overly defensive code ("AI slop") including silent error swallowing (e.g. booting with an empty index on failure) and unnecessary retry decorators.
5. Limited consumption surfaces: only Gradio Web UI and FastMCP were exposed, leaving AI agents without a simple, unauthenticated REST API or standardized Agent Skill.

## Decisions

### 1. Vector Database: LanceDB with Direct HF Hub Streaming
- Replace SQLite and `sqlite-vec` with **LanceDB**.
- LanceDB natively supports Apache Arrow columnar storage, vector similarity search, and direct connection to Hugging Face Hub datasets via `hf://datasets/<repo>`.
- The production server connects directly to `hf://datasets/couto/xkcd` without requiring manual asset downloads or temporary file management. If this streaming approach encounters performance or rate-limiting bottlenecks in the future, the connection strategy will transition to a local boot-time snapshot cache.

### 2. Embeddings & Inference: BAAI/bge-small-en-v1.5 via HF Serverless Inference
- Use **`BAAI/bge-small-en-v1.5`** (384 dimensions, 33M parameters). It provides excellent retrieval performance on English text, compact vector representations, and warm-cache availability on Hugging Face Serverless Inference.
- Use **`huggingface_hub.InferenceClient`** for query-time vector generation. This eliminates `torch` and `sentence-transformers` from production runtime dependencies, drastically reducing container size and build time.

### 3. Data Hosting & Rebuild Pipeline
- Store the corpus as a Lance dataset in a Hugging Face Dataset repository (`couto/xkcd`).
- The daily incremental rebuild runs on a lightweight GitHub Actions schedule, builds/updates the LanceDB table, uploads it to Hugging Face Datasets, and calls the Hugging Face Spaces restart API.

### 4. Multi-Interface Consumption
Expose unified interfaces from FastMCP:
1. **Gradio UI** at `/` for human browser interaction.
2. **FastMCP Server** at `/mcp` for standard MCP clients (Cursor, Claude Desktop).
3. **Unauthenticated REST API** at `/api/search?q={query}&k={count}` returning clean JSON for any AI agent or external tool without auth overhead.
4. **Agent Skill** at `.agents/skills/xkcd-search/SKILL.md` distributed via `npx skills add matheusccouto/xkcd-search-mcp`.

### 5. Deslopped, Fail-Fast Codebase
- Remove all silent exception swallowing. If the dataset cannot be loaded or inference fails, raise immediately and loudly.
- Eliminate defensive wrappers (`@tenacity.retry`, manual `.tmp` file renames) in favor of idiomatic, direct Python.
- Delete `schema.sql` and manual virtual table definitions.

## Consequences

- **Pros**:
  - Container size drops from >2.5 GB to ~150 MB by eliminating PyTorch.
  - Zero SQL boilerplate or binary vector byte conversions.
  - Standardized consumption for both human users and AI agents (via MCP, REST, and Skill).
  - Data, models, hosting, and inference are centralized on Hugging Face.
- **Cons**:
  - Direct `hf://` streaming depends on Hugging Face Hub range request responsiveness. If rate-limits occur, a fallback to local boot-time cache will be required.
  - Serverless inference introduces ~30-50ms HTTP latency per search query compared to local CPU execution.
