# Obsidian vault setup — speciesOT

How to turn this repo's `docs/` folder into a navigable Obsidian knowledge graph on
your Mac, kept in sync with the HPC through GitHub. Written for someone who has
**never used Obsidian, git-across-two-machines, or a knowledge graph** before.

The big picture (read once):

| Layer | Where | What it holds | Who edits |
|---|---|---|---|
| **Factory** | Harvard RC (`/n/holylabs/...`) | data, GPUs, the hub, training/evals (25 GB) | the Cursor agent, SLURM |
| **Reading room** | your M1 Mac | the Obsidian vault = `docs/` (the graph) | you + Cursor |
| **Conveyor belt** | GitHub (your own repo) | only the markdown + code (~280 MB) | `git push` / `git pull` |

The 25 GB of `.h5ad`/results **never moves** — it's gitignored. The Mac only ever
holds text. That's why this is cheap and fast.

---

## 0. One-time decisions already made

- **Vault root = `docs/`** (not a separate repo, not a branch). Obsidian opens this
  one folder; everything in it becomes part of the graph.
- **No `hub` branch.** A branch is the wrong tool for "a synced copy on a second
  machine" — that's just a *clone*. We sync the normal way: push from HPC, pull on Mac.
- **Cursor, not Claude Code.** Your Cursor Ultra plan already does everything the
  blueprint attributes to Claude Code. Claude Code is a *separate* $17–20/mo Anthropic
  subscription; skip it unless you later want the terminal-native flavor for fun.

---

## 1. Make your own GitHub remote (do this once, on the HPC)

The existing `josh` remote is your mentor's repo (`JoshuaPrice/speciesOT`) and is
**diverged — never force-push it**. For two-machine sync you want *your own* repo.

1. On github.com, create a new **private** repo, e.g. `junyizhou/speciesOT` (empty — no
   README/license, to avoid an initial conflict).
2. On the HPC, from the workspace root, add it as a remote called `mine` and push `main`:

   ```bash
   cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
   git remote add mine https://github.com/<your-username>/speciesOT.git
   git add -A && git commit -m "vault: Obsidian scaffold + hub vault command"   # only when you're ready
   git push -u mine main
   ```

   > The repo rule is **no commits/pushes unless you ask**. The agent won't run the
   > commit/push for you unless you say so. The 25 GB of data is gitignored, so the
   > push is small (~280 MB the first time, tiny after).

---

## 2. Install + clone on the Mac (do this once)

1. **Install Obsidian** (free): <https://obsidian.md>. Make sure it's **v1.12.4 or
   newer** (the official CLI shipped in 1.12.4, Feb 2026). Check via
   *Settings → About*; update the *installer* if older.
2. **Clone your repo** somewhere sensible, e.g. `~/code/speciesOT`:

   ```bash
   git clone https://github.com/<your-username>/speciesOT.git ~/code/speciesOT
   ```
3. **Open the vault**: in Obsidian → *Open folder as vault* → choose
   `~/code/speciesOT/docs`. (Pick `docs/`, **not** the repo root — opening the root
   would drag all the code/notebooks into the graph as noise.)
4. Obsidian asks to trust the folder / enable config — say yes.

---

## 3. First look at the graph

- Click the **graph view** icon in the left ribbon (the connected-dots icon), or
  *Cmd-P → "Open graph view"*.
- You'll see nodes (notes) and edges (every `[[wikilink]]`). The experiment notes in
  `experiments/` link to their scGen/IMPACT sibling and to the concept notes they
  exemplify; the concept notes (`concepts/`) interlink into your spider-web.
- In the graph's **Settings (gear)**: turn on **Groups** and add color groups by tag,
  e.g. `tag:#impact_cellot` (one color), `tag:#scgen` (another), `tag:#moc`. Now the
  175 experiments cluster visually by family/flavor.
- **Greyed-out nodes = "unresolved links"** — concept notes referenced but not written
  yet. That's your to-write list; it's a feature, not a bug.

How the graph is built (the demystified version): there is **no build step**. Obsidian
scans every `.md`, turns each into a node, and draws an edge wherever one note contains
`[[Another Note]]`. Tags become colors/filters. That's the whole mechanism — so the
leverage is entirely in *writing links*, which the hub now does automatically for
experiments (`./hub vault`).

