---
title: hub vault
type: hub-command
tags:
  - hub
---

# `./hub vault`

Regenerates the Obsidian-ready experiment notes in `docs/experiments/` — one per
catalogued run, with YAML frontmatter, tags, and `[[wikilinks]]` to its [[scGen]]/
[[IMPACT_CellOT]] sibling and the concept notes it exemplifies. These are what make the
graph self-assemble.

```bash
./hub vault                       # write all notes + _experiments_index.md
./hub vault --out-dir <dir>       # override output dir
```

## How it differs from `./hub card`

| | `card` | `vault` |
|---|---|---|
| Output | `docs/model_cards/` | `docs/experiments/` |
| Git | **gitignored** (HPC-only) | **tracked** (syncs to the Mac) |
| Figures | absolute-path image embeds | none (would break on the Mac) |
| Links | standard `[label](file.md)` | `[[wikilinks]]` + tags + frontmatter |
| For | reading in Cursor on the HPC | the Obsidian graph |

## The loop

Run after new evals + [[hub metrics]], then `git push`; on the Mac `git pull` and the
graph + [[Dataview]] tables refresh. **Don't hand-edit** `experiments/*.md` — your edits
are overwritten. Put prose in [[Concepts MOC|concepts]] / [[Hub Operations MOC|hub]].

## Next / related

- Setup: [[obsidian_setup]]
- Dashboards it populates: [[Hub Experiments MOC]]
- Back to: [[Hub Operations MOC]]
