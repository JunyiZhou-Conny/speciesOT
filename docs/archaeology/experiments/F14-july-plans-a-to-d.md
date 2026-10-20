# F14 · July Plans A–D: back to the atlas, a paper-style VAE on the atlas, and unbalanced OT

> On 2026-07-21 Conny gave four AI agents four parallel plans to bring the project back to the human–mouse atlas [D]. Plans A and B summarised and re-read existing results of the frozen atlas benchmark ("v08"): IMPACT_CellOT (optimal transport on autoencoder codes) beats the autoencoder-plus-mean-shift baseline on the decoded MMD score for both monocyte holdouts (M2 0.776 vs 0.575, M1 0.897 vs 0.588), but each number comes from one unseeded training run [R][C]. Plan C trained the original TensorFlow scGen VAE on the same cells (one 11-minute CPU run per holdout). Its 07-21 canvases ranked it against Plan B only by decoded fractions, which are measured against different autoencoder floors, and called it "close but not ahead" of AE-scGen [D]. On a common scale (done here) it falls between the two hub models on absolute MMD, last on MMD relative to its own floor, and well behind both on mean-expression R² [R][I]. Plan D trained an "Option A" unbalanced-OT variant (the same CellOT network on reweighted cells) on the LPS rat task in five jobs that completed on 07-21, but no result was ever written down, and the 2026-10-01 backup holds no files in this folder (nor in six other top-level folders that sort after it) [R][D]. Status: partly worked.

| | |
|---|---|
| Period | 2026-07-21 → 2026-07-30. First dated artefacts: 07-21 10:27–10:28, the UNB-BK `results/` folder and the two Plan B canvases (CV, file times) [R]; Plan C dry-run output 10:32 (APVR m2 `dry_run_split.txt`) [R]; first job 07-21 10:44 (SACCT) [R]; last F14 run: Plan C identity audit, 07-27 15:00 (APVL `identity_audit_35538746_*`, file times) [R]; code committed 07-30 (conny@4244985, conny@fe856aa) [G]. The unbalanced-OT toy is older: its results folder dates from 2026-07-10 (UNB-BK `synthetic/results/`, folder time) [R]. |
| People | Junyi (Conny) Zhou working through Cursor agents: each plan names an "owner agent" (PA:3, PB:3, PC:3, PD:3) [D]. All jobs ran under Conny's Slurm account `jzhou1125` (SACCT) [R]; git author Junyi Zhou [G]. Joshua Price appears only as the intended reader: plan and deliverable address "the mentor" (PA:97, DB:65) [D]; the 07-30 log names the mentor as Joshua Price (L0730:2-9) [D]. No reply or review was found. |
| Status | partly worked (A and B: finished, no new runs; C: trained and scored, the planned comparison with B was done only on non-comparable fractions; D: abandoned unfinished, outputs lost) |
| Main code | PL (plans and deliverables); APV/scripts/01_train_vae.py, 02_eval_metrics.py, 03_identity_audit.py; HM (metric code); UNB/uot/reweight.py, UNB/scripts/train_option_a.py, UNB/scripts/sbatch_option_a_train.sh |
| Results live in | Plan C: APVR (`metrics.json`, `split.csv`, `model/training_log.csv`, `recon_identity_*`, `audit_manifest.json`; also the TensorFlow checkpoints `model/scgen.*` and `pred_single_species_delta.h5ad`, seen with `ls` over ssh), the legacy packs with `X.npz` in fasrc:BK/atlas-paper-vae/data/, and APVL; canvases in CV. Plans A and B created no results; they read HUB/hvg_pearson_residuals_{m1,m2,a_uncapped}_v08_ood/ and conny:speciesOT/baseline/analysis/v08_scorecard_dual.csv; their canvases are in CV. Plan D: no saved results found (UNB-BK holds 0 files). |