---

## 4. Two plugins worth installing (Community plugins)

*Settings → Community plugins → Browse.* (You'll be asked to turn off Restricted Mode.)

1. **Dataview** — reads the YAML frontmatter on every experiment note as a database and
   renders **live tables**. The `Hub Experiments MOC` note already contains Dataview
   queries (e.g. "every IMPACT run sorted by R²", "runs where `frac_gap_closed` < 0").
   Without Dataview those code blocks show as plain text; with it they become tables
   that update whenever you `./hub vault` + pull.
2. **(optional) Templater** — lets the `00-system/templates/` notes auto-fill new
   concept/experiment notes. Nice-to-have, not required.

The built-in **Graph view** and **Properties** (frontmatter editor) need no install.

---

## 5. The official Obsidian CLI (optional, for agent integration)

Obsidian 1.12.4+ ships a real CLI that *remote-controls the running app* (so links and
frontmatter stay valid — unlike scripts that poke `.md` files directly).

- Enable: *Settings → General → Command line interface → Register CLI* (it adds an
  `obsidian` command to your PATH; restart the terminal).
- Try: `obsidian search query="frac_gap_closed"`, `obsidian create name="concepts/My idea"`,
  `obsidian backlinks file="concepts/MMD floor and ceiling"`.
- **Caveat:** it needs the Obsidian *desktop app running*, so it works on the **Mac**,
  not on the headless HPC login node. Cursor's agent on the Mac can call it from the
  integrated terminal exactly like any shell command.

You do **not** need this to get value — the graph + Dataview already work. It's for when
you want an agent to create/append notes programmatically.

---

## 6. The everyday loop

```
                 ┌─ HPC: run experiments, then `./hub vault`  (regenerates experiments/*.md)
   you commit ──▶│
                 └─ HPC: git push mine main
                          │
                          ▼
   Mac: git pull   ──▶ Obsidian graph updates automatically (Dataview tables refresh)
                          │
   you write intuitions in concepts/ (in Obsidian or Cursor on the Mac)
                          │
   Mac: git commit + push mine main  ──▶  HPC: git pull   (the web grows from both ends)
```

- Experiment notes are **generated** (`./hub vault`) — don't hand-edit them; your edits
  would be overwritten. Put your prose in `concepts/`, `hub/`, and `maps/`.
- Concept/MOC notes are **hand-written** (by you and/or the agent) — these are the
  durable spider-web.

---

## 7. Git hygiene for a smooth two-machine life

- `.obsidian/workspace*.json` (window layout, which note was open) churns constantly and
  causes noise/conflicts — it's already in `.gitignore`. The rest of `.obsidian/` (graph
  colors, enabled plugins) *is* committed so both machines share config.
- If you ever hit a merge conflict, it'll be in a markdown note — open it, keep both
  sides' text (knowledge is additive), delete the `<<<<<<<`/`=======`/`>>>>>>>` markers.
- **Figures don't sync** (they live under gitignored `results/.../figures/`). Experiment
  notes therefore link concepts + metrics, not images. To view a run's diagnostic
  figures, open its rich card in Cursor *on the HPC* (`docs/model_cards/<id>.md`). A
  future enhancement can copy small PNG thumbnails into a tracked `docs/_assets/`.

---

## 8. Folder map of the vault (`docs/`)

| Folder | What it is | Edited by |
|---|---|---|
| `00-system/` | the vault's behavioral contract + note templates | you / agent (rarely) |
| `concepts/` | atomic, interlinked intuition notes — **the spider-web** | you + agent (hand-written) |
| `hub/` | one note per `./hub` command — **the hub map** | you + agent |
| `experiments/` | **auto-generated** graph nodes for all 175 runs (`./hub vault`) | the hub (don't hand-edit) |
| `maps/` | Maps of Content (MOCs): the entry points into the graph | you + agent |
| `conceptual_framework.md` etc. | the existing long-form prose (source of truth) | you + agent |
| `model_cards/` | rich cards **(HPC-only, gitignored)** — figures, Cursor preview | the hub |

Start at `maps/Concepts MOC.md` and `maps/Hub Operations MOC.md` — those are the front
doors. Then just follow links and let the graph pull you around.
