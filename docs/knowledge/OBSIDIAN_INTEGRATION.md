# Obsidian Integration — Setup Guide

> How to connect your Obsidian vault to OWNEX and start searching your
> knowledge from Mission Control.

## Requirements

- An existing Obsidian vault (a local folder with `.md` files). The vault can
  also be created fresh and used only by OWNEX.
- OWNEX backend running (`python run.py` or `uvicorn api.main:app`).

## 1. Connect the vault

Open **Mission Control → Knowledge Vault** (`/knowledge`), type the absolute
path to the vault folder and press **Conectar**.

The connection verifies the path is a valid vault (it must contain at least
one markdown file) and runs an incremental scan. Equivalent API call:

```bash
curl -X POST "http://localhost:8000/api/knowledge/connect?path=/home/usuario/Obsidian/Vault"
```

## 2. What gets indexed

For every markdown file in the vault (recursively):

- **Frontmatter** (YAML) — tags, aliases, custom fields
- **Wikilinks** `[[Note]]` and embed links `![[Asset]]` — used for backlinks
  and the link graph
- **Tags** `#tag` — full-text searchable
- **Headings, checkboxes, body text** — indexed in SQLite FTS5
- **Attachments** — counted (not indexed as notes)

## 3. Search

`GET /api/knowledge/search?q=...` runs a unified hybrid search: exact match,
title, path, alias, tag, wikilink, FTS5 and semantic (local embeddings).
Results include relevance, snippet, tags and last-modified.

For AI prompts use `GET /api/knowledge/context?q=...` — top notes with
fragments, tags and related notes, ready to be injected into a prompt.

## 4. Keep the index fresh

- **Manual**: Knowledge Vault → "Scan incremental" (fast) or "Reindexar"
  (full rebuild).
- **Automatic**: scheduler job `knowledge_sync_daily` runs every day at
  `06:30` (`run_knowledge_sync`: scan + embeddings + health snapshot).

## 5. Vault operations

- **Git**: if the vault is a git repo, `GET /api/knowledge/git/status` shows
  branch and dirty files; `POST /api/knowledge/git/commit` commits (requires
  `authorized=true`, shows pending diff otherwise).
- **Snapshots**: `POST /api/knowledge/snapshots` (authorized) creates a zip
  backup; the list endpoint returns the last 10.
- **Security**: `GET /api/knowledge/security/scan` scans the vault for leaked
  API keys and credentials.

## 6. Disconnect

"Desconectar" clears the configured vault path. The index and snapshots are
preserved — reconnecting the same vault resumes incrementally.

## Notes for the legacy obsidian sync

An older `obsidian_sync` API (`/api/obsidian/*`) still exists for syncing
markdown → JSON copies of notes. The Knowledge Bridge is the preferred path
(vault is the source of truth); do not use both for the same content.
