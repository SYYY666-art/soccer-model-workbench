import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from config import SimConfig


# =====================================================================
# 模块 1：A/B/C 三种气动闭合管线（论文 §4）
# 三种管线共享同一状态接口、观测似然、参数约束、积分器与事件定位，
# 仅改变气动闭合关系，从而保证模型间比较的公平性。
# =====================================================================
class AeroClosureBase:
    """气动闭合统一接口：输入相对风速 u 与角速度 omega，输出 (Cd, Cl, Cs, extrapolation_flag)。"""
    model_id = "?"

    def __call__(self, u, omega, t=0.0):
        raise NotImplementedError


class ClosureA(AeroClosureBase):
    """A：常系数阻力 + 简化 Magnus。
    v̇ = g − k_D|u|u + Ω_eff×u，k_D = ρ A C_D / (2m)。
    Ω_eff 为低阶有效旋转向量(s⁻¹)，将真实自旋与升力比例压缩为两个横向参数，
    不能解释为球的真实角速度；采用该式后不再叠加 C_L 项。"""
    model_id = "A"

    def __init__(self, cd_const):
        self.cd_const = float(cd_const)

    def __call__(self, u, omega, t=0.0):
        return self.cd_const, 0.0, 0.0, False


class ClosureB(AeroClosureBase):
    """B：文献气动系数曲线（Asai 2007 风洞数据 + Goff & Carré 2009/2010 拟合）。

    无旋阻力（Goff & Carré 2010, Eur. J. Phys. 31, 775-784, 式(3)，
    对 Asai et al. 2007, Sports Eng. 10, 101-110 的 Teamgeist 风洞数据拟合）：
        C_D(v) = a + b / (1 + exp[(v - v_c)/v_s]),
        a = 0.155, b = 0.346, v_c = 12.19 m/s, v_s = 1.309 m/s，
        对应临界雷诺数 Re_c ≈ 1.73×10⁵（亚临界 ≈ 0.50 → 超临界 ≈ 0.155）。

    自旋修正（v > v_c 且 Sp > 0.05，式(4)）：
        C_D = c·Sp^d，c = 0.4127，d = 0.3056；
        文献注明该式对 Sp > 0.3 为外推，Sp > 1 无实验数据。

    升力系数：|C_L| 与 Sp 近似线性（Asai 2007 风洞 Sp≤0.3 区斜率与
    Goff & Carré 2010 图 7 线性区综合估计斜率 k ≈ 0.8）；
    Sp > 0.5 取平台值 0.4（Goff & Carré 2010 图 7 观测到的饱和趋势）。
    符号由经典 Magnus 方向 e_L = ω×u/|ω×u| 给出。

    超出数据域的查询（Sp>0.3 的 C_D 外推、Sp>1）置 extrapolation_flag=True，
    不静默外推。参考：Goff & Carré, Am. J. Phys. 77, 1020-1027 (2009)
    （32 面板球后临界 C_D ≈ 0.27-0.30，C_L(Sp≈0.25) ≈ 0.27-0.31）。"""
    model_id = "B"

    # Goff & Carré 2010 式(3)/(4) 拟合参数
    A_CD, B_CD, VC, VS = 0.155, 0.346, 12.19, 1.309
    C_CD, D_CD = 0.4127, 0.3056
    # 升力线性斜率与平台（文献图 6/7 线性区综合估计）
    CL_SLOPE, CL_PLAT, CL_PLAT_SP = 0.8, 0.4, 0.5
    SP_D_EXTRAP = 0.3      # C_D(Sp) 幂律的实验覆盖上界

    def __call__(self, u, omega, t=0.0):
        um = np.linalg.norm(u) + 1e-9
        sp = float(SimConfig.RADIUS * np.linalg.norm(omega) / um)
        flag = bool(sp > 1.0)  # Sp>1 无任何实验数据
        if sp > 0.05 and um > self.VC:
            cd = self.C_CD * sp ** self.D_CD
            flag = flag or bool(sp > self.SP_D_EXTRAP)
        else:
            cd = self.A_CD + self.B_CD / (1.0 + np.exp((um - self.VC) / self.VS))
        cl = self.CL_SLOPE * sp if sp <= self.CL_PLAT_SP else self.CL_PLAT
        return float(cd), float(cl), 0.0, bool(flag)


