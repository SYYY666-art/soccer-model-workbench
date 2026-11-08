# -*- coding: utf-8 -*-
"""COMSOL 队友交接数据解析与实测对照分析（论文 §7 模型标定与验证）。

解析 data/UPC2026_B_COMSOL_队友交接 下队友交付的 CSV/TXT，输出：
  1) 二维轴对称网格敏感性（01-03 阻力表，常规/更细/极细三套网格）；
  2) 三维瞬态零转/正转/反转球面总力时程（06-08），
     按 README §3 剔除启动首帧异常并完成 20 ms 接点拼接；
  3) 平台期 0.024-0.040 s 平均力系数 C_D / C_L / C_S 与压力贡献占比；
  4) 反向 Magnus 判据：实测侧向力符号 vs 经典 ω×u 方向；
  5) 可直接写入论文的英文图注。

风洞条件（05 全局参数）：U∞ = 31.46 m/s，球半径 R = 0.11 m，
ρ = 1.225 kg/m³，μ = 1.81×10⁻⁵ Pa·s → Re ≈ 4.68×10⁵；
正/反转 ωz = ±50 rad/s → 有符号旋转比 S = ±0.17483。
气动力归一化分母 ½ρU∞²A ≈ 23.044 N（A = πR² 迎风截面）。
"""

from pathlib import Path
import numpy as np

HANDOFF_DIR = Path(__file__).resolve().parent / "data" / "UPC2026_B_COMSOL_队友交接"

# ---- 风洞工况（05_三维_风洞原版_全局参数.txt） ----
U_INF = 31.46            # m/s 来流速度
R_BALL = 0.11            # m 球半径
M_BALL = 0.43            # kg 球质量
RHO_AIR = 1.225          # kg/m^3
MU_AIR = 1.81e-5         # Pa·s
A_REF = np.pi * R_BALL ** 2                       # 迎风截面面积
Q_REF = 0.5 * RHO_AIR * U_INF ** 2 * A_REF        # 气动力归一化分母 ≈ 23.044 N
RE_BALL = RHO_AIR * U_INF * 2.0 * R_BALL / MU_AIR # 雷诺数 ≈ 4.68e5
OMEGA_PLAT = 50.0                                  # rad/s 自旋平台
S_PLAT = OMEGA_PLAT * R_BALL / U_INF              # 有符号旋转比 ±0.17483
PLATEAU_T0, PLATEAU_T1 = 0.024, 0.040             # s 平台期比较窗口

# C 管线锚点表：队友仅交付单 Re 工况，将平台期系数铺到轨迹 Re 区间两个端点
RE_ANCHOR = (4.2e5, 4.7e5)      # 轨迹 |u|≈28-31.5 m/s 对应的 Re 区间
ANCHOR_VERSION = "handoff_anchor_Re468k"

# ---- 文件名清单（README §2） ----
F2D = [
    "01_二维_常规网格_球面面积与轴向阻力.csv",
    "02_二维_更细网格_球面面积与轴向阻力分解.csv",
    "03_二维_极细网格_球面面积与轴向阻力分解.csv",
]
MESH2D_NAMES = ["常规网格 (5,379 单元)", "更细网格 (14,834 单元)", "极细网格 (225,383 单元)"]
F3D_ZERO = [
    "06_三维_零转_研究2_球面三向总力_0至20ms.csv",
    "06_三维_零转_研究3_球面三向总力_20至40ms.csv",
]
F3D_POS = "07_三维_正转_研究4_球面三向总力_20至40ms.csv"
F3D_NEG = "08_三维_反转_研究4_球面三向总力_20至40ms.csv"
F3D_PRESSURE = "06_三维_零转_研究3_球面三向压力贡献_20至40ms.csv"

# CSV 列序：时间, 球面面积, Fx, Fy, Fz（二维表为 面积, 阻力[, 压差, 余项]）
T_IDX, FX_IDX, FY_IDX, FZ_IDX = 0, 2, 3, 4


def _read_table(csv_path: Path) -> np.ndarray:
    """读取 COMSOL 导出的 CSV：跳过 '%' 注释行与中文表头行，返回数值矩阵。"""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            try:
                rows.append([float(v) for v in line.split(",")])
            except ValueError:
                continue  # 表头行（含中文说明），跳过
    return np.array(rows, dtype=float)


