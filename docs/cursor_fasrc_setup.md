# Cursor ↔ Harvard FASRC (Cannon): connect, then tune

**Owns:** how a local Cursor talks to the cluster, and the cluster-side settings that make it
usable. Supersedes `docs/cursor-connect-compute-node.md` (archived under `docs/_archive/`),
which only covered pointing an SSH host at an OOD compute node.

Verified on **2026-07-27** from inside a live session: compute node `holy7c06401`,
Rocky Linux 8.10 (kernel 4.18), OOD job `35476591` on partition `shared`
(`.fasrcood/sys/dashboard…`), home `/n/home01` at 45 GB of 95 GB used.

---

## 0. The mental model

Cursor runs on your laptop. Remote-SSH installs a small server into your **cluster** `$HOME`
(`~/.cursor-server`) and runs the terminal, Python, and the agent there. Files are edited in
place on `/n/holylabs/...` — nothing is synced.

```
laptop (Cursor UI)  ──ssh──▶  login node  ──ssh──▶  compute node (your job)
                                  │                        │
                                  └──── same $HOME, same /n/holylabs ────┘
```

Two SSH host aliases, two purposes:

| Alias | Lands on | Use for |
|---|---|---|
| `fasrc` | a login node | editing, git, `./hub generate`, submitting sbatch |
| `holy-compute` | the compute node of a running job | notebooks, training, anything that burns CPU/GPU |

FASRC explicitly asks that notebooks and scripts **not** run on login nodes, and caps you at
**5 login sessions** (each Cursor window is one).

Because every node mounts the same home directory, one `~/.ssh/authorized_keys` on the cluster
governs access to *all* nodes. That single fact is why §1.2 below is the step that makes or
breaks the compute-node hop.

---

## 1. First-time setup

### 1.1 Prerequisites

- FASRC account with cluster access, FASRC password (**not** HarvardKey), and the FASRC
  **OpenAuth** 6-digit token from <https://two-factor.rc.fas.harvard.edu/>. FASRC 2FA is a
  separate system from HarvardKey 2FA.
- FASRC VPN (`vpn.rc.fas.harvard.edu`, username `<user>@fasrc`). Login nodes are reachable
  worldwide without VPN, but **passwordless key login is only permitted from Harvard networks
  and the VPN** — and key login is what keeps Cursor from asking for a 2FA code on every
  internal connection. Turn the VPN on first.
- Cursor with the **Remote - SSH** extension (`anysphere.remote-ssh`, bundled; install from the
  Extensions pane if missing).

### 1.2 Put your laptop's public key on the cluster

Run **on the laptop**, not on the cluster:

```bash
ssh-keygen -t ed25519                     # skip if you already have a key
ssh-copy-id -i ~/.ssh/id_ed25519.pub <fasrc_user>@login.rc.fas.harvard.edu
```

No `ssh-copy-id` (Windows):

```bash
cat ~/.ssh/id_ed25519.pub | ssh <fasrc_user>@login.rc.fas.harvard.edu "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Check: `ssh <fasrc_user>@login.rc.fas.harvard.edu` logs in with no password prompt (on VPN).

Being able to `ssh login → compute` *from the cluster* is not sufficient. When Cursor hops
through the login node, the **laptop's** key is what the compute node sees. A password prompt
for `<user>@holy7cXXXXX` means the laptop key is missing from `authorized_keys`.

### 1.3 Local `~/.ssh/config`

`C:\Users\<you>\.ssh\config` on Windows. Minimal working pair:

```sshconfig
Host fasrc
    HostName login.rc.fas.harvard.edu
    User <fasrc_user>
    IdentityFile ~/.ssh/id_ed25519
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 8h
    ServerAliveInterval 60
    ServerAliveCountMax 3

Host holy-compute
    HostName holy7c06401.rc.fas.harvard.edu   # changes every job — see §2.1
    User <fasrc_user>
    IdentityFile ~/.ssh/id_ed25519
    ProxyJump fasrc
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

