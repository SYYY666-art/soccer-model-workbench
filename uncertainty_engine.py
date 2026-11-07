import numpy as np
from scipy.stats import gaussian_kde
from config import SimConfig


def _variance_decomposition(rows):
    """模型包络方差分解 Var(P_g|D) = E_M[Var] + Var_M[E]（论文 §6.1，逐轴）。"""
    valid = [r for r in rows if r.get("mean_y") is not None and not np.isnan(r["mean_y"])]
    decomp = {"E_var_y": np.nan, "var_E_y": np.nan, "E_var_z": np.nan, "var_E_z": np.nan,
              "fraction_between_y": np.nan, "fraction_between_z": np.nan}
    if valid:
        e_var_y = float(np.mean([r["std_y"] ** 2 for r in valid]))
        var_E_y = float(np.var([r["mean_y"] for r in valid], ddof=0))
        e_var_z = float(np.mean([r["std_z"] ** 2 for r in valid]))
        var_E_z = float(np.var([r["mean_z"] for r in valid], ddof=0))
        decomp = {
            "E_var_y": e_var_y, "var_E_y": var_E_y,
            "E_var_z": e_var_z, "var_E_z": var_E_z,
            "fraction_between_y": var_E_y / (e_var_y + var_E_y) if (e_var_y + var_E_y) > 0 else np.nan,
            "fraction_between_z": var_E_z / (e_var_z + var_E_z) if (e_var_z + var_E_z) > 0 else np.nan,
        }
    return decomp


def _run_model_job(payload):
    """多进程 worker：单模型 反演 + 蒙特卡洛传播（论文离线批量计算用）。
    每个子进程独立构建引擎，payload 为可 pickle 的元组。"""
    (model_id, t1, t2, r1, r2, sigma_obs, wind, fix_cd,
     sigma_r, n_samples, err_model, seed) = payload
    from comsol_bridge import ComsolAeroBridge
    from physics_theory import TrajectoryPhysicsEngine
    from uncertainty_engine import UncertaintyAndTestEngine

    bridge = ComsolAeroBridge()
    phys = TrajectoryPhysicsEngine(bridge)
    unc = UncertaintyAndTestEngine(phys)
    try:
        res = phys.predict(model_id, t1, t2, np.asarray(r1, float), np.asarray(r2, float),
                           sigma_obs=sigma_obs, wind=np.asarray(wind, float), fix_cd=fix_cd)
        mc = unc.generate_mc_ensemble(res, sigma_r=sigma_r, n_samples=n_samples,
                                      err_model=err_model, seed=seed)
        st = mc["stats"]
        return {
            "model": model_id,
            "mean_y": st["y"]["mean"], "std_y": st["y"]["std"],
            "mean_z": st["z"]["mean"], "std_z": st["z"]["std"],
            "t_g_median": st["t_g"]["median"],
            "P_reach": mc["probs"]["P_reach"],
            "P_in_given_reach": mc["probs"]["P_in_given_reach"],
            "status": res["event_label"],
        }
    except Exception as e:
        return {"model": model_id, "mean_y": np.nan, "std_y": np.nan,
                "mean_z": np.nan, "std_z": np.nan, "t_g_median": np.nan,
                "P_reach": np.nan, "P_in_given_reach": np.nan,
                "status": f"ERR:{type(e).__name__}"}