def _mask_between(tbl: np.ndarray, t0: float, t1: float) -> np.ndarray:
    return (tbl[:, T_IDX] >= t0 - 1e-9) & (tbl[:, T_IDX] <= t1 + 1e-9)


def load_force_tables():
    """加载并清洗三维力表。

    返回 dict:
      zero: 零转合并时序（研究2 取 0.002-0.020 s，研究3 取 0.022-0.040 s，
            剔除两个异常首帧 203.9 N / 264.7 N）
      pos / neg: 正/反转时序（剔除 0.020 s 续算异常首帧，自 0.022 s 起）
      pressure: 零转研究3 压力贡献表（同样剔除 0.020 s 首帧）
    """
    seg1 = _read_table(HANDOFF_DIR / F3D_ZERO[0])
    seg2 = _read_table(HANDOFF_DIR / F3D_ZERO[1])
    zero = np.vstack([
        seg1[_mask_between(seg1, 0.002, 0.020)],
        seg2[_mask_between(seg2, 0.022, 0.040)],
    ])

    def _clean(path):
        tbl = _read_table(HANDOFF_DIR / path)
        return tbl[_mask_between(tbl, 0.022, 0.040)]

    return {
        "zero": zero,
        "pos": _clean(F3D_POS),
        "neg": _clean(F3D_NEG),
        "pressure": _clean(F3D_PRESSURE),
    }


def load_mesh_2d():
    """读取 01-03 二维轴对称阻力表，返回网格敏感性明细。"""
    rows = []
    for name, fname in zip(MESH2D_NAMES, F2D):
        tbl = _read_table(HANDOFF_DIR / fname)
        area = float(tbl[0, 0])
        fd = float(tbl[0, 1])
        fd_p = float(tbl[0, 2]) if tbl.shape[1] > 2 else np.nan
        fd_rest = float(tbl[0, 3]) if tbl.shape[1] > 3 else np.nan
        rows.append({
            "name": name,
            "area": area,
            "fd": fd,
            "fd_pressure": fd_p,
            "fd_rest": fd_rest,
            "cd": fd / Q_REF,
        })
    return rows


def plateau_stats(tbl: np.ndarray):
    """平台期 0.024-0.040 s 平均力与无量纲系数。

    返回 (F_avg [Fx,Fy,Fz], C_avg [C_D,C_L,C_S])，按 ½ρU²A 归一化。"""
    m = _mask_between(tbl, PLATEAU_T0, PLATEAU_T1)
    F = tbl[m][:, FX_IDX:FZ_IDX + 1].mean(axis=0)
    return F, F / Q_REF


def analyze():
    """总入口：解析全部交接数据，输出定量对照结果。"""
    ft = load_force_tables()
    mesh = load_mesh_2d()

    F0, C0 = plateau_stats(ft["zero"])
    Fp, Cp = plateau_stats(ft["pos"])
    Fn, Cn = plateau_stats(ft["neg"])
    Fpr, Cpr = plateau_stats(ft["pressure"])  # 压力贡献

    # 与零转同时间点的横向力差（正/反转 10 点与零转 0.022-0.040 对齐）
    zero_late = ft["zero"][_mask_between(ft["zero"], 0.022, 0.040)]
    dFy_pos = ft["pos"][:, FY_IDX] - zero_late[:, FY_IDX]
    dFy_neg = ft["neg"][:, FY_IDX] - zero_late[:, FY_IDX]

    # 反向 Magnus 判据：经典 Magnus 侧力沿 ω×u 方向。
    # 来流 u=+x，ωz=+50 → ω×u = +y；实测正转 ΔFy < 0 → 方向相反。
    reverse_magnus = bool(np.mean(dFy_pos) < 0.0 and np.mean(dFy_neg) > 0.0)

    # 压力贡献占比（零转平台期）
    fx_p_frac = float(Fpr[0] / F0[0])
    fy_p_frac = float(Fpr[1] / F0[1]) if abs(F0[1]) > 1e-9 else np.nan

    # 末帧瞬时值（论文引用值，README §3 核对表）
    def _last(tbl):
        return tbl[-1]

    last = {
        "zero": _last(ft["zero"]),
        "pos": _last(ft["pos"]),
        "neg": _last(ft["neg"]),
    }
    # 实测 C_L 折合为经典 Magnus 参数化下的等效 |Ω_eff|
    omega_equiv = {
        "plateau_pos": equivalent_omega_eff(abs(Cp[1])),
        "plateau_neg": equivalent_omega_eff(abs(Cn[1])),
        "last_neg": equivalent_omega_eff(abs(last["neg"][FY_IDX] / Q_REF)),
    }

    return {
        "tables": ft,
        "mesh": mesh,
        "plateau": {
            "zero": {"F": F0, "C": C0},
            "pos": {"F": Fp, "C": Cp},
            "neg": {"F": Fn, "C": Cn},
            "pressure": {"F": Fpr, "C": Cpr},
        },
        "dFy": {"pos": dFy_pos, "neg": dFy_neg,
                "t": zero_late[:, T_IDX]},
        "reverse_magnus": reverse_magnus,
        "pressure_frac": {"fx": fx_p_frac, "fy": fy_p_frac},
        "last": last,
        "omega_equiv": omega_equiv,
        "conditions": {
            "U": U_INF, "Re": RE_BALL, "S": S_PLAT,
            "q_ref": Q_REF, "omega": OMEGA_PLAT,
        },
    }