Citation shorthands: PL = conny:logs/research_logs/agent_plans_2026-07-21/ · PA, PB, PC, PD = PL/PLAN_A_atlas_memory_pack.md, PLAN_B_atlas_return_scoreboard.md, PLAN_C_paper_vae_on_atlas.md, PLAN_D_unbalanced_ot_option_a.md · DA, DB, DC, DD = PL/DELIVERABLE_A_atlas_memory.md, DELIVERABLE_B_scorecard_m1_m2.md, DELIVERABLE_C_vae_atlas_design.md, DELIVERABLE_D_option_a.md · L0720, L0723, L0727, L0730 = conny:logs/research_logs/research_log_2026-07-20.txt, _2026-07-23.txt, _2026-07-27.txt, _2026-07-30_repo_plan.txt · APV = conny:atlas-paper-vae/ · APVR = `fasrc:BK/atlas-paper-vae/results/atlas_paper_vae_{m1,m2}_v08_ood/` · APVL = fasrc:BK/atlas-paper-vae/logs/ · HUB = fasrc:BK/cellot/cellot_gpu/results/ · UNB = conny:scgen-cellot-unbalanced/ · UNB-BK = fasrc:BK/scgen-cellot-unbalanced/ (listed with `ls`/`find` over ssh on 2026-10-20) · CV = fasrc:/n/home01/jzhou1125/.cursor/projects/n-holylabs-mooney-lab-Lab-junyizhou-speciesOT/canvases/ (Cursor canvases in Conny's FASRC home, not in git or BK; listed and read over ssh on 2026-10-20) · HM = autoresearch:honest_metrics.py (byte-identical to UNB/honest_metrics.py, checked with `cmp`) · VAE = fasrc:BK/scgen-cellot-ablation/scgen-reproducibility/code/scgen/models/_vae.py · CF = conny:docs/conceptual_framework.md · PHA = `fasrc:BK/scgen-cellot-ablation/results/devar_confirmation/atlas_{m1,m2}_phaseA.csv` · SACCT = Slurm accounting (`sacct -X -D`, all jobs of `jzhou1125` running 2026-07-21…22), queried 2026-10-20.

## The question

The day before, the 07-20 log (a "mentor-facing synthesis") judged the CellOT (Bunne Fig. 4) replication on the LPS data partial: the autoencoder (AE) baseline scored at least as well as CellOT on the decoded score, while the scGen Fig. 5 mean check had passed (L0720:31-34, 52) [D]. It listed `infinite games` to stop (its term for open-ended work that cannot be finished, such as a global gene-count search) and proposed one question for the next scoreboard: "does OT beat linear AE-shift on frac_gap_closed_decoded (+ mean R² / JS guardrails)?" (L0720:31-45, 54-59) [D]. On 07-21 the work was split into four plans, with a `fence` (a rule that Plan C must not write into the hub's v08 result folders) (PL/README.md:5-12; PC:45-54) [D].

- **A:** write one "atlas memory brief": what M1 and M2 are, what is frozen in v08, what is already believed about IMPACT vs scGen, what Plan B should reopen, and what Plan C must not confuse (PA:26-32) [D]. No jobs, no edits (PA:36-41) [D].
- **B:** "On v08 OOD (start M2, then M1), does IMPACT_CellOT beat hub scGen AE+shift on `frac_gap_closed_decoded` (ncells=80), with mean-R² and JS guardrails?" (PB:36) [D].
- **C:** build an isolated scaffold to train and score a "Lotfollahi-like VAE" on v08 cells with the same metrics; full training was "Phase 2" (PC:28-30, 102-104) [D]. In fact it was trained the same morning (below).
- **D:** choose one frozen task, reproduce balanced CellOT, implement "Option A" (estimate per-cell mass weights, then train the same balanced network on reweighted samples), score it with the decoded score plus a mass-aware metric, and decide whether to try "Option B" (PD:26-48) [D]. Unbalanced OT (UOT) is optimal transport that may create or destroy mass, so not every source cell must be matched (UNB/PLAN.md:17-29) [D].

## Setup

**Atlas data (A, B, C).** The v08 M1 and M2 cuts (defined in [F10](F10-monocytes-floor-ceiling-and-v08.md)) each hold 8,054 cells: 4,027 mouse (Tabula Muris) and 4,027 human (Tabula Sapiens), 1,000 genes (APVR m2 `dry_run_split.txt`) [R]. Every one of the 27 cell types has exactly as many mouse as human cells (fasrc:BK/atlas-paper-vae/data/m2_v08_legacy/obs.csv) [R]. Genes are the top 1,000 Pearson-residual highly variable genes (genes whose expression varies most across cells), Chromium assays only, log1p values (conny:specs/atlas_paper_vae_m2_v08.yaml:10-18) [C]; values range 0–8.46 with 78% zeros (`dry_run_split.txt`) [R]. M1 and M2 contain the same 8,054 cells, and their gene lists share 999 of 1,000 genes (legacy `obs.csv`/`var.csv` of both cuts) [R]. The paper-VAE gene lists equal the hub's, in the same order (legacy `var.csv` vs HUB/hvg_pearson_residuals_m{1,2}_v08_ood/scgen/ae_identity/ae_identity_pergene.csv) [R].

**Split.** `toggle_ood` (CellOT's out-of-distribution split): first all cells, including the held-out types, are split 80/20 into train/test with random_state 0 (in the hub separately per species); then the held-out cell types are relabelled, split 50/50 stratified by species, into "ood" (the evaluation set) and "ignore" (never used) (conny:cellot/cellot_gpu/cellot/data/cell.py:267-290, 330-384) [C]. A package that wants the same cells must repeat this order exactly [I].

| cut | held-out types | OOD cells, mouse → human | paper-VAE train cells | hub train cells |
|---|---|---|---|---|
| M1 | non-classical monocyte (CL:0000875) | 182 → 183 | 5,857 | 5,854 |
| M2 | CL:0000875 + generic "monocyte" (CL:0000576) | 200 → 201 (183/180 non-classical, 17/21 monocyte) | 5,802 | 5,798 |

Sources: APVR `split.csv` joined to legacy `obs.csv`; hub counts from HUB/hvg_pearson_residuals_m{1,2}_v08_ood/scgen/ae_identity/ae_identity_metrics.csv [R]. The train sets differ because the paper-VAE scripts split all cells at once, while the hub splits each species separately (`groupby: condition`) (APV/scripts/01_train_vae.py:45-61 vs cell.py:267-290) [C]. The sizes are almost equal, but the cells are not: the two train sets share only 4,765 cells on M1 and 4,722 on M2, so about 19% of each train set differs (APVR `split.csv` vs the cell IDs in HUB/hvg_pearson_residuals_m{1,2}_v08_ood/scgen/ae_identity/ae_identity_percell.csv) [R]. The OOD halves are the same cells: the `ood` mouse and human cell IDs are identical in both files [R], and the raw MMD floor, ceiling and identity R² computed by the two code bases agree to 7 or more significant digits (M2 floor 0.0232675 in APVR m2 `metrics.json` and in HUB/hvg_pearson_residuals_m2_v08_ood/impact_cellot/evals_ood_data_space/extended_metrics.csv) [R].

**LPS data (D).** CellOT's cross-species LPS task `paper_crossspecies_rat_ood` ([F11](F11-bunne-lps-replication.md)): file `hvg-top1k-train-only.h5ad`, transport from unstimulated (`unst`) to LPS-stimulated (`LPS6`) cells, rat held out entirely, training on the other species (UNB/configs/option_a/lps_rat_balanced.yaml:5-26) [C]. The transport axis here is the stimulation, not the species [C].

**Models.**

| model | plan | architecture and training | prediction for held-out mouse cells |
|---|---|---|---|
| AE-scGen ("hub scGen") | A, B | CellOT-repo autoencoder 1000→256→256→50, dropout 0.1, `beta: 0` (no KL term), linear output layer; Adam lr 1e-3, 50k iterations (HUB/hvg_pearson_residuals_m2_v08_ood/scgen/config.yaml; conny:cellot/cellot_gpu/cellot/models/ae.py:85) [C] | encode, add (mean human code − mean mouse code over train cells), decode (ae.py:175-187; cellot/utils/evaluate.py:95) [C] |
| IMPACT_CellOT | A, B | input-convex networks (ICNN) f, g, 4 hidden layers of 64, on the same AE's 50-d codes; batch 128, lr 1e-4, 50k iterations (HUB/.../impact_cellot/config.yaml) [C]. The CellOT paper used batch 256 and 250k iterations [P, Methods "Hyperparameters"] | transport the code with the learned map, decode [C] |
| paper VAE | C | TensorFlow 1.15 `VAEArith` from the theislab scGen code: 1000→800→800→100→800→800→1000, batch norm, leaky ReLU, dropout 0.2, ReLU output layer; loss mean(0.5·‖x−x̂‖² + α·KL), α = 5e-5; Adam lr 1e-3, batch 32, 300 epochs, validation on the "test" split (VAE:107-118, 167-170; APV/configs/m2_v08.yaml:24-32; 01_train_vae.py:121-159) [C] | `single_species_delta`: decode(μ(mouse OOD) + δ), δ = mean μ(human train) − mean μ(mouse train), μ = posterior mean (APV/scripts/02_eval_metrics.py:152-171) [C] |
| Option A | D | CellOT paper recipe: ICNN 4×64, batch 256, lr 1e-4, 10 inner steps, 250k iterations on the frozen LPS AE (lps_rat_balanced.yaml:13-53) [C], as in the paper [P]; training loaders replaced by `WeightedRandomSampler` (with replacement); test loaders unchanged; seed 0 (UNB/scripts/train_option_a.py:93-131, 169-189) [C] | as IMPACT |

Notes. The paper VAE uses the same mean-shift rule as AE-scGen, in a different latent space [C]. It is not scGen's Fig. 5 rule, which predicts rat LPS cells as ½(z_mouse,LPS + δ_species + z_rat,control + δ_LPS) [P, scGen cross-species section]. Without cell-type balancing the δ is a plain mean over train cells (02_eval_metrics.py:166-168) [C]. Because every cell type has equal mouse and human counts, species composition does not bias it; but scGen's balancing would also give every cell type equal weight, while the plain mean weights types by size. The effect of that difference was not tested [I]. Training is unseeded in both atlas stacks: no TensorFlow or torch seed is set in APV/scripts/01_train_vae.py, VAE, conny:cellot/cellot_gpu/cellot/ or cellot/cellot_gpu/scripts/train.py (text search; the only seed in 01_train_vae.py, line 126, picks the optional smoke subsample) [C]. Only the data split is seeded (random_state 0). The vendored decoder discards the output of its second batch-norm layer (VAE:114), an upstream quirk also noted in L0723:102-105 [C][D].

**Evaluation.** All atlas numbers below use one set of definitions (HM:66-128, 195-349; conny:cellot/cellot_gpu/scripts/extended_metrics.py; decoded_frame_metrics.py:8-17, 125-146) [C]:
- MMD (maximum mean discrepancy, a distance between two cell clouds; 0 = same distribution): RBF kernel averaged over 50 bandwidths `logspace(1,-3)`, biased estimator, random subsamples of 30, 50 and 80 cells, 10 repetitions, seed 0; headline n = 80 [C].
- Raw frame: floor = MMD between two disjoint random subsets of the real human cells; ceiling = MMD(mouse as-is, human) [C]. Each MMD call restarts the random generator at seed 0 (HM:91) [C].
- Decoded frame: floor = MMD(decode(encode(human)), human), i.e. the model's own reconstruction error; ceiling = MMD(decode(encode(mouse)), human) [C]. `frac_gap_closed_decoded` (fgc_dec) = (ceiling − model) / (ceiling − floor). The repo calls it the `north-star`, its single headline metric (conny:AGENTS.md:31-34) [D].
- R² of means: squared Pearson correlation of the gene-mean vectors; `frac_r2_closed` puts mouse-as-is at 0 and split-half human at 1 (HM:159-162, 271-282) [C].
- `mean_js`: per-gene Jensen–Shannon divergence between 50-bin histograms, averaged over genes (HM:132-155; conny:cellot/cellot_gpu/cellot/losses/divergence.py:29-80) [C].

Flag: a decoded fraction is measured against the scored model's own AE floor, so it only ranks models that share one AE (CF:625-642) [D]. The two hub models share one AE per cut (same floor in both `decoded_frame_metrics.csv`) [R]; the paper VAE does not [C]. Plan D's evaluation was CellOT's `evaluate.py` (n = 80, 500, 1000) and `decoded_frame_metrics.py` (its default n = 30, 50, 80), plus a new sidecar `uot_aware_metrics.csv` (UNB/scripts/eval_option_a.py:36, 46-154; decoded_frame_metrics.py:91) [C]. Its outputs go to `evals_ood_data_space/`, while the production LPS numbers it was to be compared with sit in `evals_ood_data_space_paper/` with decoded n = 80, 500, 1000 (HUB/paper_crossspecies_rat_ood/impact_cellot/), so only n = 80 is common to both [C][R].

## What was done and what came out

### Before the plans (07-10 → 07-20)

- 07-10: a synthetic unbalanced-OT study existed by then (UNB-BK `synthetic/results/`, folder time 2026-07-10 13:36) [R]. No file inside survives [not found].
- 07-20: on the LPS rat task, AE-scGen scored fgc_dec 0.276 and IMPACT 0.076 at n = 80 (HUB/paper_crossspecies_rat_ood/{scgen,impact_cellot}/evals_ood_data_space_paper/decoded_frame_metrics.csv) [R]. This is the result behind "AE-scGen ≥ CellOT" in L0720:33 [D].

### Plan A — atlas memory brief (07-21)

The brief exists (DA, dated 2026-07-21, DA:3) [D]. It defines M1/M2, lists the v08 freeze, tabulates raw vs decoded scores, explains why raw MMD misled on M1 (the `AE round-trip tax`, the repo's name for the error added by encoding and decoding, plus Smart-seq2 contamination), ranks objectives, gives a "reopen list" for B, a confusion table for C and five "standing claims" (DA:11-131) [D]. Every number I checked in its table (DA:57-64) matches the result files, including the CD8 rows: IMPACT 0.935 vs AE-scGen 0.596 (HUB/hvg_pearson_residuals_a_uncapped_v08_ood/{impact_cellot,scgen}/evals_ood_data_space/decoded_frame_metrics.csv) [R]. It adds no new measurement [I]. The Smart-seq2 claims (DA:78) belong to F10 and were not re-checked here. The two Cursor canvases it cites (DA:5-6) are not in git or BK, but they survive in Conny's FASRC home: `atlas-v08-memory-pack.canvas.tsx` (07-21 10:57) and `speciesot-journeys-so-far.canvas.tsx` (07-21 11:08) (CV, file times) [R]. The memory-pack canvas has the same sections as DA, and the five closing claims of the "journeys" canvas closely follow DA:125-131 (CV, read with `grep`/`sed`) [D].

### Plan B — atlas scoreboard (07-21)

Plan B ran nothing: the sidecars were "already on disk" (DB:27) [D], and apart from one interactive dashboard session the only jobs on 07-21/22 were Plan C and D jobs (SACCT) [R]. The files it read date from 2026-06-05 (`evals.csv`, `extended_metrics.csv`) and 2026-06-09 (`decoded_frame_metrics.csv`) (file times in HUB) [R]; DB:27 says "eval dates 2026-06-05" [D].

| cut | model | fgc_dec | fr2_dec | mean_js | fgc_raw | R² of means | MMD (model) | model/floor |
|---|---|---|---|---|---|---|---|---|
| M2 | IMPACT | **0.776** | 0.861 | 0.451 | −0.128 | 0.929 | 0.117 | 1.76 |
| M2 | AE-scGen | 0.575 | 0.906 | 0.485 | −0.675 | 0.949 | 0.162 | 2.45 |
| M1 | IMPACT | **0.897** | 0.821 | 0.449 | +0.061 | 0.918 | 0.104 | 1.29 |
| M1 | AE-scGen | 0.588 | 0.857 | 0.502 | −0.759 | 0.929 | 0.173 | 2.15 |

Source: HUB/hvg_pearson_residuals_m{1,2}_v08_ood/{impact_cellot,scgen}/evals_ood_data_space/{extended_metrics,decoded_frame_metrics}.csv, n = 80 [R]; model/floor computed here [I]. Shared decoded floor/ceiling: M2 0.066/0.292, M1 0.080/0.306 [R]. All values in DB:37-49 match these files [R]. DB's extra column "hub R² (evals)" (0.923, 0.944, 0.919, 0.927) is a different quantity: the square of `r2-means` at n = 80 in each run's `evals.csv`, which is an unsquared Pearson r on 10 random subsamples (mean r 0.9607, 0.9717, 0.9585, 0.9628; squared here) [R][I]. The model/floor values match L0727:141-142 [D][R]. The same numbers appear in the Plan B canvases `atlas-m2-v08-metrics.canvas.tsx` and `atlas-m1-v08-metrics.canvas.tsx` (CV, both 07-21 10:28) [D].

Decision (DB:12): "IMPACT wins cleanly … do not reopen AE HPO" [D]. Because both models share one AE, the decoded fraction, absolute MMD and model/floor all point the same way [R][I]. Mean R² points the other way: AE-scGen is slightly better on both cuts [R]. The canvases DB names (DB:5) are not in git or BK; they exist only in CV (see above) [R]. DB:29 notes that no per-gene reconstruction audit of the hub AEs existed on 07-21 [D]; those sidecars were written on 07-30 (HUB/.../scgen/ae_identity/, file times) [R] ([F15](F15-ae-repair-rounds-and-calibration.md)).

### Plan C — paper VAE on the atlas (07-21; audit 07-27)

1. 10:32: dry run of the split; its table matches DC:52-57 (APVR m2 `dry_run_split.txt`) [R][D].
2. The old anndata in the `scgen_tf1` env cannot read the modern `.h5ad`, so a "legacy pack" (`X.npz` + `obs.csv` + `var.csv`) was exported (APV/configs/m2_v08.yaml:3-6; fasrc:BK/atlas-paper-vae/data/m2_v08_legacy/README.txt) [C][R]. The export script is not in git or BK [not found].
3. Jobs, all on the CPU partition `shared` with 8 cores (SACCT; APVL) [R]:

| job | cut | start → end (07-21, EDT) | state |
|---|---|---|---|
| 33884167 | M2 | 10:44:52 → 10:44:54 | FAILED: `/etc/bashrc: line 12: BASHRCSOURCED: unbound variable` (APVL `train_33884167.err`) |
| 33885331 | M2 | 10:49:34 → 11:01:13 (11 min 39 s) | COMPLETED |
| 33898362 | M1 | 11:19:01 → 11:30:04 (11 min 03 s) | COMPLETED |

The design doc had estimated 2–8 h on CPU (DC:147) [D]. Its stated scope was M2 only (DC:216) [D]; the M1 twin (conny:specs/atlas_paper_vae_m1_v08.yaml:40-42) [C] was added the same morning: its legacy pack is dated 11:18 and its job started 11:19 (fasrc:BK/atlas-paper-vae/data/m1_v08_legacy/, file times; SACCT) [R].

Results (APVR `metrics.json`, `model/training_log.csv`; n = 80, seed 0) [R]:

| | M1 | M2 |
|---|---|---|
| epochs run; best validation loss at epoch | 300; 299 | 300; 297 |
| final train / validation loss | 59.9 / 76.4 | 60.3 / 76.9 |
| reconstruction, paired-cell Pearson² per gene: train / held-out human | 0.816 / 0.353 | 0.816 / 0.357 |
| R² of means (`r2_all`) | 0.805 | 0.803 |
| R² of means, mouse as-is (`r2_identity`) | 0.554 | 0.559 |
| `frac_r2_closed` | 0.572 | 0.563 |
| MMD model; raw floor; raw ceiling | 0.129; 0.0236; 0.1087 | 0.124; 0.0233; 0.1062 |
| `frac_gap_closed` (raw) | −0.240 | −0.216 |
| decoded floor; decoded ceiling | 0.0483; 0.2122 | 0.0454; 0.2023 |
| `frac_gap_closed_decoded` | 0.506 | 0.498 |
| `frac_r2_closed_decoded` | 0.565 | 0.571 |
| `mean_js` | 0.108 | 0.111 |
| latent-frame fraction (denominator ≈ 0.004, not meaningful [I]) | 0.108 | 0.121 |

DC was not updated after the runs; its last word is "Not claimed until metrics land" (DC:218) [D]. Its Phase-2 step "Compare to Plan B AE-scGen on the same v08 OOD cells (north-star `frac_gap_closed_decoded`)" (DC:195; also APV/README.md:38-39) asked for a comparison on the decoded fraction itself [D]. The Phase-2 canvases exist in CV: `atlas-paper-vae-m2-v08-metrics.canvas.tsx` (07-21 11:05, four minutes after the M2 job ended) and `atlas-paper-vae-m1-v08-metrics.canvas.tsx` (11:33) [R]. Their numbers match `metrics.json` (all M2 values and the M1 summary rows checked here), and they rank the VAE on that fraction against remembered hub values: "Does not beat remembered hub M2 AE-scGen (~0.575)" and, for M1, "0.506 ≈ near hub AE (~0.59), well below IMPACT (~0.90)" (CV, read over ssh) [D]. Their last row leaves the "side-by-side on the same v08 OOD cells" as the next step [D]; it was never done. The comparison on a common scale, from the three result files:

| cut | model | MMD (model) | MMD − raw floor | model / own floor | fgc_dec (own ruler; denominator) | R² of means | `frac_r2_closed` | mean_js |
|---|---|---|---|---|---|---|---|---|
| M2 | IMPACT | **0.117** | 0.094 | **1.76** | 0.776 (0.225) | 0.929 | 0.854 | 0.451 |
| M2 | paper VAE | 0.124 | 0.101 | 2.73 | 0.498 (0.157) | 0.803 | 0.563 | **0.111** |
| M2 | AE-scGen | 0.162 | 0.139 | 2.45 | 0.575 (0.225) | **0.949** | **0.899** | 0.485 |
| M1 | IMPACT | **0.104** | 0.080 | **1.29** | 0.897 (0.225) | 0.918 | 0.832 | 0.449 |
| M1 | paper VAE | 0.129 | 0.106 | 2.67 | 0.506 (0.164) | 0.805 | 0.572 | **0.108** |
| M1 | AE-scGen | 0.173 | 0.150 | 2.15 | 0.588 (0.225) | **0.929** | **0.857** | 0.502 |

Sources: APVR `metrics.json`; HUB/hvg_pearson_residuals_m{1,2}_v08_ood/{impact_cellot,scgen}/evals_ood_data_space/*.csv [R]; differences and ratios computed here [I]. Same OOD cells, same genes, same MMD code (see Setup) [R][I]. What it shows [I]:
- On absolute MMD to the real human cells, the paper VAE sits between IMPACT and AE-scGen on both cuts.
- On model/own floor, it is last. The repo's rule for models with different AE floors is to rank on absolute MMD, gap above floor and model/floor (CF:642) [D]; here those give different orders.
- Its decoded fraction is last, but it is read off a shorter ruler (denominator 0.157–0.164 vs 0.225; CF:633) [R][D], so it should not be ranked against the hub fractions. The canvases' verdict "near AE-scGen, below IMPACT" rests on exactly that ranking; on absolute MMD the VAE is closer to the human cells than AE-scGen on both cuts.
- Its mean R² is clearly worst: it closes 56–57% of the mouse–human mean gap, against 83–90% for the hub models.
- Its far lower `mean_js` most likely comes from its ReLU output layer, which can output exact zeros: held-out human reconstructions are 67–68% zeros (true 76%) for the paper VAE and 0% for the hub AE (APVR `recon_identity_pergene.csv`; HUB/.../scgen/ae_identity/ae_identity_metrics.csv; VAE:118; ae.py:85) [R][C]. The zero fraction of the transported predictions themselves was not measured, so this explanation is [I].

**Identity audit, 07-27 (job 35538746, "Track B" of the AE study).** The two checkpoints were restored without retraining and scored with the five-axis reconstruction panel of the LPS work (APV/scripts/03_identity_audit.py; fasrc:BK/sbatch/lps/atlas_paper_vae_identity_audit.sbatch) [C]; it took about 3 minutes (L0727:287-291; APVL file times 14:57–15:00) [D][R]. Held-out slices, deterministic decode(μ(x)), next to the hub AE's sidecars written on 07-30:

| slice | stack | paired-cell Pearson² per gene (mean) | COD per gene (median) | reconstruction MMD, n = 80 | zeros in reconstruction (true) |
|---|---|---|---|---|---|
| M1 human OOD | paper VAE | 0.353 | 0.245 | 0.050 | 0.68 (0.76) |
| M1 human OOD | hub AE | 0.235 | 0.156 | 0.080 | 0.00 (0.76) |
| M2 human OOD | paper VAE | 0.357 | 0.245 | 0.043 | 0.67 (0.76) |
| M2 human OOD | hub AE | 0.247 | 0.169 | 0.066 | 0.00 (0.76) |
| M2 mouse OOD | paper VAE | 0.206 | −0.005 | 0.067 | 0.77 (0.84) |
| M2 mouse OOD | hub AE | 0.075 | −0.030 | 0.145 | 0.00 (0.84) |

Sources: APVR `recon_identity_extended.json`, `recon_identity_pergene.csv`; HUB/hvg_pearson_residuals_m{1,2}_v08_ood/scgen/ae_identity/ae_identity_metrics.csv. The hub script imports the same metric helpers (conny:cellot/cellot_gpu/scripts/ae_identity_metrics.py:25, 61) [R][C]. COD (coefficient of determination, 1 − SSE/SST) is per gene. So the paper VAE reconstructs held-out monocytes better than the hub AE on every axis shown, yet transfers the species shift worse on mean R² [R][I]. The six atlas rows of the Track B table in the log (L0727:302-307) match the two JSON files [R]; its three LPS rows (L0727:299-301) come from the Stage-0 audit and were not re-checked here. The Track B canvas `ae-identity-cross-dataset-metrics.canvas.tsx` (CV, 07-27 15:03) carries the same atlas values [D].

Later reuse: the 07-27…07-29 calibration study re-scored Plan C's saved predictions ([F15](F15-ae-repair-rounds-and-calibration.md)). Its seed sweep gives the only noise estimate for these numbers: over 5 MMD subsampling seeds at n = 80, fgc_dec ranged 0.5017–0.5091 (M1) and 0.4965–0.5056 (M2), and model MMD 0.1286–0.1308 and 0.1210–0.1244; R² of means was identical in every seed, and seed 0 reproduces `metrics.json` (PHA, rows `variant = raw_prediction`) [R]. Model/floor ranged 2.63–2.74 (M1) and 2.64–2.80 (M2), because the floor estimate itself moves (0.0478–0.0490 and 0.0440–0.0470) [R]. The E3 re-scoring of 07-27 used yet another draw and reports 2.60 and 2.83 (`fasrc:BK/scgen-cellot-ablation/results/transport_calibration/atlas_m{1,2}_transport.json`; L0727:620-623) [R][D]; these are the same predictions, not different models. This is metric noise only; the VAE was trained once per cut [R]. No comparable noise estimate exists for the two hub models [not found].

### Plan D — unbalanced OT, Option A (07-21)

Design (DD; UNB/README.md; UNB/PLAN.md) [D][C]:
- Freeze target: the LPS rat task with its frozen AE; the atlas M2 cut was rejected to avoid "ownership collision" with Plan B (DD:11-20) [D].
- Balanced reference: production IMPACT fgc_dec 0.0759 at n = 80, 0.0918 at 500, 0.0910 at 1000 (DD:28-32), which matches the result file (HUB/paper_crossspecies_rat_ood/impact_cellot/evals_ood_data_space_paper/decoded_frame_metrics.csv) [R]. Allowed deviation for a retrain: |Δ| ≤ 0.03 (DD:35) [D], not derived from any rerun [I].
- Weights: `uniform`, `louvain_match` or `density_ratio`, blended as w = (1 − α)·uniform + α·w_method (UNB/uot/reweight.py:83-87) [C]. `louvain_match` pushes both sides toward the geometric mean of their Louvain-cluster compositions (Louvain = graph-based cell clusters) and gives clusters present on one side only a weight of 1e-3 (reweight.py:90-137) [C]. `density_ratio` uses k-nearest-neighbour distances in the frozen AE codes (reweight.py:140-174) [C].
- Mass-aware sidecar: `effective_kept_mass` (effective sample size of the source weights divided by n), weight entropy, and a composition-matched MMD (DD:58-64; UNB/metrics/uot_aware.py:41-134) [C].
- Synthetic proof: a 2-D toy with four Gaussian cell types, a known affine map, skewed compositions and a mouse-only blob, solved with balanced and unbalanced Sinkhorn (entropic OT) and a barycentric map, with six pass/fail checks (UNB/synthetic/toy_data.py; run_synthetic.py:30-92, 164-179) [C]. DD:38, DD:103 and UNB/README.md:10 say the checks pass [D]. The CSV they cite (`synthetic/results/synthetic_guards.csv`) and the figure `synthetic_mechanism.png` are in neither git nor BK [not found], so no number survives.

Runs (SACCT; UNB/scripts/sbatch_option_a_train.sh:11, 32-38) [R][C]:

| job | arm | submitted (07-21) | final run | preempted runs | total run time | state |
|---|---|---|---|---|---|---|
| 33886063_0 | `balanced_parity` (no weights) | 10:50:57 | 18:14 → 19:17 | 3 | 2.9 h | COMPLETED |
| 33886063_1 | `louvain_match`, α = 0.25 | 10:50:57 | 16:17 → 18:47 | 1 | 3.0 h | COMPLETED |
| 33886063_2 | `louvain_match`, α = 0.5 | 10:50:57 | 21:53 → 22:07 | 3 | 2.9 h | COMPLETED |
| 33886063_3 | `louvain_match`, α = 1 | 10:50:57 | 18:14 → 20:44 | 2 | 3.1 h | COMPLETED |
| 33887334 (`uotA_dens`) | `density_ratio`, α = 1 [I from folder name] | 10:53:55 | 16:17 → 19:11 | 0 | 2.9 h | COMPLETED |

The `gpu_requeue` partition preempts jobs; the training script resumes from `cache/last.pt` (train_option_a.py:174, 214) [C]. For the four array tasks, `set -euo pipefail` (sbatch:20) means that COMPLETED implies training and the evaluation chain both exited without error [I]. The density job's script is in neither git nor BK [not found].

What is left:
- DD's comparison table has "TBD" in every Option-A row, and its checklist item "GPU α-sweep submitted + table filled" is unticked (DD:70-95) [D]. The README still says "in progress" (UNB/README.md:11), and PLAN.md says the sweep is "not yet submitted" (UNB/PLAN.md:3-7) [D]. All were written before, or never updated after, the 10:50 submission, and were committed unchanged on 07-30 [I][G].
- The kept-mass values in DD:77-81 (1.000, 0.947, 0.816, 0.526) describe the weight files, not trained models (uot_aware.py:106-134) [C][D]; the weight files are lost (UNB-BK `results/lps_rat/weights/` is empty) [R].
- On 07-30 the folder held 113 MB, with 112 MB of `results/` and four large `.err` logs (L0730:237-250) [D]. In BK it holds 0 files and one broken symlink, `results/lps_rat/model-scgen`, created 07-21 18:41 by the evaluation step (UNB-BK; eval_option_a.py:145-151) [R][C]. Each arm's run folder was last changed about six minutes before its job ended, and each `evals_ood_data_space/` folder at the minute the job ended (19:17, 18:47, 22:07, 20:44, 19:11) (UNB-BK; SACCT) [R]. So the evaluation chain wrote files into every arm [I].
- The loss is not specific to Plan D. In BK, every top-level folder from `scgen-cellot-unbalanced/` onward in alphabetical order (`scgen-cellot-unbalanced`, `scgen-reproducibility`, `scripts`, `specs`, `speciesOT`, `src`, `tb`) holds directories but 0 files, while the folders before it are complete; BK's git index lists 272 tracked files as missing from its working tree, all of them in these folders (21 in `scgen-cellot-unbalanced`, 210 in `speciesOT`, 20 in `scripts`, 15 in `specs`, 4 in `tb`, 2 in `src`) (ssh `find` counts and `git ls-files --deleted` in BK, 2026-10-20) [R]. The Plan D result folders keep their July modification times, and deleting a file changes its folder's time, so the files were most likely never copied into the backup rather than deleted beforehand [I]. conny:docs/archaeology/sources.md:65 already lists three of these folders as empty skeletons [D].
- No document or canvas reports any Option-A number (searched: git, BK text files, Josh's repository, CV) [not found].
- The composition-matched MMD could not have been produced by this chain. It needs `treated_louvain` in `eval_clouds.npz` (eval_option_a.py:99-106), no script writes that array (conny:cellot/cellot_gpu/scripts/dump_eval_clouds.py:78), and the sidecar is written before `evaluate.py` even runs (eval_option_a.py:111-118 vs 144-154) [C].

07-23: "Unbalanced OT stays paused" (L0723:7) [D]. 07-30: the code was committed as "the paused unbalanced-OT line, committed to preserve the code" (conny@4244985) [G].

## Verdict

- **A** is an accurate summary of existing single-seed results; every number checked matches its file [R]. It is not new evidence.
- **B's** answer, "IMPACT beats AE-scGen on the decoded score for M1 and M2", is what the files say, and it also holds on absolute MMD and model/floor [R]. AE-scGen keeps a small mean-R² edge [R]. The evidence is moderate: one unseeded training run per model, one split, 365–401 evaluation cells, and M1/M2 share all cells and 999 of 1,000 genes, so they are not independent replicates [R][C][I].
- **C** shows that the original scGen VAE with a single species shift trains in about 11 minutes on CPU on the atlas and reconstructs held-out monocytes better than the hub AE [R]. As a predictor it does not beat IMPACT in any MMD view. It beats AE-scGen on absolute MMD but loses on model/floor and clearly on mean R² (0.80 vs 0.93–0.95) [R][I]. These orderings hold across the 5 MMD seeds of PHA (model/floor 2.63–2.80 vs AE-scGen's 2.15/2.45) [R], but the hub numbers have no noise estimate. The only written comparison, in the 07-21 canvases ("close but not ahead", "near hub AE"), ranks fractions measured on different rulers and is not supported as stated [D][I]. Evidence: one unseeded run per cut; the metric noise is small (fgc_dec stays within 0.008 of the seed-0 value across 5 MMD seeds) [R]. Nothing can be said about OT in the VAE latent space: it was never run [not found].
- **D** yields no real-data conclusion. The design and code exist and the jobs ran, but the outputs and any reading of them are lost [R][D]. Its status is "abandoned unfinished".

## Why it stopped

- A and B were one-shot deliverables, finished on 07-21 [D].
- C: no stated reason. Its checkpoints were taken up by the bounded AE study (audit 07-27, calibration 07-27…07-29; [F15](F15-ae-repair-rounds-and-calibration.md)) [D][R]. Of Phase 2, only the canvases were made (CV, 07-21) [R]; the matched comparison and VAE-latent IMPACT were not found [not found].
- D: stated reason, 07-23: "Unbalanced OT stays paused … If full-cloud fidelity is required, a bounded AE repair study is warranted before adding an unbalanced-OT degree of freedom" (L0723:7, 18-19) [D]; repeated in L0727:14 and conny:AGENTS.md:144 [D].
- What the record suggests [I]: the plans were a one-day sprint. From 07-23 attention moved to the autoencoder. D's results seem never to have been opened: no log, deliverable or canvas mentions them. D's baseline on its chosen task already lost to the linear shift (0.076 vs 0.276) [R], and the day before, the 07-20 log had called chasing the LPS Fig. 4 replication an `infinite game` (L0720:34, 40-45) [D].

## Problems in how it was done

- **D's outputs are lost and were never recorded.** No Option-A result can be checked; the go/no-go in DD:99-108 stays "provisional" (UNB-BK; L0730:237-250) [R][D]. The results were gitignored (conny:.gitignore:53) [C] and the backup has a gap that covers this whole folder (see Plan D above) [R], so no copy is known [I].
- **D's documents contradict the Slurm record.** DD, the README and PLAN.md describe the sweep as not yet submitted, while all five jobs had completed by 22:07 (DD:72, 94; UNB/README.md:11; UNB/PLAN.md:5-6; SACCT) [D][R]. conny:docs/archaeology/timeline.md:115 and sources.md:65 say four jobs; there were five, counting `uotA_dens` [R].
- **D's mass-aware metric was not computable as wired**, so the only "mass-aware" numbers would have been statistics of the weights, which say nothing about the trained map (eval_option_a.py:99-118; dump_eval_clouds.py:78) [C][I].
- **D's `--seed 0` does not make its arms reproducible.** Four of the five jobs were preempted 1–3 times and resumed from `cache/last.pt` (SACCT; train_option_a.py:174, 214). The checkpoint stores weights, optimiser state and step but no random state, and the seed is re-set at every restart (train_option_a.py:169-171, 196-205), so each resumed run repeats random draws and the arms are not comparable seeded runs [C][R][I].
- **D's synthetic "Option-A bridge" uses the unbalanced solver's own kept mass as weights** (run_synthetic.py:54-63), not the `louvain_match`/`density_ratio` estimators used on real data. It does not validate them [C][I].
- **D tested the stimulation axis, with a baseline that already lost to the mean shift** (fgc_dec 0.076 vs 0.276, see "Before the plans") [R]. UNB/PLAN.md:53-55 says the composition argument is "strongest on the species axis" [D]. On the atlas it is weak: species have equal counts per cell type by construction (legacy `obs.csv`) [R][I].
- **D's `parity gate` (the rule that the balanced retrain must reproduce production IMPACT within 0.03) was set without measured rerun noise**, and it compares a seeded retrain with an unseeded original (DD:34-36; train_option_a.py:169) [D][C]. Only its n = 80 value could have been checked: the Option-A chain scores decoded n = 30, 50, 80 in a different evaluation folder, while DD's 500 and 1000 references come from the production `_paper` evaluation (eval_option_a.py:131-138; HUB/paper_crossspecies_rat_ood/impact_cellot/evals_ood_data_space_paper/) [C][R].
- **C was compared with B only on the decoded fraction, which must not be ranked across different AE floors** (CF:625-642). The plan itself prescribed that comparison (DC:195; APV/README.md:38-39), and the 07-21 canvases concluded "close but not ahead" / "near hub AE" from it (CV) [D]. On absolute MMD the VAE beats AE-scGen, so the canvas verdict depends on the wrong ruler [R][I]. L0727:144-157 also placed the VAE's +0.51/+0.50 in a cross-dataset table and later corrected the framing (L0727:159-172) [D].
- **`mean_js` is not comparable across stacks** with different output layers (ReLU vs linear: 67–68% vs 0% zeros) [R][C]. Used as a `guardrail` (the repo's word for a secondary check beside the headline metric, conny:AGENTS.md:35-36), JS then mostly measures the output layer [I].
- **Single runs, no training seeds** in either atlas stack (see Setup) [C]. On LPS, three runs of the paper recipe differed by about 0.085 in DEG R² (L0727:268-275; not re-checked here, see F15) [D]. No model-vs-model gap here has an error bar for training noise, and the hub numbers have no metric-noise estimate either (PHA covers only the paper VAE) [R].
- **C's train split is not the hub's.** The sizes are close (5,802 vs 5,798 cells on M2), but about 19% of the train cells differ (4,722 shared on M2, 4,765 on M1), because the paper-VAE scripts split all cells at once instead of per species (`groupby: condition`) (01_train_vae.py:45-61; APVR `split.csv` vs HUB ae_identity_percell.csv) [C][R]. DC:159 required "the same toggle_ood logic"; only the OOD half matches [D][R]. The δ and the VAE are therefore fitted on partly different cells than AE-scGen's.
- **The Track B finding "COD swings −0.30 vs +0.23" (L0727:344-349) comes from one gene**: M1 human OOD has one gene with COD −451; without it the mean is +0.24, and the COD medians are equal (0.245 and 0.245) (APVR `recon_identity_extended.json`, `recon_identity_pergene.csv`) [R]. The log's explanation (amplitude sensitivity on small slices) is incomplete; medians are safer, as the 07-30 hub script also notes (conny:cellot/cellot_gpu/scripts/ae_identity_metrics.py:18-23) [C].
- **Deliverables depend on Cursor canvases outside version control** (DA:5-6, DB:5, DC:194). They survive only in Conny's FASRC home (CV), not in git or BK [R], and the Option-A canvas suggested in PD:97 was never made [not found].

## Terms used here

- **Plan A / B / C / D**: the four agent task files of 2026-07-21 (PL/README.md:5-10).
- **`fence`**: rule that Plan C must not write into the hub's v08 `scgen/` or `impact_cellot/` folders (PL/README.md:12; PC:45-54).
- **M1 / M2**: v08 atlas cuts holding out non-classical monocytes (M1), or non-classical plus generic monocytes (M2).
- **CD8 uncapped (`a_uncapped`)**: v08 cut holding out CD8 T cells from the full, uncapped atlas.
- **v08**: the frozen atlas preprocessing version (Chromium only, species-stratified OOD split); see F10.
- **hub (`./hub`)**: Conny's command-line tool that generates, runs and scores CellOT experiments ([F09](F09-hub-and-metrics-infrastructure.md)).
- **AE-scGen / hub scGen**: CellOT-repo autoencoder with `beta: 0` plus a latent mean shift; not the scGen VAE.
- **paper VAE / `VAEArith`**: the original TensorFlow scGen VAE code (theislab).
- **IMPACT / IMPACT_CellOT**: CellOT's ICNN transport map on the hub AE's codes, used mouse → human.
- **`north-star`**: the repo's name for its headline metric, `frac_gap_closed_decoded`.
- **fgc_dec / fgc_raw / fr2_dec**: `frac_gap_closed` in the decoded or raw frame; `frac_r2_closed_decoded`.
- **model/floor**: model MMD divided by the model's own decoded floor (its reconstruction MMD).
- **`AE round-trip tax`**: the repo's name for the MMD error added by encoding and decoding cells.
- **`single_species_delta`**: Plan C's prediction rule, one latent shift from mouse to human.
- **legacy pack**: `X.npz` + `obs.csv` + `var.csv` export of a v08 `.h5ad` for the old anndata in `scgen_tf1`.
- **Track B**: the 07-27 identity audit of Plan C's checkpoints (no retraining).
- **Option A / B / C**: UOT routes in UNB/PLAN.md §4: reweight then balanced CellOT / entropic UOT solver / unbalanced ICNN.
- **α (alpha)**: blend between uniform weights (0) and full reweighting (1).
- **`louvain_match` / `density_ratio`**: Option-A weight estimators (cluster proportions / kNN density ratio).
- **`parity gate`**: the requirement that the balanced retrain reproduce production IMPACT within 0.03.
- **`effective_kept_mass`**: effective sample size of the source weights divided by the number of cells.
- **`infinite game`**: the 07-20 log's term for open-ended work to stop.
- **Stage 0**: the scGen Fig. 5 LPS replication with the TensorFlow VAE ([F12](F12-scgen-fig5-stage0-and-stage1.md)).

## What the package needs from this

1. **Model-free metric reference on the v08 OOD cells (recommended).** Inputs: `fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m{1,2}_v08.h5ad` (or the legacy pack); OOD cells = rows with `split == "ood"` in APVR `split.csv`. Config: raw floor = split-half MMD of the human OOD cells, ceiling = MMD(mouse OOD, human OOD), biased RBF MMD over `logspace(1,-3,50)`, n = 30, 50, 80 drawn in that order, 10 repetitions, `numpy.random.default_rng(0)` created per call (HM:73-128) [C]. Expected at n = 80: M2 floor 0.0232675, ceiling 0.1061868, `r2_identity` 0.5589876, `r2_self` 0.9924411; M1 floor 0.0236093, ceiling 0.1087470, `r2_identity` 0.5541515, `r2_self` 0.9917168 (APVR `metrics.json`; HUB/.../extended_metrics.csv) [R]. Tolerance: two separate implementations of the same procedure (hub `extended_metrics.py`, HM) agree within 4e-8 [R], so 1e-6 is safe if the package reproduces the subsampling exactly. With other random draws, PHA's 5-seed ranges for model MMD and the decoded floor are up to about 0.003 wide at n = 80 [R]; the raw floor and ceiling were not re-drawn there, so treat ±0.003 as a rough guide for them [I]. Both h5ad files are in BK (32.9 MB each, `ls` over ssh) [R].
2. **Re-scoring a saved prediction.** Input: APVR `pred_single_species_delta.h5ad` (written 07-21, APVL `train_33885331.out`; still used 07-27, L0727:584-585 [D]; present in BK, 805 KB for M1 and 878 KB for M2, `ls` over ssh [R]). Expected raw-frame values at n = 80, seed 0: M2 MMD 0.124112, R² of means 0.803171, `mean_js` 0.111438, `frac_gap_closed` −0.216172; M1 0.129217, 0.804537, 0.108481, −0.240430 (APVR `metrics.json`) [R]. Tolerance: R² and JS are deterministic and were reproduced exactly by a later re-scoring (`fasrc:BK/scgen-cellot-ablation/results/transport_calibration/atlas_m{1,2}_transport.json`) [R]; MMD ±0.003 across seeds (PHA) [R]. The decoded values (fgc_dec 0.506 / 0.498; 0.5017–0.5091 / 0.4965–0.5056 across 5 seeds, PHA) also need the TensorFlow checkpoint (`model/scgen.*`, present in BK; SHA-256 in APVR `audit_manifest.json`) [R]. Use them only if the package can run or port TF1 weights.
3. **Plan B's scoreboard** (fgc_dec M2 0.776 / 0.575, M1 0.897 / 0.588 [R]) is the v08 regression target; see F10. The record gives no training-noise tolerance for it. The saved predictions and AE checkpoints of all four runs are in BK (`evals_ood_data_space/imputed.h5ad`, `eval_clouds.npz`, `cache/model.pt`; `ls` over ssh) [R], so the package can re-score them without retraining.
4. **Not worth reproducing as a numeric reference:** retraining the paper VAE (TF1, unseeded, one run; only a loose sanity range is supported, e.g. R² of means ≈ 0.80 and held-out human paired Pearson² ≈ 0.35 [R]). Also Plan D: no output survives, and the seeded toy's expected values are not in the record. UNB/scripts/test_reweight_unit.py is a usable code test if the package ever adds reweighting [C].

## Open questions

- Does any other copy of the original working tree exist, made before the 10-01 backup? The backup lacks every file in `scgen-cellot-unbalanced/` and six later folders; how the backup was made is not recorded. Did anyone look at Plan D's outputs? No document cites a number.
- What exactly did job 33887334 (`uotA_dens`) run? Its script was not found (it may have been one of the lost files in UNB-BK `scripts/`).
- What were the five figures of 07-21 12:39 in fasrc:BK/.cursor-assets/ (`failure-1-loss-vs-mmd.png` … `failure-5-unexplored.png`) made for? No canvas in CV refers to them (`grep` for `.png` and `failure-`), and every 07-21 canvas was last saved before 12:39 (CV, file times) [R].
- Why does the paper VAE reconstruct held-out monocytes better than the hub AE but transfer the species shift worse on mean R² (0.80 vs 0.93–0.95)?
- How much of the `mean_js` gap (0.11 vs 0.45–0.50) is the output layer, and how much is real marginal fit?
- What is the training-seed noise of all three atlas models?
- Did Josh read Deliverables A and B? No record was found.

## Sources

Git (local clone conny:, branch with main 109bf12): PL/README.md, PA, PB, PC, PD, DA, DB, DC, DD; APV/README.md, APV/configs/m1_v08.yaml, m2_v08.yaml, APV/scripts/_data.py, 00_dry_run_split.py, 01_train_vae.py, 02_eval_metrics.py, 03_identity_audit.py, run_train_eval.sbatch, run_train_eval_m1.sbatch, submit_train.sh; conny:specs/atlas_paper_vae_m1_v08.yaml, atlas_paper_vae_m2_v08.yaml; UNB/README.md, PLAN.md, DELIVERABLE_D_option_a.md (identical to DD), honest_metrics.py (compared with HM), uot/reweight.py, uot/__init__.py, metrics/uot_aware.py, scripts/estimate_weights.py, train_option_a.py, eval_option_a.py, print_sbatch_chain.sh, sbatch_option_a_train.sh, test_reweight_unit.py, synthetic/guards.py, run_synthetic.py, toy_data.py, ot_solvers.py, brenier_illustration.py (header), configs/option_a/lps_rat_balanced.yaml, lps_rat_smoke.yaml; L0720, L0723, L0727, L0730 (lines 183-330, 420-520, 655-700); conny:logs/research_logs/research_log_2026-07-30_env_modernization.txt (search only); CF (lines 612-660, 747-782); conny:AGENTS.md:25-60, 105-144; conny:cellot/cellot_gpu/cellot/data/cell.py:250-398; cellot/models/ae.py:85, 175-187; cellot/losses/divergence.py; cellot/utils/evaluate.py:60-130; scripts/extended_metrics.py; scripts/evaluate.py:100-175; scripts/decoded_frame_metrics.py:1-150; scripts/dump_eval_clouds.py:1-88; scripts/ae_identity_metrics.py:1-70; scripts/train.py (seed search); conny:speciesOT/baseline/analysis/v08_scorecard_dual.csv; conny:.gitignore:50-53; conny:README.md:90; conny@4244985 and conny@fe856aa (`git show --stat`, `git log`); conny:docs/archaeology/inventory.csv, sources.md (incl. lines 60-65), timeline.md (incl. lines 111-118), metrics.md, experiments/F08-hvg-flavor-matrix.md (style and split notes); conny:docs/hub_usage.md:320-340 (search hit only).

Other repositories: HM and its `git log` (autoresearch@5d1a7d9); Josh's repository, branches main, cellot, src, junyi-r2-evaluation, MMDEv_Test, scgen-model-impl and junyi (`git grep` only: no F14 files beyond the copy of Conny's history on `junyi`; josh@main:e11_otdd_standard.ipynb has Josh's own earlier unbalanced entropic OT cost, which Plan D does not reference); the AI-built package (ref origin/src) and conny origin/pr-6-reference-bundle (`git grep` only, nothing relevant).

FASRC mirror (cited as fasrc:BK/<path>): APVR `metrics.json`, `split.csv`, `dry_run_split.txt` (m2), `model/training_log.csv`, `recon_identity_extended.json`, `recon_identity_pergene.csv`, `audit_manifest.json` (both cuts); `fasrc:BK/atlas-paper-vae/data/{m1,m2}_v08_legacy/` (obs.csv, var.csv, README.txt); APVL `train_33884167.*`, `train_33885331.*`, `train_m1_33898362.*`, `identity_audit_35538746_{1,2}.*`; fasrc:BK/sbatch/lps/atlas_paper_vae_identity_audit.sbatch; VAE (and its diff with `mac:scGen v.s. CellOT/scgen-reproducibility/code/scgen/models/_vae.py`); `fasrc:BK/scgen-cellot-ablation/results/transport_calibration/atlas_{m1,m2}_transport.json`; PHA; HUB/hvg_pearson_residuals_{m1,m2}_v08_ood/{impact_cellot,scgen}/config.yaml and evals_ood_data_space/{evals,extended_metrics,decoded_frame_metrics}.csv; HUB/hvg_pearson_residuals_{m1,m2}_v08_ood/scgen/ae_identity/{ae_identity_metrics.csv, ae_identity_pergene.csv, ae_identity_percell.csv (cell IDs per slice), ae_identity_manifest.json}; `fasrc:BK/scgen-cellot-ablation/results/transport_calibration/atlas_{m1,m2}_transport.csv`; HUB/hvg_pearson_residuals_a_uncapped_v08_ood/{impact_cellot,scgen}/evals_ood_data_space/*.csv; HUB/paper_crossspecies_rat_ood/{impact_cellot,scgen}/config.yaml and evals_ood_data_space_paper/{decoded_frame_metrics,extended_metrics}.csv; fasrc:BK/AGENTS.md (identical to conny:AGENTS.md); fasrc:BK/logs/research_logs/agent_plans_2026-07-21/ (identical to PL) and research_log_2026-07-30_repo_plan.txt; fasrc:BK/.cursor-assets/ (listing; two figures viewed); fasrc:BK/logs/ and fasrc:BK/sbatch/ (listings and file times).

FASRC directly (ssh): UNB-BK (`ls -la`, `find -maxdepth 6` with types and times, `find -type f`/`-type l` counts); SACCT for 2026-07-21…22 with requeue history (`sacct -u jzhou1125 -X -D`, re-run in the verification pass, all job times in the tables re-checked). The first author's later ssh attempt failed with a multiplexing and then an authentication error; the verification pass on 2026-10-20 had working ssh and added: CV listing and `cat`/`grep`/`sed` of `atlas-paper-vae-m2-v08-metrics.canvas.tsx`, `atlas-paper-vae-m1-v08-metrics.canvas.tsx`, `atlas-m1-v08-metrics.canvas.tsx`, `atlas-m2-v08-metrics.canvas.tsx`, `atlas-v08-memory-pack.canvas.tsx`, `speciesot-journeys-so-far.canvas.tsx`, `ae-identity-cross-dataset-metrics.canvas.tsx`; `ls` of APVR and its `model/` folders, `fasrc:BK/atlas-paper-vae/data/{m1,m2}_v08_legacy/`, fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/ (v08 files), HUB/hvg_pearson_residuals_m{1,2}_v08_ood/{scgen,impact_cellot}/{evals_ood_data_space,cache}/; file counts of BK top-level folders; in BK's git: `git log -g HEAD` (reflog), `git ls-files scgen-cellot-unbalanced`, `git ls-files --deleted`; `ls` of /n/holylabs/mooney_lab/Lab/junyizhou/.

Papers: scGen (Lotfollahi et al. 2019), cross-species section [P]; CellOT (Bunne et al. 2023), Methods, "Hyperparameters" and the scRNA paragraph before it [P].