`ControlMaster` matters: Cursor opens more than one SSH connection per window, and without
multiplexing each one triggers a fresh 2FA prompt. `ControlPersist 8h` reuses the first
authenticated connection for the day.

**Windows:** `ControlMaster` is unsupported and FASRC does not support Remote-SSH to a compute
node from Windows. Use `fasrc` for editing, and FASRC's *Remote-Tunnel via batch job* for
compute (§4).

### 1.4 Connect

1. `Cmd/Ctrl+Shift+P` → **Remote-SSH: Connect to Host** → `fasrc`.
2. Enter FASRC password, then the OpenAuth code, in the palette input.
3. **File → Open Folder** and **paste** the full project path
   (`/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT`). Paste it whole — typing it makes Cursor
   enumerate huge directories as you go and it will hang.

### 1.5 Get onto a compute node

Either read the **Host** off an Open OnDemand session card, or from a login-node terminal:

```bash
salloc -J cursor -p test -c 4 --mem 16G -t 0-08:00
hostname          # e.g. holy7c06401.rc.fas.harvard.edu
```

Put that hostname in the `holy-compute` block, then **Remote-SSH: Connect to Host** →
`holy-compute`. If it fails immediately, open a `fasrc` window first (that establishes the
shared master connection Cursor's second connection needs), or pre-warm it locally with
`ssh -o ServerAliveInterval=30 -fN fasrc`.

---

## 2. Optimizations (what is worth changing about the current setup)

Ordered by payoff. Each one states the problem observed on this cluster, then the fix.

### 2.1 Stop hand-editing `HostName` every session

The compute node changes with every job, so the config in §1.3 needs an edit per session — and
a stale `HostName` produces a confusing hang rather than a clear error. Two better options.

**(a) Attach to whatever job you already have running.** Name the job `cursor` (`salloc -J cursor …`)
and let SSH look up the node:

```sshconfig
Host holy-compute
    User <fasrc_user>
    IdentityFile ~/.ssh/id_ed25519
    ProxyCommand ssh -q fasrc "nc \$(squeue -u <fasrc_user> -h -t R -n cursor -o '%N' | head -n1) 22"
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 4h
    ServerAliveInterval 60
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
```

For an **OOD** session instead of `salloc`, the job name is `.fasrcood/sys/dashboard/...`, so
match on that:

```sshconfig
    ProxyCommand ssh -q fasrc "nc \$(squeue -u <fasrc_user> -h -t R -o '%N %j' | awk '/fasrcood/{print \$1; exit}') 22"
```

`StrictHostKeyChecking no` / `UserKnownHostsFile /dev/null` are required here: the alias is
stable but the host key changes with the node, which otherwise trips host-key verification.

**(b) Allocate on connect** (FASRC-documented). Replace the `ProxyCommand` with:

```sshconfig
    ProxyCommand ssh -q fasrc "salloc --immediate=180 -J cursor -p test -c 4 --mem 16G -t 0-04:00 --quiet /bin/bash -c 'echo $SLURM_JOBID > ~/cursor-job-id; nc \$SLURM_NODELIST 22'"
```

Convenient, with one trap: Cursor makes **two** connections, so without the `ControlMaster`
block above you get **two SLURM jobs**. Keep multiplexing on, and when a session ends clear the
socket with `ssh -O exit holy-compute` so the next connect allocates cleanly.

Either way, `scancel` is still yours to run (§2.5).

### 2.2 Fix the agent sandbox — it cannot work on this cluster

Cursor tries to run agent shell commands inside a sandbox, and on Cannon **both** backends fail,
so commands intermittently die with `exit code 2` and
`Failed to resolve Linux sandbox backend`:

- **Landlock** is absent. `cat /sys/kernel/security/lsm` returns `capability,yama,selinux,bpf`
  on this node — no `landlock` (kernel 4.18 predates Landlock v3).
- **bubblewrap** exists (`/usr/bin/bwrap`) but its preflight fails while setting up the CA
  bundle: `bwrap: Can't create file at /etc/pki/tls/certs/ca-bundle.crt: No such file or
  directory`. On the host that path is a symlink into `/etc/pki/ca-trust/extracted/...`; the
  bind-mount inside the namespace has nowhere to land.

Neither is fixable without root, so disable the sandbox for cluster work. Preferred, because it
travels with the repo:

```json
// .cursor/sandbox.json
{ "type": "insecure_none" }
```

Per-user equivalent (covers every workspace on the cluster): the same file at
`~/.cursor/sandbox.json`. Or, per-remote in the UI: **Settings → search "sandbox"** → disable.

Two caveats. `.cursor/*.json` is write-protected from the agent, so create it by hand. And
`insecure_none` means agent commands run with your full cluster privileges — which is already
true of anything you approve in a terminal here, but worth stating out loud on shared storage.

### 2.3 Keep the editor away from a quarter-terabyte of results

Measured at the workspace root:

| Directory | Size | Tracked? |
|---|---|---|
| `scgen-cellot-autoresearch/` | 197 G | gitignored |
| `cellot/` | 25 G | `results/`, `datasets/` gitignored |
| `scgen-cellot-ablation/` | 12 G | gitignored |
| everything else | < 1 G | mostly tracked |

`.gitignore` does **not** restrain the file watcher, so the remote server sets watches across
~235 GB on an NFS mount. That shows up as slow saves, laggy search, and a busy extension host.
Add a workspace settings file:

```json
// .vscode/settings.json
{
  "files.watcherExclude": {
    "**/scgen-cellot-autoresearch/**": true,
    "**/scgen-cellot-ablation/**": true,
    "**/scgen-cellot-autoresearch/results/**": true,
    "**/cellot/cellot_gpu/results/**": true,
    "**/cellot/cellot_gpu/datasets/**": true,
    "**/cellot/_archive/**": true,
    "**/reference_papers/**": true,
    "**/.git/objects/**": true
  },
  "search.exclude": {
    "**/scgen-cellot-autoresearch/**": true,
    "**/scgen-cellot-ablation/**": true,
    "**/cellot/cellot_gpu/results/**": true,
    "**/cellot/cellot_gpu/datasets/**": true,
    "**/cellot/_archive/**": true,
    "**/reference_papers/**": true
  },
  "files.exclude": { "**/__pycache__": true }
}
```

And keep codebase indexing off the same paths with a `.cursorindexingignore` at the repo root
(same syntax as `.gitignore`):

```gitignore
scgen-cellot-autoresearch/
scgen-cellot-ablation/
cellot/cellot_gpu/results/
cellot/cellot_gpu/datasets/
cellot/_archive/
reference_papers/
docs/model_cards/
```

Excluding them from *search* is a real trade-off: log spelunking under
`scgen-cellot-autoresearch/` then needs `rg` in a terminal. That is the right trade for an
editor on a network filesystem.

### 2.4 Watch the home quota

`~/.cursor-server` (server builds, extensions, caches, logs) lives in `$HOME`, which is
**95 GB and already 47% full**. Measured 2026-07-27: `~/.cursor-server` **4.8 GB**, `~/.cache`
**5.4 GB** — together about a fifth of the 45 GB in use. When a connection starts failing in
strange ways, quota is a prime suspect:

```bash
du -sh ~/.cursor-server ~/.cursor ~/.cache 2>/dev/null
df -h /n/home01
rm -rf ~/.cursor-server/data/{Cache,CachedData,CachedExtensionsVSIXs}
rm -rf ~/.cursor-server/data/logs/*        # keeps the current session's logs
```

Old server builds under `~/.cursor-server/bin/<commit>/` accumulate after upgrades; all but the
newest are safe to delete while disconnected.

### 2.5 Session hygiene

- Closing a Cursor window does **not** end an `salloc`. `squeue -u $USER` then
  `scancel <jobid>`; the allocate-on-connect variant writes the id to `~/cursor-job-id`.
- 5 login sessions max. Use **Close Remote Connection** rather than leaving windows open.
- Prefer the VPN for interactive sessions; connections are noticeably more stable.
- Long training runs belong in `sbatch`, not in a Cursor terminal — a dropped SSH connection
  takes the terminal's process with it.

### 2.6 Make work survive disconnects

`tmux` is available (`/usr/bin/tmux`). Anything long-running that must be interactive should
start inside it, so a closed laptop lid does not kill it:

```bash
tmux new -s work        # detach: Ctrl-b then d
tmux attach -t work
```

The `agent` CLI is also installed (`~/.local/bin/agent`). `~/cursor-remote/start_worker.sh`
registers this node as a Cursor "My Machines" worker inside tmux, so an agent driven from
<https://cursor.com/agents> (phone included) executes here, in this repo. It lives only as long
as the SLURM job, and needs a paid plan. See `~/cursor-remote/README.md`.

### 2.7 Environment details specific to this repo

- `./hub` auto-activates the `CellOT` conda env; notebooks and `./hub prep` want `analysis`.
- `cellot` is not pip-installed — `export PYTHONPATH=<repo>/cellot/cellot_gpu` before importing it.
- If the remote server refuses to start, temporarily comment out the `conda init` block in
  `~/.bashrc`; FASRC lists it as a known Remote-SSH failure mode.
- Optional local settings that shave a few seconds and some flakiness off each connect:

```json
{
  "remote.SSH.remotePlatform": { "fasrc": "linux", "holy-compute": "linux" },
  "remote.SSH.connectTimeout": 60
}
```

---

## 3. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Password prompt for `<user>@holy7cXXXXX` | laptop key not in cluster `authorized_keys` | §1.2 |
| `Connection closed by UNKNOWN port 65535` after auth | compute node rejected the laptop's credentials | §1.2 |
| 2FA asked repeatedly in one session | no `ControlMaster`, or a stale socket | §1.3; `ssh -O check fasrc`, `ssh -O exit fasrc` |
| `Host key verification failed` on `holy-compute` | alias reused across nodes with different host keys | add `StrictHostKeyChecking no` + `UserKnownHostsFile /dev/null` (§2.1) |
| Connect hangs, no prompt | `HostName` points at a node whose job ended | update it, or switch to a dynamic `ProxyCommand` (§2.1) |
| Agent commands fail `exit 2`, `Failed to resolve Linux sandbox backend` | no Landlock, bwrap preflight fails | §2.2 |
| Two SLURM jobs per connect | allocate-on-connect without multiplexing | §2.1(b) |
| `Failed to parse remote port` | stale lockfiles | remove `~/.cursor-server/.lockfiles`, reconnect |
| Server won't install/start | `$HOME` quota, or `conda init` in `~/.bashrc` | §2.4, §2.7 |
| Editor sluggish, saves slow | watcher crawling 235 GB of results | §2.3 |
| Two Cursor windows fight over one node | 5-session cap / duplicate jobs | close unused windows, `scancel` strays |

---

## 4. If SSH is not cooperating (or you are on Windows)

FASRC's own recommendation is **Remote Tunnel via a batch job**: submit a job that downloads the
editor CLI and runs `code tunnel`, authenticate with a **personal GitHub account** (Harvard
Microsoft accounts stopped working for device-code auth in July 2026), then attach from the local
editor's Remote-Tunnel extension. It survives network glitches and works from Windows.
Script and steps: <https://docs.rc.fas.harvard.edu/kb/vscode-remote-development-via-ssh/>

---

## 5. Onboarding someone else

Send them [`docs/cursor_fasrc_handout.md`](cursor_fasrc_handout.md) — a standalone version of
§1, §2.1(a), §2.2, §2.4, §2.5, and §4, with every speciesOT-specific path and measurement
stripped out and `<fasrc_user>` placeholders throughout. It assumes nothing about this repo, so
it can go to anyone with a FASRC account.

Keep the two files in sync when the connection recipe changes: this document owns the reasoning
and the cluster measurements, the handout owns the shareable instructions.

---

*Last updated 2026-07-27. Cluster-side facts (kernel LSM list, quota, directory sizes, job
layout) were measured on `holy7c06401`; re-measure before trusting the numbers a year from now.*