def equivalent_omega_eff(cl_abs):
    """把实测 |C_L| 折合为经典 Magnus 参数化下的等效 |Ω_eff| (s⁻¹)：

    a_lift = |Ω_eff|·|u| ≡ (ρA/2m)·C_L·|u|²  →  |Ω_eff| = (ρA/2m)·C_L·|u|。
    用于与实验台 A 管线反演的 Ω_eff 量级对照。"""
    return float(cl_abs * RHO_AIR * A_REF / (2.0 * M_BALL) * U_INF)


def generate_comsol_table(output_path=None):
    """从队友交接 CSV 自动生成 C 管线锚点系数表 data/comsol_table.csv。

    队友交付的是固定 Re≈4.68e5 的瞬态力表（非多工况图谱），本表把平台期
    平均系数铺到轨迹 Re 区间 [4.2e5, 4.7e5] 的两个端点（假设超临界区系数对
    Re 弱依赖），S 取实测三工况 −0.17483 / 0 / +0.17483，共 2×3=6 行。
    透明标注 grid_version=ANCHOR_VERSION；越界查询由 ComsolAeroBridge
    标记 extrapolation_flag，不静默外推。"""
    import pandas as pd

    ft = load_force_tables()
    plateau = {}
    for key in ("zero", "pos", "neg"):
        tbl = ft[key]
        m = _mask_between(tbl, PLATEAU_T0, PLATEAU_T1)
        F = tbl[m][:, FX_IDX:FZ_IDX + 1].mean(axis=0)
        Fstd = tbl[m][:, FX_IDX:FZ_IDX + 1].std(axis=0)
        plateau[key] = (F / Q_REF, Fstd / Q_REF)

    rows = []
    for re_val in RE_ANCHOR:
        for s_val, key in ((-S_PLAT, "neg"), (0.0, "zero"), (S_PLAT, "pos")):
            C, Cstd = plateau[key]
            rows.append({
                "Re": re_val,
                "S": round(float(s_val), 5),
                "orientation": 0,
                "C_D": round(float(C[0]), 4),
                "C_L": round(float(C[1]), 4),
                "C_S": round(float(C[2]), 4),
                "C_D_std": round(float(Cstd[0]), 4),
                "C_L_std": round(float(Cstd[1]), 4),
                "C_S_std": round(float(Cstd[2]), 4),
                "grid_version": ANCHOR_VERSION,
            })
    out = Path(output_path) if output_path is not None else HANDOFF_DIR.parent / "comsol_table.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return str(out)


def magnus_classic_direction():
    """经典 Magnus 方向 (ω×u) 的单位向量：来流 +x、自旋 +z → +y。"""
    omega = np.array([0.0, 0.0, OMEGA_PLAT])
    u = np.array([U_INF, 0.0, 0.0])
    cross = np.cross(omega, u)
    return cross / np.linalg.norm(cross)


