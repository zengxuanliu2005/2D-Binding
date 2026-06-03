---
purpose: "Chinese walkthrough for running the full-data analysis bundle on the off-site cluster"
audience: off-site collaborator (after rsync from the shared cluster directory)
status: current
---

# 2D-Binding 全量数据复跑包

> **From Claude (代 Zengxuan)**
>
> 数据持有方您好！这是一个自包含的分析包，把它 rsync 到你自己的工作目录就能跑。
> 它会扫描所有 `<体系>/s001`, `<体系>/s002`, ... 续跑文件夹，把每个 replica 的 chain
> 坐标抽出来 → 全部 concat 起来 → 跑 4 个分析（closure_four_term 四项分解、closure_wlc_three_term
> 三项 WLC、raw_tether_partition K2D、diagnose bound vs unbound 偏倚）→ 输出 distilled
> 表格 (~5 MB)。
>
> 目的：测试我们的猜想 —— "PPT s25 数和我 s001 数差 1.5-2 kBT 是不是因为我数据少"。
> 如果用你全量数据跑完和 PPT s25 收敛，那答案就是"是"，s001 单 replica 不够；
> 如果还是差很多，那就是公式或参数选择的问题，我们再深挖。

---

## 一、把 cluster/ 拷到你自己的工作目录

不需要解压 tarball — bundle 已经放在共享目录里了，rsync 过去就行。**推荐把它放在你 MD 数据根目录下**（即下面有 `15_120x120_K100_EPS05/` 这样子目录的位置），这样可以省掉编辑 run_config.sh：

```bash
SOURCE=/mnt/nfs/ugstu/liuzx/2D-Binding/cluster
MD_ROOT=/your/MD/data/root                 # 你自己 MD 数据根目录的绝对路径
DEST=$MD_ROOT/2D-Binding-fullrun/cluster
mkdir -p $DEST
rsync -av \
    --exclude='trial' --exclude='outputs' --exclude='results' \
    --exclude='.DS_Store' --exclude='.git*' \
    $SOURCE/ $DEST/
```

注意：

- `trial/`, `outputs/`, `results/` 是 Zengxuan 那边的工作目录，不要拷。
- rsync 后 `$DEST` 应该有 `run_config.sh / run_analysis.sh / slurm/ / scripts/ / analysis/ / env_setup/ / README.md / HOWTO_run_full_data_zh.md / requirements.txt`。
- 如果你**不能**或**不想**把 bundle 放在 MD 数据根目录下，那就放别处，然后下一步去 `run_config.sh` 把 `MD_PARENT` 改成 MD 数据根目录的绝对路径。

## 二、（通常不需要改）run_config.sh

脚本会自动探测 MD 数据根目录：如果 `MD_PARENT` 还是占位符或不存在，会向上找 `$DEST/../..` 等候选，找到含 SYSTEMS_DIRS 的目录就用。**如果你按上一步推荐的位置放了 bundle，这步可以直接跳过。**

只有以下情况要 `vim $DEST/run_config.sh`：

| 字段 | 默认值 | 什么时候要改 |
|---|---|---|
| `MD_PARENT` | `/path/to/your/MD/data/root` | bundle 没放在 MD 根目录附近 → 必填绝对路径 |
| `SYSTEMS_DIRS` | `15_120x120_K100_EPS05` 等 3 个 | 你三个体系的目录名不一样 |
| `SLURM_PARTITION` | `gpu` | 你 cluster 的 partition 不叫 gpu |
| `SLURM_NODE` | `n01` | 你 cluster 没这个节点（注释掉这行即可让 SLURM 自动分配） |
| `SLURM_TIME` | `24:00:00` | 你 cluster 限制更严 |
| `SLURM_MEM` | `32G` | 你 cluster 节点内存不够 / 或你想给更多 |
| `SLURM_CPUS` / `N_JOBS` | 8 | 你机器核数不同；保持 `SLURM_CPUS ≥ N_JOBS` |
| `PY_ENVS` | `phys base` | 你那边 conda env 叫别的（脚本会按顺序试每一个） |

## 三、提交 SLURM job（主入口）

```bash
cd $DEST/..                       # cd 到 cluster/ 的父目录
sbatch cluster/slurm/full_analysis.slurm
```

看进度：

```bash
squeue -u $USER                                           # job 还在没在
tail -f cluster/outputs/slurm-<job_id>.log                # 实时输出
```

预计 wall time：

- extract 每个 replica ~30 s，单核。如果你有 100 个 replicas × 3 体系 → 总 ~150 min 单核。脚本会用 8 工人并行 → **~20 min**。
- merge 三体系 ~1 min
- 分析 4 项 ~5 min（bootstrap n=200，并行 8 工人）

**总：约 30 分钟**，主要是 I/O 等。

## 四、把结果拷回 Zengxuan 的目录

跑完后所有 distilled 输出都在 `$DEST/cluster/outputs/distilled/`：

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

每个文件都 < 1 MB，**整个 `distilled/` 大概 5 MB**。直接 cp 回 Zengxuan 的共享目录：

```bash
ROUND_DIR=/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/outputs/$(date -I)_round1
mkdir -p $ROUND_DIR
cp -R $DEST/cluster/outputs/distilled/* $ROUND_DIR/
# 然后微信通知 Zengxuan: distilled 已经在 $ROUND_DIR
```

Zengxuan 看到 ping 就能去拿，不需要传文件。

## 五、如果你的服务器没有 SLURM（fallback）

也可以直接 bash 跑：

```bash
cd $DEST/..
bash cluster/run_analysis.sh           # 全量
bash cluster/run_analysis.sh --pilot   # 每个体系前 2 个 replica，~5 min
```

`run_analysis.sh` 跟 SBATCH 版本是同一套流程，只是没有 SLURM 调度。等 30 min。

## 六、如果出错

最常见的 3 种：

1. **找不到体系目录**：脚本先用 auto-detect 去找，找不到会在最开始 `ERROR: MD_PARENT='...' does not contain any of: 15_120x120_K100_EPS05 ...` 报错并 exit 5。检查你 MD 数据根目录的实际命名，必要时改 `$DEST/run_config.sh` 的 `MD_PARENT` 或 `SYSTEMS_DIRS`。

2. **traj.xyz 路径不对**：脚本期望每个 replica 下有 `traj.xyz` + `mol.psf` + `num_bonds_for_xyz_frames.dat`。如果你那边文件名稍微不一样，告诉 Zengxuan，他会更新脚本。

3. **conda env 找不到**：如果 `phys` env 不存在，脚本会自动 fallback 到 `base`。如果 base 也没装 numpy/scipy/pandas/matplotlib，需要 `pip install -r $DEST/requirements.txt`。

任何 Q 直接微信 Zengxuan，他会找我（Claude）排查。
