---
purpose: "Chinese WeChat reply drafts for the off-site collaborator's Q&A about the full-data analysis bundle"
audience: user (Zengxuan, to copy-paste); Claude (to append new templates when new Q&A patterns appear)
status: current
---

# cluster/WECHAT_TEMPLATES_zh.md — WeChat 回复模板（中文）

外部协作者（学姐）跑全量数据 bundle 期间常见 Q&A。用户可以直接复制粘贴。新出现的 Q 在这里追加，**不要**写进 plan 文件。

## 1. 初次询问 "这个 bundle 是分析什么的 / 输出去哪"（2026-06-03 收到）

学姐看到 bundle 路径 + HOWTO 之后问：
1. "这个是分析什么的？"
2. "他分析了以后每一个文件夹下的文件都会到相应的文件夹下面吗？"

完整回复：

```
学姐你好！

【这个 bundle 分析什么的？】
我们这边在做三个体系 (K100/K10/K01 — 同 k_a 但 lp 不同) 的跨膜 R-L 结合 K2D 分析。35× K2D 比能不能纯用熵差解释还是悬而未决，bundle 跑 5 个分析把 ΔΔF 拆出来 + 跟 PPT s25 对比 + 检测 bound/unbound 几何偏倚。

我自己 s001 单 replica 跑出来跟 PPT s25 差 1.5-2 kBT，猜测是"我数据少"。你用全量数据跑完一比，这个猜想就能直接证伪/证实。

bundle 跑的 5 个分析：
  1. closure_four_term       — S1-S23 四项 ΔΔF 分解
  2. closure_wlc_three_term  — 三项 WLC (对标 PPT s25)
  3. raw_tether_partition    — 从 traj.xyz 直接算 K2D,max
  4. diagnose_bound_vs_unbound — bound vs unbound 几何对比
  5. reconcile_methods       — 5 方法 ΔΔF 汇总

总时长约 30 min (SLURM 调度时间不算)。

【文件去向】
跑的过程中所有中间 + 最终输出都会落在你工作目录下的 cluster/ 里：

  $DEST/cluster/
  ├── outputs/
  │   ├── extracted/<体系>/<replica>/chain_coords.npz   ← 每个 replica 中间提取 (大文件)
  │   ├── chain_coords/<体系>/chain_coords.npz           ← 每个体系 concat 后合并 (中等)
  │   └── distilled/                                      ← 最终输出, ~5 MB
  │       ├── inventory.tsv                               (每体系找到几个 replicas)
  │       ├── closure_four_term_data.md + .npz            (四项分解)
  │       ├── closure_wlc_three_term.md + .npz            (三项 WLC)
  │       ├── raw_tether_partition.md + .npz              (绝对 K2D)
  │       ├── diagnose_bias.txt                            (bound/unbound)
  │       ├── method_reconciliation.md + .png             (5 方法汇总)
  │       └── run_log.txt                                  (完整 run log)
  └── results/                                            ← 中间 md+npz+png 的"原版"
                                                            (distilled/ 是这里的精简 copy)

你【只需要 cp distilled/ 这一个目录】回共享目录就行：

  ROUND=/mnt/nfs/ugstu/liuzx/2D-Binding/cluster/outputs/$(date -I)_round1
  mkdir -p $ROUND
  cp -R $DEST/cluster/outputs/distilled/* $ROUND/

extracted/ 和 chain_coords/ 是中间文件占空间但你不需要管 — 跑完确认 distilled 拷回来了你 rm -rf $DEST 整个工作目录都可以。

任何问题随时问！
```

## 2. 常见 follow-up 速查表

| 学姐可能问 | 怎么答（一句话） |
|---|---|
| "我的 MD 数据目录命名不一样" | "改 `$DEST/cluster/run_config.sh` 里的 SYSTEMS_DIRS 数组" |
| "我 cluster 没有 gpu partition" | "改 run_config.sh 里 SLURM_PARTITION" |
| "需要 conda env phys 吗" | "不需要, base 有 numpy/scipy/pandas/matplotlib 就行" |
| "跑很久还没动" | "tail -f cluster/outputs/slurm-<job_id>.log 看进度" |
| "rsync 复制要多久" | "1-3 min, 总共 ~46 文件 < 1 MB" |
| "我能跑 pilot 先看看吗" | "可以, `bash cluster/run_analysis.sh --pilot`, 每体系 2 replicas, ~5 min" |
| "MD_PARENT 要填什么" | "通常不用填 — auto-detect 会从 `$BUNDLE_ROOT/../..` 找 SYSTEMS_DIRS; 只有 bundle 放在非常规位置才要手动改 run_config.sh 顶部" |
| "需要 git 吗" | "不需要 — 全程 rsync + cp + sbatch + cp，零 git" |
| "extract 报 mol.psf 找不到" | "检查 cluster/outputs/<体系>/ 下有没有 per-system symlink；run_analysis.sh 启动时会自动创建，如果失败检查 MD_PARENT 是不是对" |

## 何时追加新模板到这里

任何时候学姐问了一个**新的、值得复用**的问题，把回答追加到上面表里。如果是单次澄清，不用记录。如果是 multi-line 复杂回答，新开一个 "## N. <topic>" 段落。

**绝对不要**把这些 templates 复制到 plan 文件 — plan 只 focus 下一个 session 的工作，文档累积归 `cluster/WECHAT_TEMPLATES_zh.md`。