def captions_en(res):
    """生成论文可直接使用的英文图注（README §4 要求的交付物之一）。"""
    mesh = res["mesh"]
    C0 = res["plateau"]["zero"]["C"]
    Cp = res["plateau"]["pos"]["C"]
    Cn = res["plateau"]["neg"]["C"]
    last = res["last"]
    dFy = res["dFy"]
    cap_mesh = (
        "Grid sensitivity of the 2-D axisymmetric drag on a smooth soccer ball "
        f"(U = {U_INF} m/s, Re = {RE_BALL:.2e}). The axial drag decreases from "
        f"{mesh[0]['fd']:.2f} N on the standard mesh to {mesh[2]['fd']:.2f} N on the "
        f"ultra-fine mesh (C_D from {mesh[0]['cd']:.3f} to {mesh[2]['cd']:.3f}), "
        "and the refinement change is carried almost entirely by the pressure contribution."
    )
    cap_forces = (
        "Transient surface-integrated forces on the smooth sphere from the 3-D wind tunnel "
        f"model (U = {U_INF} m/s). Mean plateau values (0.024-0.040 s): zero spin "
        f"F_x = {C0[0]*Q_REF:.2f} N (C_D = {C0[0]:.3f}); positive spin "
        f"F_y = {Cp[1]*Q_REF:.2f} N (C_L = {Cp[1]:+.3f}); negative spin "
        f"F_y = {Cn[1]*Q_REF:.2f} N (C_L = {Cn[1]:+.3f}). The lateral-force sign is "
        "opposite to the classical Magnus direction, indicating a reverse Magnus "
        f"effect near the critical Reynolds number; |ΔF_y| at 0.040 s is {abs(dFy['neg'][-1]):.2f} N."
    )
    cap_pressure = (
        "Decomposition of the zero-spin force into pressure and residual contributions. "
        f"The pressure contribution accounts for {res['pressure_frac']['fx']:.0%} of F_x "
        f"and {res['pressure_frac']['fy']:.0%} of F_y on the plateau, so the lateral "
        "force is essentially a pressure-asymmetry effect."
    )
    return {
        "mesh": cap_mesh,
        "forces": cap_forces,
        "pressure": cap_pressure,
    }


FIG_LABELS = {
    "zh": {
        "st1": "球面侧向力 F<sub>y</sub>(t)", "st2": "相对零转的侧向力差 ΔF<sub>y</sub>(t)",
        "zero": "零转 ω=0", "pos": "正转 ω<sub>z</sub>=+50 rad/s", "neg": "反转 ω<sub>z</sub>=−50 rad/s",
        "pr": "零转压力贡献",
        "dpos": "ΔF<sub>y</sub>(正转)−ΔF<sub>y</sub>(零转)", "dneg": "ΔF<sub>y</sub>(反转)−ΔF<sub>y</sub>(零转)",
        "tx": "时间 t (ms)", "fy": "侧向力 F<sub>y</sub> (N)", "dfy": "ΔF<sub>y</sub> (N)",
        "m1": "轴向总阻力 F<sub>D</sub> (N)", "m2": "总阻力系数 C<sub>D</sub> (−)",
        "bar_total": "总阻力", "bar_pres": "其中压差阻力", "bar_cd": "C<sub>D</sub>",
    },
    "en": {
        "st1": "Sphere lateral force F<sub>y</sub>(t)", "st2": "Lateral-force difference from zero spin ΔF<sub>y</sub>(t)",
        "zero": "Zero spin ω=0", "pos": "Positive spin ω<sub>z</sub>=+50 rad/s",
        "neg": "Negative spin ω<sub>z</sub>=−50 rad/s",
        "pr": "Zero-spin pressure contribution",
        "dpos": "ΔF<sub>y</sub>(positive)−ΔF<sub>y</sub>(zero)", "dneg": "ΔF<sub>y</sub>(negative)−ΔF<sub>y</sub>(zero)",
        "tx": "Time t (ms)", "fy": "Lateral force F<sub>y</sub> (N)", "dfy": "ΔF<sub>y</sub> (N)",
        "m1": "Axial drag F<sub>D</sub> (N)", "m2": "Drag coefficient C<sub>D</sub> (−)",
        "bar_total": "Total drag", "bar_pres": "Pressure drag", "bar_cd": "C<sub>D</sub>",
    },
}


