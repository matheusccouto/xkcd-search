# xkcd Search

Semantic search engine over xkcd comics and community explanations, queryable by humans, AI agents, and MCP clients.

## Language

**Comic**:
An xkcd comic strip identified by its canonical publication number, title, image, and alt text.
_Avoid_: Strip, episode, post, item

**Alt Text**:
The secondary punchline or author commentary authored by Randall Munroe displayed as tooltip text on a comic image.
_Avoid_: Title text, tooltip, hover caption

**Transcript**:
The verbatim text of scene descriptions, character dialogue, and visual content inside a comic strip.
_Avoid_: Script, dialogue, OCR text

**Explanation**:
The community-authored breakdown from explainxkcd describing the humor, scientific background, and cultural references of a comic.
_Avoid_: Summary, notes, review, interpretation

**Chunk**:
A discrete semantic text unit representing either a comic's metadata or a subsection of its explanation, paired with a vector embedding.
_Avoid_: Fragment, segment, passage, split

**Search Result**:
A deduplicated comic match returned with relevance ranking, metadata, and attribution link.
_Avoid_: Hit, candidate, record, entry