class ClosureC(AeroClosureBase):
    """C：COMSOL 气动系数图谱 G_C:(Re,S,q,orientation) -> (C_D,C_L,C_S)，经 ComsolAeroBridge 查询。"""
    model_id = "C"

    def __init__(self, bridge):
        self.bridge = bridge

    def __call__(self, u, omega, t=0.0):
        return self.bridge.get_aero_coeffs(u, omega)


# =====================================================================
# 模块 2：三维动力学母模型与事件积分（论文 §3/§8.1）
# =====================================================================
def make_rhs(closure, wind, omega_mode):
    """构造 RHS(t, s, omega)。

    omega_mode = "effective"：A 管线，v̇ = g − k_D|u|u + Ω_eff×u；
    omega_mode = "physical" ：B/C 管线，升力 F_L = (1/2)ρA|u|² C_L e_L，e_L=(ω×u)/|ω×u|。
    阻力和升力均基于相对风速 u = v − v_w，而不是地面系速度。"""
    q = SimConfig.RHO_AIR * SimConfig.AREA / (2.0 * SimConfig.MASS)
    wind = np.asarray(wind, dtype=float)

    def rhs(t, s, omega):
        vel = s[3:]
        u = vel - wind
        um = np.linalg.norm(u) + 1e-9
        cd, cl, cs, _flag = closure(u, omega, t)
        a_drag = -q * cd * um * u
        if omega_mode == "effective":
            # A：Ω_eff×u 低阶有效旋转项，不叠加 C_L（避免重复计算同一效应）
            a_lift = np.cross(np.asarray(omega, dtype=float), u)
        else:
            cross = np.cross(np.asarray(omega, dtype=float), u)
            cnorm = np.linalg.norm(cross)
            e_l = cross / cnorm if cnorm > 1e-6 else np.zeros(3)
            a_lift = q * cl * um * um * e_l
        return np.concatenate([vel, SimConfig.GRAVITY + a_drag + a_lift])

    return rhs


def integrate_flight(rhs, omega_vec, v0, t_max=None, max_step=None,
                     method=None, rtol=None, atol=None):
    """积分飞行 ODE 并定位两个终止事件：
      goal 事件 G_goal = x − 11，direction=+1（首次向前穿越球门平面）；
      ground 事件 G_ground = z − R，direction=−1（向下触地，忽略 t=0 初始接触根）。
    返回 (sol, event_label, t_event)，label ∈ {"goal","ground","timeout"}。
    默认使用论文 §8 规范的高精度 DOP853 设置；内层反演/灵敏度调用可传入更快配置。"""
    t_max = t_max if t_max is not None else SimConfig.T_MAX_FLIGHT
    max_step = max_step if max_step is not None else SimConfig.ODE_MAX_STEP
    method = method if method is not None else SimConfig.ODE_METHOD
    rtol = rtol if rtol is not None else SimConfig.ODE_RTOL
    atol = atol if atol is not None else SimConfig.ODE_ATOL

    def goal_ev(t, s):
        return s[0] - SimConfig.GOAL_X
    goal_ev.terminal = True
    goal_ev.direction = 1.0

    def ground_ev(t, s):
        return s[2] - SimConfig.RADIUS
    ground_ev.terminal = True
    ground_ev.direction = -1.0

    sol = solve_ivp(
        lambda t, s: rhs(t, s, omega_vec),
        [0.0, t_max],
        np.concatenate([SimConfig.R0, np.asarray(v0, dtype=float)]),
        method=method, rtol=rtol, atol=atol,
        events=[goal_ev, ground_ev], max_step=max_step, dense_output=True
    )

    t_goal = [t for t in sol.t_events[0] if t > 1e-9]
    t_ground = [t for t in sol.t_events[1] if t > 1e-9]
    if t_goal and (not t_ground or t_goal[0] <= t_ground[0]):
        return sol, "goal", float(t_goal[0])
    if t_ground:
        return sol, "ground", float(t_ground[0])
    return sol, "timeout", float(sol.t[-1])


