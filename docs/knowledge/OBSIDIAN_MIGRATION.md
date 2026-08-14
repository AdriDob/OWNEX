# Obsidian Migration — Moving your knowledge into the vault

> Guidelines for moving existing knowledge (notes, docs, exports) into an
> Obsidian vault so OWNEX can index it. The vault is the single source of
> truth — migration means *moving files into the vault*, not importing them
> into a database.

## Recommended vault layout

```
vault/
├── 00-Inbox/        # new notes, unprocessed
├── 10-Projects/     # active project notes
├── 20-Areas/        # ongoing areas (bug bounty, dev, learning)
├── 30-Resources/    # reference material
├── 90-Meta/         # templates, index notes
└── _attachments/    # images and assets (embeds ![[asset.png]])
```

OWNEX indexes the whole tree recursively; the exact structure is yours.

## Format requirements

- Plain Markdown (`.md`), UTF-8.
- YAML frontmatter is supported and indexed:

```yaml
---
title: IDOR checklist
tags: [web, idor, checklist]
aliases: [checklist idor]
---
```

- Wikilinks (`[[Note]]`) create the link graph and backlinks.
- Other formats (`.txt`, `.docx`, HTML exports) are **not indexed** — convert
  them to Markdown first.

## Migration paths

### From the legacy obsidian_sync JSON copies

If notes were previously synced via `/api/obsidian/*` (markdown → JSON
copies), the JSON copies are now redundant. Keep the markdown as source:

1. Verify the markdown files exist in the vault.
2. Delete the generated JSON copies (or keep them only as archive).
3. Connect the vault to the Knowledge Bridge and reindex.

### From other tools (Notion, Evernote, Roam, plain folders)

1. Export to Markdown (Notion: "Export → Markdown & CSV"; Evernote:
   enex → md via `yarle`; Roam: "Export → Markdown").
2. Move the exported `.md` files into the vault folders above.
3. Check frontmatter and fix broken wikilinks (use
   `GET /api/knowledge/health` → `broken_links` after reindexing).
4. Run **Reindexar** (full scan) from Knowledge Vault.

### Importing existing personal notes (manual)

If you have notes as JSON/DB entries from other OWNEX modules, convert them
to Markdown files in the vault (one file per note, frontmatter with tags) —
the Knowledge Bridge then makes them searchable through the same API.

## After migration

- `GET /api/knowledge/health` shows notes indexed, broken links, duplicates
  and missing attachments — fix those in the vault (the index reflects the
  vault, not the other way around).
- Duplicates detected by `find_duplicates()` should be merged in the vault
  and re-scanned.
- Set up git in the vault and snapshot before big migrations
  (`POST /api/knowledge/snapshots`).
