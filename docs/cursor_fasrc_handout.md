# Using Cursor on your laptop with Harvard FASRC (Cannon)

A short setup guide. At the end, Cursor runs on your laptop while the terminal, Python, and the
AI agent all execute on the cluster, editing files in place under `/n/...` — nothing is synced
back and forth, and you never need to `scp` a file to try a change.

Replace `<fasrc_user>` throughout with your FASRC username (the short one, e.g. `jharvard` —
not an email address, not HarvardKey).

## How it works

Cursor installs a small server into your cluster home directory (`~/.cursor-server`) the first
time you connect, and talks to it over SSH.

```
laptop (Cursor UI)  ──ssh──▶  login node  ──ssh──▶  compute node (your Slurm job)
                                  │                        │
                                  └──── same $HOME, same /n/holylabs ────┘
```

You set up two SSH targets and pick one depending on what you're doing:

| Target | Lands on | Use for |
|---|---|---|
| `fasrc` | a login node | editing code, git, submitting `sbatch` jobs |
| `holy-compute` | the compute node of a job you started | notebooks, training, anything CPU/GPU-heavy |

FASRC asks that notebooks and scripts **not** run on login nodes, and limits you to **5 login
sessions** — each Cursor window counts as one.

All cluster nodes mount the same home directory, so a single `~/.ssh/authorized_keys` on the
cluster controls access to every node. That's why step 2 below is the one that matters most.

## 1. Prerequisites

- FASRC account **with cluster access**, your FASRC password, and the FASRC **OpenAuth** 6-digit
  2FA token from <https://two-factor.rc.fas.harvard.edu/>. FASRC 2FA is its own system,
  unrelated to HarvardKey 2FA.
- The FASRC VPN (`vpn.rc.fas.harvard.edu`, username in the form `<fasrc_user>@fasrc`). Login
  nodes are reachable worldwide without it, but **passwordless SSH-key login is only permitted
  from Harvard networks and the VPN** — and key login is what stops Cursor from asking for a 2FA
  code on every internal connection. Connect to the VPN before the steps below.
- Cursor, with the **Remote - SSH** extension. It ships with Cursor; install it from the
  Extensions pane if it isn't there.

## 2. Put your laptop's SSH key on the cluster

Run these **on your laptop**, in a local terminal:

```bash
ssh-keygen -t ed25519      # skip this line if you already have a key
ssh-copy-id -i ~/.ssh/id_ed25519.pub <fasrc_user>@login.rc.fas.harvard.edu
```

If `ssh-copy-id` isn't available (typical on Windows), do the same thing by hand:

```bash
cat ~/.ssh/id_ed25519.pub | ssh <fasrc_user>@login.rc.fas.harvard.edu "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

**Check it worked:** `ssh <fasrc_user>@login.rc.fas.harvard.edu` should log you in with no
password prompt (while on the VPN).

Being able to `ssh` from the login node to a compute node is *not* the same thing. When Cursor
hops through the login node, the compute node authenticates your **laptop's** key. If you later
get a password prompt for `<fasrc_user>@holy7cXXXXX`, come back to this step.

## 3. Edit your local SSH config

The file is `~/.ssh/config` on macOS/Linux, `C:\Users\<you>\.ssh\config` on Windows. Create it if
it doesn't exist, and add:

```sshconfig
Host fasrc
    HostName login.rc.fas.harvard.edu
    User <fasrc_user>
    IdentityFile ~/.ssh/id_ed25519
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 8h
    ServerAliveInterval 60

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

What the non-obvious lines do:

- **`ControlMaster` / `ControlPath` / `ControlPersist`** reuse one authenticated connection.
  Cursor opens more than one SSH connection per window, and without this each one prompts for a
  fresh 2FA code. With it, you authenticate once and it's good for hours.
- **`ProxyCommand`** on `holy-compute` looks up the node your job is running on (any running job
  named `cursor`) and tunnels to it through the login node, so you never hand-edit a hostname
  when your job changes nodes.
- **`StrictHostKeyChecking no` / `UserKnownHostsFile /dev/null`** are needed because the alias
  stays the same while the actual node — and its host key — changes between jobs.

**Windows users:** `ControlMaster` isn't supported, and FASRC doesn't support Remote-SSH to a
compute node from Windows. Use `fasrc` for editing, and for compute use FASRC's
*Remote-Tunnel via batch job* approach instead (see the link at the bottom).

## 4. Connect, for editing

