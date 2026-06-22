# scGen vs CellOT ablation (rev 3)

**Active workspace:** [`/Users/conny/Desktop/scGen v.s. CellOT`](../../scGen-vs-CellOT)  
(symlink: `speciesOT/scGen-vs-CellOT`)

The canonical plan and scripts live in the Desktop folder. This copy points agents and docs at the same content.

**Quick link:** [scgen_bunne_ablation_plan.md](../../scGen-vs-CellOT/scgen_bunne_ablation_plan.md)

## Execution order

1. **Stage 0 (gate):** scGen repo → 6619 + scGen split + Fig5 → ~0.91 R²  
2. **Stage 1 (2×2):** CellOT scGen + `transport_scgen` + unified eval  
   - A: 6619, rat in train  
   - B: 1k, rat in train  
   - C: 6619, Bunne OOD  
   - D: 1k, Bunne OOD  

See full checklist in the Desktop `README.md`.
