# 2D-Binding 全量数据复跑包

> **From Claude (代 Zengxuan)**
>
> 学姐你好！这是一个自包含的分析包，把它解压到你 MD 数据所在的根目录就能跑。
> 它会扫描所有 `<体系>/s001`, `<体系>/s002`, ... 续跑文件夹，把每个 replica 的 chain
> 坐标抽出来 → 全部 concat 起来 → 跑 4 个分析（phd_closure 四项分解、phd_closure_s25
> 三项 WLC、raw_tether_partition K2D、diagnose bound vs unbound 偏倚）→ 输出 distilled
> 表格 (~10 MB)。你只需要把 `distilled/` 整个发回给 Zengxuan 就行，不用传 GB 级的中
> 间 npz。
>
> 目的：测试我们的猜想 —— "PPT s25 数和我 s001 数差 1.5-2 kBT 是不是因为我数据少"。
> 如果用你全量数据跑完和 PPT s25 收敛，那答案就是"是"，s001 单 replica 不够；
> 如果还是差很多，那就是公式或参数选择的问题，我们再深挖。

## 一、解压

把 `bundle_for_senior.tgz` 拷到你 MD 数据根目录（**即下面有 `15_120x120_K100_EPS05/` 这样子目录的位置**）：

```bash
cd /path/to/your/MD/data/root
tar xzf bundle_for_senior.tgz
cd bundle_for_senior
```

## 二、环境

```bash
# 如果你的 phys env 已经齐了，直接：
conda activate phys

# 否则任何 Python 3.10+ env，pip install：
pip install -r requirements.txt
```

只依赖 numpy/scipy/pandas/matplotlib/scikit-learn —— 都是分析栈，**不需要 pygamd**。

## 三、跑全量

```bash
bash run_full_analysis.sh
```

脚本会：
1. 扫描父目录 `../` 下 K100/K10/K01 三个体系的所有 `s\d{3}` replicas
2. 对每个 replica 跑 extract_chain_coords，输出到 `extracted/<system>/<replica>/chain_coords.npz`
3. 把每个体系的 replicas 沿 frame 轴 concat → `merged/<system>/chain_coords.npz`
4. 跑 4 个分析脚本（约 10 min 总，已经 multi-process）
5. 全部结果 distilled 到 `distilled/`

预计 wall time：
- extract 每个 replica ~30 s，单核。如果你有 100 个 replicas × 3 体系 → 总 ~150 min 单核。脚本会用 8 工人并行 → **~20 min**。
- merge 三体系 ~1 min
- 分析 4 项 ~5 min（bootstrap n=200，并行 8 工人）

**总：约 30 分钟**，主要是 I/O 等。

如果你只想先 pilot 看一下（每体系前 2 个 replicas，5 min）：

```bash
bash run_full_analysis.sh --pilot
```

## 四、发回 Zengxuan 什么

跑完后 `distilled/` 目录里：

```
distilled/
├── inventory.tsv                   # 每个体系实际找到几个 replicas、总帧数
├── phd_closure.md + .npz           # 四项 ΔΔF 分解 + bootstrap σ
├── phd_closure_s25.md + .npz       # 三项 WLC + bootstrap σ
├── raw_tether_partition.md + .npz  # rigid 绝对 K2D + bootstrap
├── diagnose_bias.md                # bound vs unbound 几何对比表
└── reconcile_methods.md            # 5 方法 ΔΔF 汇总
```

每个文件都 < 1 MB，**整个 `distilled/` 大概 5 MB**。微信 / 邮件发回来就行。

## 五、如果出错

最常见的 3 种：

1. **找不到体系目录**：脚本默认 `../15_120x120_K100_EPS05/s\d{3}/`。如果你的命名不同（比如 `K_100_eps05`），改 `run_full_analysis.sh` 顶部的 `SYSTEMS_DIRS` 数组。

2. **traj.xyz 路径不对**：脚本期望每个 replica 下有 `traj.xyz` + `mol.psf` + `num_bonds_for_xyz_frames.dat`。如果你那边文件名稍微不一样，告诉 Zengxuan，他会更新脚本。

3. **某体系跑崩**：脚本会继续做剩下的体系，崩掉的体系会在 distilled/run_log.txt 留 trace。

任何 Q 直接微信 Zengxuan，他会找我（Claude）排查。

---

谢谢学姐！🎉