def build_force_timeseries_fig(res, lang="zh"):
    """三维力时程对照图：三工况 Fy(t)、ΔFy(t) 与压力贡献 Fy(t)。"""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    L = FIG_LABELS.get(lang, FIG_LABELS["zh"])
    ft = res["tables"]
    dFy = res["dFy"]
    zero = ft["zero"]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=(L["st1"], L["st2"]))

    fig.add_trace(go.Scatter(x=zero[:, 0] * 1e3, y=zero[:, FY_IDX], mode="lines+markers",
                             name=L["zero"], line=dict(color="#334155")), row=1, col=1)
    fig.add_trace(go.Scatter(x=ft["pos"][:, 0] * 1e3, y=ft["pos"][:, FY_IDX], mode="lines+markers",
                             name=L["pos"], line=dict(color="#dc2626")), row=1, col=1)
    fig.add_trace(go.Scatter(x=ft["neg"][:, 0] * 1e3, y=ft["neg"][:, FY_IDX], mode="lines+markers",
                             name=L["neg"], line=dict(color="#2563eb")), row=1, col=1)
    fig.add_trace(go.Scatter(x=ft["pressure"][:, 0] * 1e3, y=ft["pressure"][:, FY_IDX],
                             mode="lines", line=dict(color="#334155", dash="dot"),
                             name=L["pr"]), row=1, col=1)

    fig.add_trace(go.Scatter(x=dFy["t"] * 1e3, y=dFy["pos"], mode="lines+markers",
                             name=L["dpos"], line=dict(color="#dc2626")), row=2, col=1)
    fig.add_trace(go.Scatter(x=dFy["t"] * 1e3, y=dFy["neg"], mode="lines+markers",
                             name=L["dneg"], line=dict(color="#2563eb")), row=2, col=1)
    fig.add_hline(y=0.0, line=dict(color="#94a3b8", width=1, dash="dash"), row=2, col=1)

    fig.update_layout(height=560, margin=dict(l=10, r=10, t=80, b=10),
                      legend=dict(orientation="h", y=1.16, x=0.0, yanchor="bottom"),
                      hovermode="x unified",
                      template="plotly_white")
    fig.update_xaxes(title_text=L["tx"], row=2, col=1)
    fig.update_yaxes(title_text=L["fy"], row=1, col=1)
    fig.update_yaxes(title_text=L["dfy"], row=2, col=1)
    return fig


def build_mesh_sensitivity_fig(res, lang="zh"):
    """二维网格敏感性柱状图：轴向总阻力与 C_D。"""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    L = FIG_LABELS.get(lang, FIG_LABELS["zh"])
    mesh = res["mesh"]
    names = [m["name"] for m in mesh]
    fd = [m["fd"] for m in mesh]
    cd = [m["cd"] for m in mesh]
    fd_p = [m["fd_pressure"] if np.isfinite(m["fd_pressure"]) else None for m in mesh]

    fig = make_subplots(rows=1, cols=2, subplot_titles=(L["m1"], L["m2"]))

    fig.add_trace(go.Bar(x=names, y=fd, name=L["bar_total"], marker_color="#0d9488",
                         text=[f"{v:.3f}" for v in fd], textposition="outside"), row=1, col=1)
    if any(p is not None for p in fd_p):
        fig.add_trace(go.Bar(x=names[1:], y=fd_p[1:], name=L["bar_pres"],
                             marker_color="#f59e0b",
                             text=[f"{v:.3f}" for v in fd_p[1:]],
                             textposition="outside"), row=1, col=1)
    fig.add_trace(go.Bar(x=names, y=cd, name=L["bar_cd"], marker_color="#2563eb",
                         text=[f"{v:.3f}" for v in cd], textposition="outside"), row=1, col=2)

    fig.update_layout(height=400, margin=dict(l=10, r=10, t=50, b=10),
                      showlegend=False, template="plotly_white",
                      hovermode="x unified")
    return fig


if __name__ == "__main__":
    res = analyze()
    print("== 平台期平均（0.024-0.040 s） ==")
    for key, lab in [("zero", "零转"), ("pos", "正转"), ("neg", "反转")]:
        p = res["plateau"][key]
        print(f"{lab}: F=({p['F'][0]:.3f},{p['F'][1]:+.3f},{p['F'][2]:+.3f}) N  "
              f"C=({p['C'][0]:.3f},{p['C'][1]:+.3f},{p['C'][2]:+.3f})")
    print(f"压力贡献占比: Fx {res['pressure_frac']['fx']:.1%}, Fy {res['pressure_frac']['fy']:.1%}")
    print(f"反向 Magnus: {res['reverse_magnus']}")
    print(f"末帧: 零转 Fy={res['last']['zero'][FY_IDX]:+.3f}, "
          f"正转 Fy={res['last']['pos'][FY_IDX]:+.3f}, "
          f"反转 Fy={res['last']['neg'][FY_IDX]:+.3f} N")
    for k, cap in captions_en(res).items():
        print(f"\n[{k}] {cap}")
