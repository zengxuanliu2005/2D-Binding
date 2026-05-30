# ξ_RL fit replication — PhD's 2-step protocol

## Step 1: Unconstrained Hu fit

| system | K2D,max (nm²) | ξ_RL (nm) | n_data |
|---|---:|---:|---:|
| result_K100.tsv | 11889.4 ± 350.6 | 0.6848 ± 0.0291 | 13 |
| result_K10.tsv | 776.7 ± 10.9 | 2.0755 ± 0.0903 | 16 |
| result_K1.tsv | 324.5 ± 8.9 | 2.2531 ± 0.1833 | 18 |

## Step 2: Per-#bonds K2D,max (ξ_RL fixed from Step 1)


### result_K100.tsv (ξ_RL = 0.6848 nm fixed)

| #bonds | K2D,max (nm²) | RMSE | n_pts |
|---|---:|---:|---:|
| 2 | 12020.0 | 0.0 | 1 |
| 5 | 11527.9 | 0.0 | 1 |
| 6 | 11994.2 | 0.0 | 1 |
| 7 | 11934.7 | 158.5 | 2 |
| 8 | 11518.3 | 16.9 | 2 |
| 9 | 12293.0 | 56.3 | 2 |
| 10 | 11487.8 | 184.1 | 2 |
| 11 | 12463.6 | 0.0 | 1 |
| 12 | 12424.0 | 0.0 | 1 |

**Mean across transitions:** 11962.6 ± 385.7 nm²

### result_K10.tsv (ξ_RL = 2.0755 nm fixed)

| #bonds | K2D,max (nm²) | RMSE | n_pts |
|---|---:|---:|---:|
| 2 | 772.5 | 0.0 | 1 |
| 3 | 762.6 | 10.7 | 6 |
| 4 | 782.8 | 15.8 | 5 |
| 5 | 792.9 | 3.6 | 4 |

**Mean across transitions:** 777.7 ± 13.1 nm²

### result_K1.tsv (ξ_RL = 2.2531 nm fixed)

| #bonds | K2D,max (nm²) | RMSE | n_pts |
|---|---:|---:|---:|
| 1 | 301.4 | 0.0 | 1 |
| 2 | 318.0 | 3.0 | 2 |
| 3 | 314.6 | 11.0 | 3 |
| 4 | 326.3 | 13.6 | 4 |
| 5 | 332.8 | 15.1 | 4 |
| 6 | 337.8 | 11.9 | 4 |

**Mean across transitions:** 321.8 ± 13.3 nm²

## Comparison to PhD's published values

| system | ξ_RL fit (ours) | ξ_RL PhD | Δ | K2D,max fit (ours, mean) | K2D,max PhD | Δ% |
|---|---:|---:|---:|---:|---:|---:|
| result_K100.tsv | 0.6848 | 0.68 | 0.0048 | 11962.6 | 12705 | 5.8% |
| result_K10.tsv | 2.0755 | 2.08 | 0.0045 | 777.7 | 875 | 11.1% |
| result_K1.tsv | 2.2531 | 2.25 | 0.0031 | 321.8 | 362 | 11.1% |
