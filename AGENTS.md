## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Active product scope

The official product is the Streamlit application at `dashboard/app.py`.

Read `PROJECT_MASTER_CONTEXT.md` and `ACTIVE_WORKSPACE.md` before broad repository work.

Default active scope:
- `dashboard/`
- `shared/`
- `sync/`
- `supabase/`
- `tests/`

Do not search, analyze, modify, or use `archive/` unless the user explicitly requests historical material.

Also avoid raw exploration of `.next/`, `node_modules/`, `.vercel/`, `.netlify/`, and `graphify-out/`. Query Graphify instead of reading its generated output broadly.

Next.js, React, and Vercel are not current implementations. If Vercel is reconsidered in the future, build it from scratch and recover only explicitly selected business rules or UX decisions.
