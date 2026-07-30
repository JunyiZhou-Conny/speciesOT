# Connect Cursor to OOD Compute Node (instead of login node)

When you start a Jupyter/OOD session, the job runs on a **compute node** (e.g. `holy7c04205.rc.fas.harvard.edu`). Cursor can use that node via SSH so you get full compute resources instead of the limited login node.

## 1. Get the compute node hostname from Open OnDemand

In your OOD session card, copy the **Host** value (e.g. `holy7c04205.rc.fas.harvard.edu`). This changes each time you start a new session.

## 2. Edit your SSH config

You already have `fasrc` for the login node. Add a second block that jumps through it to the compute node.

**Existing (keep as-is):**
```sshconfig
Host fasrc
    HostName login.rc.fas.harvard.edu
    User jzhou1125
    IdentityFile ~/.ssh/id_rsa
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 8h
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

**Add this (compute node via fasrc):**
```sshconfig
Host holy-compute
    HostName holy7c04205.rc.fas.harvard.edu
    User jzhou1125
    IdentityFile ~/.ssh/id_rsa
    ProxyJump fasrc
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

Replace `holy7c04205.rc.fas.harvard.edu` with the **current** Host from your OOD session when you start a new job (it changes per session).

## 3. Connect Cursor to the compute node

1. In Cursor: **Remote-SSH: Connect to Host** (Command Palette or remote icon).
2. Choose **`holy-compute`** (the Host you defined), not the login node.
3. Cursor will: connect to the login node, then jump to the compute node. Your workspace will be the same files (e.g. `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT`) but commands run on the compute node.

## 4. When you start a new OOD session

The compute node hostname changes with each new job. Update `~/.ssh/config`:

- Set `HostName` under `holy-compute` to the new Host from the OOD session card (e.g. `holy7c04321.rc.fas.harvard.edu`).

## Notes

- **Session lifetime:** When the OOD job ends, that compute node is no longer yours; switch Cursor back to the login host or update to a new compute node.
- **Same files:** Login and compute nodes share the same filesystem, so your project path is the same on both.
- If direct SSH to the compute node is blocked from outside, `ProxyJump` through the login node is required (as in the config above).
