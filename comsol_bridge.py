import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator, LinearNDInterpolator
from config import SimConfig


class ComsolAeroBridge:
    """COMSOL 气动系数图谱接口（论文 §4.3 / 附录 B 交付清单）。

    C 管线图谱：G_C : (Re, S, q, orientation) -> (C_D, C_L, C_S)。
    - 队友按 docs/COMSOL数据交付格式.md 导出的 CSV 需包含字段：
      Re, S, orientation, C_D, C_L, C_S[, C_D_std, C_L_std, C_S_std, grid_version]
    - 完整 Re×S 网格工况用 log10(Re)×S 张量积插值；
      散点工况（如仅零自旋基准 + 少量正反自旋）自动改用散点线性插值；
    - 查询超出图谱覆盖域时返回 extrapolation_flag=True（不得无声外推）；
    - 未加载数据前，C 管线不可用；任何占位值都明确标记为"未验证"。"""

    REQUIRED_COLS = ["Re", "S", "C_D", "C_L", "C_S"]

    def __init__(self, csv_path=None):
        self.csv_path = csv_path
        self.data_loaded = False
        self.df = None
        self._interps = None          # {"cd": fn, "cl": fn, "cs": fn}
        self._re_bounds = None
        self._s_bounds = None
        self.grid_type = None         # "grid" 或 "scatter"
        self.grid_version = None
        if csv_path:
            self.load_comsol_table(csv_path)

    # ------------------------------------------------------------------
    def load_comsol_table(self, csv_path):
        """读取并校验 COMSOL 系数图谱，构建 log10(Re)×S 插值器。
        工况矩阵完整时用张量积插值，否则退化为散点线性插值。"""
        df = pd.read_csv(csv_path)
        missing = [c for c in self.REQUIRED_COLS if c not in df.columns]
        if missing:
            raise ValueError(f"COMSOL CSV 缺少必要字段: {missing}")

        self.df = df
        re_all = df["Re"].to_numpy(dtype=float)
        s_all = df["S"].to_numpy(dtype=float)
        log_re_all = np.log10(re_all)
        re_axis = np.unique(re_all)
        s_axis = np.unique(s_all)

        pts = np.stack([log_re_all, s_all], axis=1)
        if len(re_axis) * len(s_axis) == len(df):
            # 完整工况网格 → 张量积插值
            def make_grid(col):
                tab = df.pivot_table(index="Re", columns="S", values=col)
                return tab.reindex(index=re_axis, columns=s_axis).to_numpy(dtype=float)

            self._interps = {
                key: RegularGridInterpolator(
                    (np.log10(re_axis), s_axis), make_grid(col), method="linear",
                    bounds_error=False, fill_value=np.nan)
                for key, col in (("cd", "C_D"), ("cl", "C_L"), ("cs", "C_S"))
            }
            self.grid_type = "grid"
            self._re_bounds = (float(np.log10(re_axis[0])), float(np.log10(re_axis[-1])))
            self._s_bounds = (float(s_axis[0]), float(s_axis[-1]))
        else:
            # 散点工况（非完整矩阵）→ 线性四面体插值，凸包外返回 NaN 触发外推警告
            self._interps = {
                key: LinearNDInterpolator(pts, df[col].to_numpy(dtype=float),
                                          fill_value=np.nan)
                for key, col in (("cd", "C_D"), ("cl", "C_L"), ("cs", "C_S"))
            }
            self.grid_type = "scatter"
            self._re_bounds = (float(log_re_all.min()), float(log_re_all.max()))
            self._s_bounds = (float(s_all.min()), float(s_all.max()))

        self.grid_version = str(df.get("grid_version", [None])[0]) if "grid_version" in df.columns else "unspecified"
        self.data_loaded = True

    # ------------------------------------------------------------------
    def compute_re_and_spin_ratio(self, v_vec, omega_vec):
        """Re = ρD|u|/μ；S = R|ω|/|u|（论文 §3.2/§3.4）。"""
        v_mag = np.linalg.norm(v_vec) + 1e-9
        omega_mag = np.linalg.norm(omega_vec)
        re = SimConfig.RHO_AIR * SimConfig.DIAMETER * v_mag / SimConfig.MU_AIR
        spin_ratio = SimConfig.RADIUS * omega_mag / v_mag
        return float(re), float(spin_ratio)

    def get_aero_coeffs(self, v_vec, omega_vec):
        """核心接口：返回 (Cd, Cl, Cs, extrapolation_flag)。

        - 已加载图谱：log10(Re)×S 双线性插值；越界时 NaN→flag=True 并回退最近点；
        - 未加载图谱：返回明确标记为未验证的占位值（教学基准），flag=True。"""
        re, s = self.compute_re_and_spin_ratio(v_vec, omega_vec)
        if not self.data_loaded:
            # 缺失工况的占位默认值：在替换为交付数据前不可用于预测，调用时必须触发外推与占位警告
            return 0.25, 0.20, 0.0, True

        log_re = np.clip(np.log10(re), self._re_bounds[0], self._re_bounds[1])
        s_clip = np.clip(s, self._s_bounds[0], self._s_bounds[1])
        flag = bool(re < 10 ** self._re_bounds[0] or re > 10 ** self._re_bounds[1]
                    or s < self._s_bounds[0] or s > self._s_bounds[1])
        pt = np.array([[log_re, s_clip]])
        cd = float(self._interps["cd"](pt)[0])
        cl = float(self._interps["cl"](pt)[0])
        cs = float(self._interps["cs"](pt)[0])
        if np.isnan(cd) or np.isnan(cl):
            flag = True
            cd, cl, cs = 0.25, 0.20, 0.0
        return cd, cl, cs, flag
