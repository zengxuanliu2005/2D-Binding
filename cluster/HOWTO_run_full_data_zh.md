---
purpose: "Chinese walkthrough for running the full-data analysis bundle on the off-site cluster"
audience: off-site collaborator (after receiving cluster-bundle-<date>-<sha>.tgz)
status: current
---

# 2D-Binding 全量数据复跑包

> **From Claude (代 Zengxuan)**
>
> 数据持有方您好！这是一个自包含的分析包，把它解压到你 MD 数据所在的根目录就能跑。
> 它会扫描所有 `<体系>/s001`, `<体系>/s002`, ... 续跑文件夹，把每个 replica 的 chain
> 坐标抽出来 → 全部 concat 起来 → 跑 4 个分析（closure_four_term 四项分解、closure_wlc_three_term
> 三项 WLC、raw_tether_partition K2D、diagnose bound vs unbound 偏倚）→ 输出 distilled
> 表格 (~5 MB)。你只需要把 `distilled/` 整个发回给 Zengxuan 就行，不用传 GB 级的中
> 间 npz。
>
> 目的：测试我们的猜想 —— "PPT s25 数和我 s001 数差 1.5-2 kBT 是不是因为我数据少"。
> 如果用你全量数据跑完和 PPT s25 收敛，那答案就是"是"，s001 单 replica 不够；
> 如果还是差很多，那就是公式或参数选择的问题，我们再深挖。

## 一、解压

把 `cluster-bundle-<date>-<sha>.tgz` 拷到你 MD 数据根目录（**即下面有 `15_120x120_K100_EPS05/` 这样子目录的位置**）：

```bash
cd /path/to/your/MD/data/root
tar xzf cluster-bundle-<date>-<sha>.tgz
ls cluster/                    # 应该看到 run_config.sh / slurm/ / scripts/ 等
```

## 二、改 run_config.sh（**只需改这一个文件**）

```bash
vim cluster/run_config.sh
```

需要确认 / 改的字段（顶部那几行）：

| 字段 | 默认值 | 干什么 |
|---|---|---|
| `MD_PARENT` | `/path/to/your/MD/data/root` | **必填** — 你 MD 数据根目录的绝对路径 |
| `SYSTEMS_DIRS` | `15_120x120_K100_EPS05` 等 3 个 | 如果你三个体系的目录名不一样，改这里 |
| `N_JOBS` | 8 | 并行进程数 (16 核机器可调到 16) |
| `N_BOOTSTRAP` | 200 | bootstrap 次数；默认即可 |
| `SLURM_PARTITION` | `gpu` | 你 cluster 的 partition 名（**如果你 cluster partition 不叫 gpu 必改**） |
| `SLURM_NODE` | `n01` | 指定节点；如果不需要指定可注释掉 |
| `SLURM_TIME` | `24:00:00` | wall time |
| `SLURM_MEM` | `32G` | 内存 |
| `SLURM_CPUS` | 8 | 每个 job 用几个 CPU（**应该 ≥ N_JOBS**） |
| `PY_ENVS` | `phys base` | conda env 候选，第一个 import 成功的就用 |

## 三、提交 SLURM job

```bash
cd /path/to/your/MD/data/root     # 也就是 cluster/ 的父目录
sbatch cluster/slurm/full_analysis.slurm
```

job 进度看：

```bash
squeue -u $USER                              # job 还在没在
tail -f cluster/outputs/slurm-<job_id>.log   # 实时输出
```

预计 wall time：
- extract 每个 replica ~30 s，单核。如果你有 100 个 replicas × 3 体系 → 总 ~150 min 单核。脚本会用 8 工人并行 → **~20 min**。
- merge 三体系 ~1 min
- 分析 4 项 ~5 min（bootstrap n=200，并行 8 工人）

**总：约 30 分钟**，主要是 I/O 等。

## 四、发回 Zengxuan 什么

跑完后 `cluster/outputs/distilled/` 目录里：

```
cluster/outputs/distilled/
├── inventory.tsv                       # 每个体系实际找到几个 replicas
├── closure_four_term_data.md + .npz    # 四项 ΔΔF 分解 + bootstrap σ
├── closure_wlc_three_term.md + .npz    # 三项 WLC + bootstrap σ
├── raw_tether_partition.md + .npz      # rigid 绝对 K2D + bootstrap
├── diagnose_bias.txt                   # bound vs unbound 几何对比表
├── method_reconciliation.md            # 5 方法 ΔΔF 汇总
└── run_log.txt                         # 跑全过程的 log
```

每个文件都 < 1 MB，**整个 `distilled/` 大概 5 MB**。打包发回：

```bash
tar czf distilled-from-offsite.tgz cluster/outputs/distilled/
# 然后微信 / 邮件给 Zengxuan
```

## 五、如果你的服务器没有 SLURM（fallback）

也可以直接 bash：

```bash
cd /path/to/your/MD/data/root
bash cluster/run_analysis.sh
# 或者只跑前两个 replica 看看：
bash cluster/run_analysis.sh --pilot
```

`run_analysis.sh` 跟 SBATCH 版本是同一套流程，只是没有 SLURM 调度。等 30 min。

## 六、如果出错

最常见的 3 种：

1. **找不到体系目录**：脚本默认 `${MD_PARENT}/15_120x120_K100_EPS05/s\d{3}/`。如果你的命名不同（比如 `K_100_eps05`），改 `cluster/run_config.sh` 顶部的 `SYSTEMS_DIRS` 数组。

2. **traj.xyz 路径不对**：脚本期望每个 replica 下有 `traj.xyz` + `mol.psf` + `num_bonds_for_xyz_frames.dat`。如果你那边文件名稍微不一样，告诉 Zengxuan，他会更新脚本。

3. **conda env 找不到**：如果 `phys` env 不存在，脚本会自动 fallback 到 `base`。如果 base 也没装 numpy/scipy/pandas/matplotlib，需要 `pip install -r cluster/requirements.txt`。

任何 Q 直接微信 Zengxuan，他会找我（Claude）排查。

---

谢谢外部协作者！🎉