1. In Cursor: `Cmd/Ctrl+Shift+P` → **Remote-SSH: Connect to Host** → `fasrc`.
2. If prompted, type your FASRC password, then your OpenAuth code, into the box at the top.
3. **File → Open Folder**, and **paste** the full path of the project you want
   (e.g. `/n/holylabs/<lab>/Lab/<you>/<project>`). Paste it rather than typing — Cursor tries to
   list directories as you type, and `/n` is enormous enough to hang the window.

This connection is for reading and writing code, git, and submitting jobs.

## 5. Connect, for running things

Start a job from a `fasrc` terminal inside Cursor:

```bash
salloc -J cursor -p test -c 4 --mem 16G -t 0-08:00
```

Name it `cursor` (`-J cursor`) so the SSH config in step 3 can find it. Adjust resources as
needed; for a GPU use something like `-p gpu_test --gres=gpu:1`.

Then **Remote-SSH: Connect to Host** → `holy-compute`.

Two things that trip people up:

- If the first attempt fails, open a `fasrc` window first (that establishes the shared
  connection the second one needs), then connect to `holy-compute`.
- **Closing the Cursor window does not end the Slurm job.** When you're done:
  `squeue -u $USER`, then `scancel <jobid>`.

## 6. Turn off the agent sandbox for cluster work

Cursor normally runs agent terminal commands inside a sandbox. That cannot work on Cannon: the
cluster kernel (Rocky Linux 8, kernel 4.18) has no Landlock support, and the bubblewrap fallback
fails during setup. Left enabled, agent commands fail with
`Failed to resolve Linux sandbox backend`.

Create `~/.cursor/sandbox.json` on the cluster containing:

```json
{ "type": "insecure_none" }
```

(Or, in the UI: **Settings** → search "sandbox" → disable it for that remote.) The trade-off is
that agent commands then run with your normal cluster privileges — the same as anything you'd
approve in a terminal there.

## 7. Two housekeeping habits

- **Home quota.** `~/.cursor-server` (server builds, extensions, caches) lives in your home
  directory, which is 95 GB — a few GB per machine you connect from, and it grows with upgrades.
  If connections start failing in odd ways, check `du -sh ~/.cursor-server ~/.cache` and
  `df -h`, then delete `~/.cursor-server/data/{Cache,CachedData,CachedExtensionsVSIXs}` and old
  builds under `~/.cursor-server/bin/`.
- **Big result directories.** If your project holds tens of GB of outputs, the file watcher will
  crawl all of it over the network filesystem and the editor gets sluggish. `.gitignore` does
  **not** stop the watcher — add the heavy paths to `files.watcherExclude` and `search.exclude`
  in the project's `.vscode/settings.json`, and to a `.cursorindexingignore` file at the project
  root.

## If SSH gives you trouble

FASRC's own preferred method is **Remote Tunnel via a batch job**: submit a job that downloads
the editor CLI and runs `code tunnel`, authenticate with a **personal GitHub account** (Harvard
Microsoft accounts stopped working for device-code auth in July 2026), then attach from your
local editor. It's more resilient to network glitches and it works from Windows.

Full FASRC documentation, including that script:
<https://docs.rc.fas.harvard.edu/kb/vscode-remote-development-via-ssh/>

## Quick troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Password prompt for `<fasrc_user>@holy7cXXXXX` | your laptop's key isn't in the cluster's `authorized_keys` | step 2 |
| `Connection closed by UNKNOWN port 65535` right after authenticating | same as above — the compute node rejected the laptop | step 2 |
| Asked for a 2FA code over and over | `ControlMaster` missing, or a stale socket | step 3; `ssh -O check fasrc`, `ssh -O exit fasrc` |
| `Host key verification failed` for `holy-compute` | the node behind the alias changed | the two `StrictHostKeyChecking`/`UserKnownHostsFile` lines in step 3 |
| Connect hangs with no prompt | no running job named `cursor` for the `ProxyCommand` to find | `squeue -u $USER`; start one as in step 5 |
| Agent commands fail with `Failed to resolve Linux sandbox backend` | sandbox unsupported on this kernel | step 6 |
| `Failed to parse remote port` | stale lock files | delete `~/.cursor-server/.lockfiles` and reconnect |
| Remote server won't install or start | home quota full, or `conda init` in `~/.bashrc` interfering | step 7; temporarily comment out the conda block |
| Editor slow, saves lag | watcher crawling large result directories | step 7 |