class UncertaintyAndTestEngine:
    """概率预测引擎（论文 §6）：

    - 观测误差模型：独立均匀舍入 ±0.005 m 或独立高斯 σ_r（可扫描）；
    - 参数后验抽样：θ ~ N(θ_MAP, Σ_θ)，联合观测误差一起传播；
    - 事件量 (t_g, y_g, z_g) 对参数扰动采用一阶灵敏度线性传播（公式 6.5），
      并对 |v_x(t_g)| 过小的近切触样本给出线性失效警示；
    - 事件标签（goal-in / goal-out / ground / timeout）全部保留，不静默剔除；
    - 输出 P_reach、P_in|reach、P(reach∧in) 及均值/中位数/众数、95% 椭圆与 HDR。"""

    def __init__(self, physics_engine):
        self.physics_engine = physics_engine

    # ------------------------------------------------------------------
    @staticmethod
    def sample_obs_noise(rng, n, err_model, sigma_r, n_frames=2):
        if err_model == "uniform":
            hw = SimConfig.ROUNDING_HALFWIDTH
            return rng.uniform(-hw, hw, (n, n_frames, 3))
        return rng.normal(0.0, max(sigma_r, 1e-4), (n, n_frames, 3))

    # ------------------------------------------------------------------
    def generate_mc_ensemble(self, base_res, sigma_r=0.010, n_samples=600,
                             err_model="gaussian", seed=None):
        rng = np.random.default_rng(SimConfig.MC_SEED if seed is None else seed)
        t1, t2 = base_res["t1"], base_res["t2"]
        r1, r2 = base_res["r1"], base_res["r2"]
        inv = base_res["inversion"]
        p = inv["n_params"]
        theta0 = np.array(inv["theta_map"], dtype=float)
        cov = np.atleast_2d(inv["cov_theta"])
        J_pg = np.atleast_2d(base_res["sensitivity"])          # (3, p)

        # ---- 1) 观测误差抽样 → 三点法解析快速重反演 v0 / a（第三帧用最小二乘） ----
        t3 = base_res.get("t3")
        r3 = base_res.get("r3")
        if t3 is not None:
            obs = np.vstack([np.asarray(r1, float), np.asarray(r2, float), np.asarray(r3, float)])
            n_frames = 3
            t_vec = np.array([t1, t2, t3], dtype=float)
        else:
            obs = np.vstack([np.asarray(r1, float), np.asarray(r2, float)])
            n_frames = 2
            t_vec = np.array([t1, t2], dtype=float)
        noise = self.sample_obs_noise(rng, n_samples, err_model, sigma_r, n_frames)
        obs_noisy = obs[None, :, :] + noise
        X_mat = np.stack([t_vec, 0.5 * t_vec ** 2], axis=1)          # (m, 2)
        mc_v0 = np.zeros((n_samples, 3))
        mc_a = np.zeros((n_samples, 3))
        for d in range(3):
            rhs = obs_noisy[:, :, d] - SimConfig.R0[d]               # (n, m)
            va, *_ = np.linalg.lstsq(X_mat, rhs.T, rcond=None)       # (2, n)
            mc_v0[:, d] = va[0]
            mc_a[:, d] = va[1]

        # ---- 2) 参数后验抽样（多元正态；log C_D 在变换空间抽样） ----
        try:
            theta_dev = rng.multivariate_normal(np.zeros(p), cov, size=n_samples)
        except Exception:
            theta_dev = np.zeros((n_samples, p))

        # ---- 3) MAP 轨迹相对解析基线的气动偏移 ----
        delta_aero = base_res["states_ode"][:3, :] - base_res["pos_ca"]   # (3, N) 供粒子云
        p_g_ca = SimConfig.R0 + base_res["v0_ca"] * base_res["t_goal_ca"] \
            + 0.5 * base_res["acc_ca"] * base_res["t_goal_ca"] ** 2
        t_ev = float(base_res["t_event"])
        p_ev = np.asarray(base_res["event_pos"], dtype=float)
        dt_shift = t_ev - base_res["t_goal_ca"]
        dp_shift = p_ev - p_g_ca

        # ---- 4) 每样本事件量（解析落点 + 气动偏移 + 一阶参数传播） ----
        disc = mc_v0[:, 0] ** 2 - 2.0 * mc_a[:, 0] * (SimConfig.R0[0] - SimConfig.GOAL_X)
        ax_mc = mc_a[:, 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            t_ca = (-mc_v0[:, 0] + np.sqrt(np.maximum(disc, 0.0))) / ax_mc
        t_ca = np.where(np.abs(ax_mc) < 1e-6,
                        (SimConfig.GOAL_X - SimConfig.R0[0]) / np.maximum(mc_v0[:, 0], 1e-6),
                        t_ca)
        t_ca = np.where(t_ca > 0, t_ca, (SimConfig.GOAL_X - SimConfig.R0[0]) / np.maximum(mc_v0[:, 0], 1e-6))

        p_ca = SimConfig.R0[None, :] + mc_v0 * t_ca[:, None] + 0.5 * mc_a * (t_ca[:, None] ** 2)
        dev = theta_dev @ J_pg.T                                    # (n, 3): [dt, dy, dz]
        t_g = t_ca + dt_shift + dev[:, 0]
        corr = np.zeros((n_samples, 3))
        corr[:, 1:] = dev[:, 1:]                                    # 位置修正只作用于 (y, z)
        p_g = p_ca + dp_shift[None, :] + corr

        y_g = p_g[:, 1]
        z_g = p_g[:, 2]

        # ---- 5) 事件标签分类（不删除任何样本） ----
        timeout = (t_g <= 0) | (t_g > SimConfig.T_MAX_FLIGHT)
        ground = (~timeout) & (z_g <= SimConfig.RADIUS)
        reach = (~timeout) & (~ground)
        yc_lo, yc_hi = SimConfig.GOAL_Y_MIN + SimConfig.RADIUS, SimConfig.GOAL_Y_MAX - SimConfig.RADIUS
        zc_lo, zc_hi = SimConfig.RADIUS, SimConfig.GOAL_Z_MAX - SimConfig.RADIUS
        in_full = reach & (y_g > yc_lo) & (y_g < yc_hi) & (z_g > zc_lo) & (z_g < zc_hi)
        in_center = reach & (np.abs(y_g) < 3.66) & (z_g > 0) & (z_g < 2.44)

        vx_at_g = mc_v0[:, 0] + mc_a[:, 0] * t_g
        near_tangent = reach & (np.abs(vx_at_g) < SimConfig.NEAR_TANGENT_VX)

        labels = np.empty(n_samples, dtype=object)
        labels[:] = "timeout"
        labels[ground] = "ground"
        labels[reach] = "goal_out"
        labels[in_full] = "goal_in"

        n = n_samples
        n_reach = int(reach.sum())
        n_in = int(in_full.sum())
        probs = {
            "n_total": n,
            "n_reach": n_reach,
            "n_ground": int(ground.sum()),
            "n_timeout": int(timeout.sum()),
            "n_in_full": n_in,
            "n_in_center": int(in_center.sum()),
            "P_reach": n_reach / n,
            "P_in_given_reach": (n_in / n_reach) if n_reach else 0.0,
            "P_in_and_reach": n_in / n,
            "P_ground": float(ground.mean()),
            "P_timeout": float(timeout.mean()),
            "P_near_tangent": float(near_tangent.mean()),
        }

        # ---- 6) 落点统计（基于到达球门平面的样本） ----
        stats = {"t_g": {}, "y": {}, "z": {}, "ellipse_pts": None, "hdr": None, "mode": None}
        if n_reach:
            gy, gz = y_g[reach], z_g[reach]
            tg = t_g[reach]
            for name, arr in (("t_g", tg), ("y", gy), ("z", gz)):
                q = np.quantile(arr, [0.025, 0.25, 0.5, 0.75, 0.975])
                stats[name] = {"q025": q[0], "q25": q[1], "median": q[2],
                               "q75": q[3], "q975": q[4], "mean": float(np.mean(arr)),
                               "std": float(np.std(arr))}

            # 核密度众数（2D 网格）
            stats["mode"] = self._density_mode(gy, gz)
            # 50% / 95% 高斯联合椭圆（χ²₂ 阈值）
            stats["ellipse_pts_50"] = self._gaussian_ellipse(gy, gz, SimConfig.CHI2_50_2D)
            stats["ellipse_pts"] = self._gaussian_ellipse(gy, gz, SimConfig.CHI2_95_2D)
            # 95% 最高密度区域（KDE 等高线阈值）
            stats["hdr"] = self._hdr_region(gy, gz, 0.95)
        else:
            for key in ("t_g", "y", "z"):
                stats[key] = {"q025": np.nan, "q25": np.nan, "median": np.nan,
                              "q75": np.nan, "q975": np.nan, "mean": np.nan, "std": np.nan}

        return {
            "mc_v0": mc_v0,
            "mc_a": mc_a,
            "delta_aero": delta_aero,
            "goal_y_mc": y_g[reach] if n_reach else np.array([]),
            "goal_z_mc": z_g[reach] if n_reach else np.array([]),
            "t_g_mc": t_g[reach] if n_reach else np.array([]),
            "y_g_all": y_g,
            "z_g_all": z_g,
            "t_g_all": t_g,
            "labels": labels,
            "probs": probs,
            "stats": stats,
            "err_model": err_model,
            "sigma_r": sigma_r,
            "seed": SimConfig.MC_SEED if seed is None else seed,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def get_cloud_at_frame(mc_data, t_curr, frame_idx):
        """进度条当前时刻 t_curr 的三维粒子云 (N, 3)。"""
        cloud_pos = (
            SimConfig.R0[None, :]
            + mc_data["mc_v0"] * t_curr
            + 0.5 * mc_data["mc_a"] * (t_curr ** 2)
            + mc_data["delta_aero"][:, frame_idx][None, :]
        )
        return cloud_pos

    # ------------------------------------------------------------------
    @staticmethod
    def _density_mode(gy, gz, bins=40):
        hist, ye, ze = np.histogram2d(gy, gz, bins=bins)
        iy, iz = np.unravel_index(np.argmax(hist), hist.shape)
        return {"y": 0.5 * (ye[iy] + ye[iy + 1]), "z": 0.5 * (ze[iz] + ze[iz + 1])}

    @staticmethod
    def _gaussian_ellipse(gy, gz, chi2, n_pts=100):
        mean = np.array([np.mean(gy), np.mean(gz)])
        cov = np.cov(np.vstack([gy, gz]))
        eigvals, eigvecs = np.linalg.eigh(cov)
        th = np.linspace(0, 2 * np.pi, n_pts)
        circle = np.vstack([np.cos(th), np.sin(th)])
        half = np.sqrt(np.maximum(eigvals, 1e-9)) * np.sqrt(chi2)
        return mean[:, None] + eigvecs @ np.diag(half) @ circle

    @staticmethod
    def _hdr_region(gy, gz, mass=0.95, grid=64):
        """简版最高密度区域：KDE 网格密度等高线阈值（含 mass 质量）。"""
        try:
            kde = gaussian_kde(np.vstack([gy, gz]))
        except Exception:
            return None
        pad = 0.1
        y_lo, y_hi = float(np.min(gy)) - pad, float(np.max(gy)) + pad
        z_lo, z_hi = float(np.min(gz)) - pad, float(np.max(gz)) + pad
        yy = np.linspace(y_lo, y_hi, grid)
        zz = np.linspace(z_lo, z_hi, grid)
        Y, Z = np.meshgrid(yy, zz)
        dens = kde(np.vstack([Y.ravel(), Z.ravel()])).reshape(grid, grid)
        dens /= dens.sum()
        flat = np.sort(dens.ravel())[::-1]
        csum = np.cumsum(flat)
        level = float(flat[np.searchsorted(csum, mass)])
        return {"y": yy, "z": zz, "density": dens, "level": level}

    # ------------------------------------------------------------------
    def model_envelope(self, t1, t2, r1, r2, sigma_r, n_samples, err_model, wind,
                       models=("A-1", "A-2", "B")):
        """模型包络与方差分解（论文 §6.1）：
        Var(P_g|D) = E_M[Var(P_g|D,M)] + Var_M(E[P_g|D,M])。
        各模型独立反演并传播，输出条件均值/协方差与两类方差的逐轴分解。"""
        sigma_obs = max(sigma_r, 1e-4) if err_model == "gaussian" else SimConfig.ROUNDING_HALFWIDTH / np.sqrt(3.0)
        rows = []
        for mid in models:
            try:
                fix_cd = SimConfig.CD_A_PRIOR_MEAN if mid == "A-1" else None
                res = self.physics_engine.predict(
                    mid, t1, t2, r1, r2, sigma_obs=sigma_obs, wind=wind, fix_cd=fix_cd)
                mc = self.generate_mc_ensemble(
                    res, sigma_r=sigma_r, n_samples=n_samples, err_model=err_model)
                st = mc["stats"]
                rows.append({
                    "model": mid,
                    "mean_y": st["y"]["mean"], "std_y": st["y"]["std"],
                    "mean_z": st["z"]["mean"], "std_z": st["z"]["std"],
                    "t_g_median": st["t_g"]["median"],
                    "P_reach": mc["probs"]["P_reach"],
                    "P_in_given_reach": mc["probs"]["P_in_given_reach"],
                    "status": res["event_label"],
                })
            except Exception as e:
                rows.append({"model": mid, "mean_y": np.nan, "std_y": np.nan,
                             "mean_z": np.nan, "std_z": np.nan,
                             "t_g_median": np.nan, "P_reach": np.nan,
                             "P_in_given_reach": np.nan, "status": f"ERR:{type(e).__name__}"})

        valid = [r for r in rows if not np.isnan(r["mean_y"])]
        decomp = _variance_decomposition(rows)
        return rows, decomp

    # ------------------------------------------------------------------
    def model_envelope_parallel(self, t1, t2, r1, r2, sigma_r, n_samples, err_model, wind,
                                models=("A-1", "A-2", "B"), n_jobs=None, seed=None):
        """离线论文批量并行版（多进程），用于大样本/多模型重计算。
        注意：Streamlit 交互界面请使用串行版 model_envelope；
        本方法面向独立 Python 脚本（须置于 if __name__ == "__main__" 保护内运行）。"""
        import os
        from concurrent.futures import ProcessPoolExecutor

        sigma_obs = max(sigma_r, 1e-4) if err_model == "gaussian" else SimConfig.ROUNDING_HALFWIDTH / np.sqrt(3.0)
        n_jobs = n_jobs if n_jobs else min(len(models), os.cpu_count() or 2)
        jobs = []
        for mid in models:
            fix_cd = SimConfig.CD_A_PRIOR_MEAN if mid == "A-1" else None
            jobs.append((mid, t1, t2, np.asarray(r1, float), np.asarray(r2, float),
                         sigma_obs, np.asarray(wind, float), fix_cd,
                         sigma_r, n_samples, err_model, seed))
        with ProcessPoolExecutor(max_workers=n_jobs) as ex:
            rows = list(ex.map(_run_model_job, jobs))
        decomp = _variance_decomposition(rows)
        return rows, decomp