# =====================================================================
# 模块 3：数据诊断基线（论文 §2）
# =====================================================================
class TrajectoryPhysicsEngine:
    """三维动力学反演与预测引擎：基线诊断 + 受约束 MAP 反演 + 事件定位 + 灵敏度。"""

    def __init__(self, aero_bridge):
        self.aero_bridge = aero_bridge

    # ---------------- §2.1 相邻区间平均速度 ----------------
    def interval_velocities(self, t1, t2, r1, r2, t3=None, r3=None):
        if t1 <= 0 or t2 <= t1:
            raise ValueError("观测时刻必须满足 0 < t1 < t2")
        r1, r2 = np.asarray(r1, dtype=float), np.asarray(r2, dtype=float)
        v01 = (r1 - SimConfig.R0) / t1
        v12 = (r2 - r1) / (t2 - t1)
        v23 = None
        if t3 is not None:
            if t3 <= t2:
                raise ValueError("观测时刻必须满足 0 < t1 < t2 < t3")
            v23 = (np.asarray(r3, dtype=float) - r2) / (t3 - t2)
        return v01, v12, v23

    # ---------------- §2.2 三点恒加速度插值 ----------------
    def constant_accel_baseline(self, t1, t2, r1, r2, t3=None, r3=None):
        """三点恒加速度 r(t)=r0+v0 t+(1/2)a t²（等间隔 h 时退化为论文公式）。
        提供第三帧时改用三帧最小二乘，噪声放大显著降低。
        返回 v0_ca, acc_ca, t_g_ca, p_g_ca(末点)。"""
        if t1 <= 0 or t2 <= t1:
            raise ValueError("观测时刻必须满足 0 < t1 < t2")
        r1, r2 = np.asarray(r1, dtype=float), np.asarray(r2, dtype=float)
        t_vec = [t1, t2]
        obs = np.vstack([r1, r2])
        if t3 is not None:
            if t3 <= t2:
                raise ValueError("观测时刻必须满足 0 < t1 < t2 < t3")
            t_vec.append(t3)
            obs = np.vstack([obs, np.asarray(r3, dtype=float)])
        X = np.stack([np.asarray(t_vec, float), 0.5 * np.asarray(t_vec, float) ** 2], axis=1)
        v0 = np.zeros(3)
        acc = np.zeros(3)
        for i in range(3):
            sol, *_ = np.linalg.lstsq(X, obs[:, i] - SimConfig.R0[i], rcond=None)
            v0[i], acc[i] = sol[0], sol[1]
        t_g = self._crossing_time(v0[0], acc[0])
        p_g = SimConfig.R0 + v0 * t_g + 0.5 * acc * t_g ** 2
        return v0, acc, t_g, p_g

    @staticmethod
    def _crossing_time(v0x, ax):
        """求解 x(t)=11 的首次正向根（运动学基线用）。"""
        roots = np.roots([0.5 * ax, v0x, SimConfig.R0[0] - SimConfig.GOAL_X])
        pos = [float(r.real) for r in roots if abs(r.imag) < 1e-7 and r.real > 0]
        if pos:
            return min(pos)
        if v0x > 1e-3:
            return (SimConfig.GOAL_X - SimConfig.R0[0]) / v0x
        return SimConfig.T_MAX_FLIGHT

    # ---------------- §2.3 重力基线 ----------------
    def gravity_baselines(self, t1, t2, r1, r2, t3=None, r3=None):
        """两种重力基线（忽略全部气动力）：
          (a) 仅用 r0 与 r1 的 t1 时刻预测（信息时序：不使用 r2/r3）；
          (b) 全部观测的最小二乘拟合固定重力模型。"""
        r1, r2 = np.asarray(r1, dtype=float), np.asarray(r2, dtype=float)
        g = SimConfig.GRAVITY

        # (a) 仅利用 t₁ 帧提供的约束
        v0_a = (r1 - SimConfig.R0) / t1 - 0.5 * g * t1
        t_g_a = (SimConfig.GOAL_X - SimConfig.R0[0]) / v0_a[0] if v0_a[0] > 1e-3 else np.nan
        p_g_a = SimConfig.R0 + v0_a * t_g_a + 0.5 * g * t_g_a ** 2

        # (b) 全部观测帧的最小二乘拟合
        t_vec = np.array([t1, t2] + ([t3] if t3 is not None else []), dtype=float)
        obs = np.vstack([r1, r2])
        if t3 is not None:
            obs = np.vstack([obs, np.asarray(r3, dtype=float)])
        s2 = float(np.sum(t_vec ** 2))
        r_obs = obs - SimConfig.R0[None, :]
        v0_b = np.zeros(3)
        for d in range(3):
            v0_b[d] = float(np.sum(t_vec * (r_obs[:, d] - 0.5 * g[d] * t_vec ** 2)) / s2)
        t_g_b = (SimConfig.GOAL_X - SimConfig.R0[0]) / v0_b[0] if v0_b[0] > 1e-3 else np.nan
        p_g_b = SimConfig.R0 + v0_b * t_g_b + 0.5 * g * t_g_b ** 2

        return {"v0_r1": v0_a, "t_g_r1": t_g_a, "p_g_r1": p_g_a,
                "v0_ls": v0_b, "t_g_ls": t_g_b, "p_g_ls": p_g_b}

    # =====================================================================
    # 模块 4：受约束 MAP 反演（论文 §5）
    # =====================================================================
    def _build_basis(self, r2):
        """构造局部正交基底：e0 沿参考速度方向，e1、e2 为两个横向方向。
        有效旋转参数化约束 Ω_eff·u_ref=0，只反演横向分量 o1,o2。"""
        v_ref = (np.asarray(r2, dtype=float) - SimConfig.R0)
        e0 = v_ref / (np.linalg.norm(v_ref) + 1e-9)
        e1 = np.cross(e0, [0.0, 0.0, 1.0])
        e1 /= (np.linalg.norm(e1) + 1e-9)
        e2 = np.cross(e0, e1)
        return e0, e1, e2

    def invert_model(self, model_id, t1, t2, r1, r2, sigma_obs=0.010,
                     wind=None, fix_cd=None, lam_parallel=0.0, n_starts=3,
                     t3=None, r3=None):
        """受约束加权最小二乘 / 最大后验反演。

        - A-1：外部固定 C_D，反演 v0(3) + 横向 Ω_eff(2)，共 5 参数（稳健低维版本）；
        - A-2：反演 v0(3) + log C_D + 横向 Ω_eff(2)，共 6 参数（六坐标六参数候选，需 SVD 诊断）；
        - B  ：文献曲线外部固定，反演 v0(3) + 真实横向自旋 ω⊥(2)，共 5 参数；
        - C  ：COMSOL 图谱外部固定，参数化同 B。

        正值参数 log 参数化，横向分量带弱高斯先验；多起点优化；返回协方差与 SVD 诊断。"""
        wind = np.asarray(wind, dtype=float) if wind is not None else SimConfig.WIND_DEFAULT.copy()
        obs = np.vstack([np.asarray(r1, dtype=float), np.asarray(r2, dtype=float)])
        times = np.array([t1, t2])
        t_last = t2
        r_last = np.asarray(r2, dtype=float)
        if t3 is not None:
            if t3 <= t2:
                raise ValueError("观测时刻必须满足 0 < t1 < t2 < t3")
            obs = np.vstack([obs, np.asarray(r3, dtype=float)])
            times = np.array([t1, t2, t3])
            t_last = t3
            r_last = np.asarray(r3, dtype=float)
        e0, e1, e2 = self._build_basis(r_last)
        sigma_obs = max(float(sigma_obs), 1e-4)

        v0_ca, acc_ca, t_g_ca, _ = self.constant_accel_baseline(t1, t2, r1, r2, t3, r3)
        t_span = max(2.0 * t_last, 0.5)

        if model_id == "A-1":
            assert fix_cd is not None, "A-1 需要外部固定 C_D"
            closure = ClosureA(fix_cd)
            n_par = 5
            logcd_prior_mean = None
        elif model_id == "A-2":
            closure = ClosureA(SimConfig.CD_A_PRIOR_MEAN)
            n_par = 6
            logcd_prior_mean = float(np.log(SimConfig.CD_A_PRIOR_MEAN))
        elif model_id == "B":
            closure = ClosureB()
            n_par = 5
            logcd_prior_mean = None
        elif model_id == "C":
            if not getattr(self.aero_bridge, "data_loaded", False):
                raise RuntimeError("COMSOL 图谱尚未加载，无法使用 C 管线")
            closure = ClosureC(self.aero_bridge)
            n_par = 5
            logcd_prior_mean = None
        else:
            raise ValueError(f"未知模型管线: {model_id}")

        omega_mode = "effective" if model_id.startswith("A") else "physical"
        o_prior_sigma = SimConfig.OMEGA_EFF_PRIOR_SIGMA if model_id.startswith("A") else 40.0

        def pack_theta(theta):
            v0 = theta[:3]
            if model_id == "A-2":
                cd = float(np.exp(theta[3]))
                o1, o2 = theta[4], theta[5]
            else:
                cd = float(fix_cd) if model_id == "A-1" else None
                o1, o2 = theta[3], theta[4]
            omega = o1 * e1 + o2 * e2
            if model_id.startswith("A"):
                omega = omega + lam_parallel * e0   # 轴向诊断分量，不直接贡献经典 Magnus 力
            return v0, cd, omega

        def residual(theta):
            theta = np.asarray(theta, dtype=float)
            v0, cd, omega = pack_theta(theta)
            closure_local = ClosureA(cd) if model_id == "A-2" else closure
            rhs = make_rhs(closure_local, wind, omega_mode)
            # 反演内层采用 LSODA 加速（实测较 DOP853 快约 5 倍）；
            # 最终事件定位仍遵循论文 §8 的高精度 DOP853 规范
            sol = solve_ivp(
                lambda t, s: rhs(t, s, omega), [0.0, t_span],
                np.concatenate([SimConfig.R0, v0]),
                method="LSODA", rtol=1e-6, atol=1e-8,
                max_step=SimConfig.ODE_MAX_STEP, dense_output=True
            )
            pred = sol.sol(times)[:3].T
            res = ((pred - obs) / sigma_obs).ravel()
            # 弱先验正则项（MAP 目标函数）
            if model_id == "A-2":
                res = np.append(res, (theta[3] - logcd_prior_mean) / SimConfig.CD_A_PRIOR_SIGMA_LOG)
            res = np.append(res, [theta[n_par - 2] / o_prior_sigma, theta[n_par - 1] / o_prior_sigma])
            return res

        # 多起点优化：以不同初值规避局部极值
        base = np.zeros(n_par)
        base[:3] = v0_ca
        if model_id == "A-2":
            base[3] = float(np.log(SimConfig.CD_A_PRIOR_MEAN))
        base[-2:] = [0.35, 0.04]
        starts = [base.copy()]
        if n_starts > 1:
            s2 = base.copy(); s2[-2:] = [1.2, 0.3]
            starts.append(s2)
        if n_starts > 2:
            s3 = base.copy(); s3[-2:] = [-0.8, 0.9]
            starts.append(s3)

        best = None
        for st in starts[:n_starts]:
            try:
                r = least_squares(residual, st, xtol=1e-8, ftol=1e-8, max_nfev=250)
            except Exception:
                continue
            cost = float(np.sum(r.fun ** 2))
            if best is None or cost < best[0]:
                best = (cost, r)
        if best is None:
            raise RuntimeError("反演优化失败：所有起点均未收敛")

        res = best[1]
        theta_map = res.x
        v0_opt, cd_opt, omega_opt = pack_theta(theta_map)

        # 协方差与 SVD 可辨识性诊断（论文 §5.3）
        jac = np.atleast_2d(res.jac)                      # (m, p)
        _, sv, _ = np.linalg.svd(jac)
        sv = sv[sv > 1e-14]
        cond = float(sv.max() / sv.min()) if len(sv) else np.inf
        jtj = jac.T @ jac
        cov_theta = np.linalg.pinv(jtj)
        se_theta = np.sqrt(np.clip(np.diag(cov_theta), 0.0, None))

        inversion = {
            "model_id": model_id,
            "n_params": n_par,
            "theta_map": theta_map,
            "cov_theta": cov_theta,
            "se_theta": se_theta,
            "sv": sv,
            "cond": cond,
            "rms_res": float(np.sqrt(np.mean(res.fun[:6] ** 2))) * sigma_obs,   # 位置残差 RMS (m)
            "n_starts": n_starts,
            "sigma_obs": sigma_obs,
        }
        return v0_opt, cd_opt, omega_opt, inversion, closure

    # =====================================================================
    # 模块 5：主预测（反演 → 事件积分 → 网格状态）
    # =====================================================================
    def predict(self, model_id, t1, t2, r1, r2, sigma_obs=0.010, wind=None,
                fix_cd=None, lam_parallel=0.0, n_starts=3, t3=None, r3=None):
        wind = np.asarray(wind, dtype=float) if wind is not None else SimConfig.WIND_DEFAULT.copy()
        v0_opt, cd_opt, omega_opt, inversion, closure = self.invert_model(
            model_id, t1, t2, r1, r2, sigma_obs=sigma_obs, wind=wind,
            fix_cd=fix_cd, lam_parallel=lam_parallel, n_starts=n_starts, t3=t3, r3=r3)

        omega_mode = "effective" if model_id.startswith("A") else "physical"
        rhs = make_rhs(closure, wind, omega_mode)
        sol_goal, label, t_event = integrate_flight(rhs, omega_opt, v0_opt)

        # 事件落点与近切触标记
        p_event = sol_goal.sol(t_event)[:3] if t_event is not None else None
        v_event = sol_goal.sol(t_event)[3:] if t_event is not None else None
        near_tangent = bool(v_event is not None and abs(v_event[0]) < SimConfig.NEAR_TANGENT_VX)

        t_end = float(max(min(t_event if label != "timeout" else sol_goal.t[-1], sol_goal.t[-1]), 1e-3))
        t_eval = np.linspace(0.0, t_end, 200)
        states_ode = sol_goal.sol(t_eval)

        q = SimConfig.RHO_AIR * SimConfig.AREA / (2.0 * SimConfig.MASS)
        acc_total = np.zeros((3, len(t_eval)))
        acc_drag = np.zeros((3, len(t_eval)))
        acc_lift = np.zeros((3, len(t_eval)))
        cd_traj = np.zeros(len(t_eval))
        for i in range(len(t_eval)):
            vi = states_ode[3:, i]
            u = vi - wind
            um = np.linalg.norm(u) + 1e-9
            cd, cl, cs, _flag = closure(u, omega_opt, t_eval[i])
            cd_traj[i] = cd
            ad = -q * cd * um * u
            if omega_mode == "effective":
                al = np.cross(omega_opt, u)
            else:
                cross = np.cross(omega_opt, u)
                cn = np.linalg.norm(cross)
                e_l = cross / cn if cn > 1e-6 else np.zeros(3)
                al = q * cl * um * um * e_l
            acc_drag[:, i] = ad
            acc_lift[:, i] = al
            acc_total[:, i] = SimConfig.GRAVITY + ad + al

        v0_ca, acc_ca, t_g_ca, p_g_ca = self.constant_accel_baseline(t1, t2, r1, r2, t3, r3)
        pos_ca = SimConfig.R0[:, None] + v0_ca[:, None] * t_eval[None, :] + 0.5 * acc_ca[:, None] * (t_eval[None, :] ** 2)

        # 事件时间/落点对参数的灵敏度（论文 §6.5，中心差分）
        sensitivity = self._event_sensitivity(
            model_id, t1, t2, r1, r2, sigma_obs, wind, fix_cd, lam_parallel,
            v0_opt, omega_opt, inversion, t_event, p_event, t3, r3)

        baselines = {
            "interval": self.interval_velocities(t1, t2, r1, r2, t3, r3),
            "gravity": self.gravity_baselines(t1, t2, r1, r2, t3, r3),
        }

        return {
            # 网格化状态输出（供可视化与统计复用）
            "t_eval": t_eval,
            "states_ode": states_ode,
            "acc_total": acc_total,
            "acc_drag": acc_drag,
            "acc_magnus": acc_lift,          # 升力/有效旋转项（旧名兼容）
            "pos_ca": pos_ca,
            "v0_ode": v0_opt,
            "cd_ode": (cd_opt if cd_opt is not None
                       else float(np.mean(cd_traj))),   # B/C：曲线给定，报告轨迹平均 C_D
            "omega_ode": omega_opt,
            "t_goal_ode": float(t_event) if label == "goal" else float(t_end),
            "v0_ca": v0_ca,
            "acc_ca": acc_ca,
            "t_goal_ca": t_g_ca,
            # ---- 输入与风场（供蒙特卡洛引擎复用） ----
            "t1": t1,
            "t2": t2,
            "r1": np.asarray(r1, dtype=float),
            "r2": np.asarray(r2, dtype=float),
            "t3": t3,
            "r3": None if r3 is None else np.asarray(r3, dtype=float),
            "wind": wind,
            # ---- 事件与诊断 ----
            "model_id": model_id,
            "event_label": label,
            "t_event": float(t_event),
            "event_pos": p_event,
            "event_vel": v_event,
            "near_tangent": near_tangent,
            "inversion": inversion,
            "baselines": baselines,
            "sensitivity": sensitivity,
            "sigma_obs": sigma_obs,
        }

    def _event_sensitivity(self, model_id, t1, t2, r1, r2, sigma_obs, wind, fix_cd,
                           lam_parallel, v0_opt, omega_opt, inversion, t_event, p_event,
                           t3=None, r3=None):
        """中心差分计算 (t_g, y_g, z_g) 对反演参数的灵敏度矩阵 J_pg (3×p)。
        线性传播依据论文公式 6.5。"""
        p = inversion["n_params"]
        theta0 = np.array(inversion["theta_map"], dtype=float)
        omega_mode = "effective" if model_id.startswith("A") else "physical"
        basis_r = np.asarray(r3, dtype=float) if r3 is not None else np.asarray(r2, dtype=float)
        e0, e1, e2 = self._build_basis(basis_r)
        # 灵敏度差分需复用与反演一致的闭合关系（B/C 管线由外部曲线/图谱给定）
        if model_id == "B":
            closure_b = ClosureB()
        elif model_id == "C":
            closure_b = ClosureC(self.aero_bridge)
        else:
            closure_b = None
        jac = np.zeros((3, p))
        eps = SimConfig.FD_EPS
        for j in range(p):
            row = np.zeros(3)
            for sign in (+1.0, -1.0):
                th = theta0.copy()
                th[j] = theta0[j] + sign * eps * max(abs(theta0[j]), 1.0)
                v0t = th[:3]
                if model_id == "A-2":
                    cdt = float(np.exp(th[3])); o1t, o2t = th[4], th[5]
                else:
                    cdt = fix_cd; o1t, o2t = th[3], th[4]
                omt = o1t * e1 + o2t * e2
                if model_id.startswith("A"):
                    omt = omt + lam_parallel * e0
                closure_t = ClosureA(cdt) if model_id == "A-2" else (
                    ClosureA(fix_cd) if model_id == "A-1" else closure_b)
                rhs_t = make_rhs(closure_t, wind, omega_mode)
                try:
                    # 灵敏度差分采用 LSODA 加速并放宽容差；该精度对一阶误差传播已充分
                    sol_t, lab_t, te_t = integrate_flight(
                        rhs_t, omt, v0t, method="LSODA", rtol=1e-5, atol=1e-7)
                    pe_t = sol_t.sol(te_t)[:3] if te_t is not None else np.full(3, np.nan)
                    row += sign * np.array([te_t, pe_t[1], pe_t[2]])
                except Exception:
                    row += sign * np.full(3, np.nan)
            jac[:, j] = row / (2.0 * eps * max(abs(theta0[j]), 1.0))
        return jac
