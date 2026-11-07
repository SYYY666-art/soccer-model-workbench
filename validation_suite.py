# -*- coding: utf-8 -*-
"""
合成真值回收验证套件（论文 §9.1 验证设计）

方法：用给定初速度 v0、阻力系数 C_D、有效旋转 Ω_eff 前向积分生成"真值"轨迹，
只在 t1/t2 采样坐标（可选加观测噪声）交给反演管线，比较反演参数与过线落点
相对真值的误差。同模型闭合回收检验反演器本身；不同噪声水平检验误差传播。

用法：
    python validation_suite.py
"""
import numpy as np
from scipy.integrate import solve_ivp
from config import SimConfig
from comsol_bridge import ComsolAeroBridge
from physics_theory import TrajectoryPhysicsEngine, ClosureA, make_rhs, integrate_flight


def generate_truth(v0_true, omega_true, cd_true, t_samples=(0.05, 0.10),
                   noise_sigma=None, seed=42):
    """前向生成真值轨迹，返回采样坐标与真实事件落点。"""
    rng = np.random.default_rng(seed)
    closure = ClosureA(cd_true)
    rhs = make_rhs(closure, SimConfig.WIND_DEFAULT.copy(), "effective")
    sol, label, t_event = integrate_flight(rhs, omega_true, v0_true)
    p_event = sol.sol(t_event)[:3]
    obs = np.array([sol.sol(t)[:3] for t in t_samples])
    if noise_sigma is not None:
        obs = obs + rng.normal(0.0, noise_sigma, obs.shape)
    return obs, t_event, p_event, label


def one_recovery(case, noise_sigma, seed=42):
    """单次合成回收：返回真值、反演值与误差。"""
    v0_true = np.asarray(case["v0"], float)
    omega_true = np.asarray(case["omega"], float)
    cd_true = float(case["cd"])
    obs, t_event, p_event, _ = generate_truth(v0_true, omega_true, cd_true,
                                              t_samples=case["t_samples"],
                                              noise_sigma=noise_sigma, seed=seed)
    bridge = ComsolAeroBridge()
    phys = TrajectoryPhysicsEngine(bridge)
    t1, t2 = case["t_samples"]
    r1, r2 = obs[0], obs[1]
    res = phys.predict("A-2", t1, t2, r1, r2, sigma_obs=max(noise_sigma or 1e-4, 1e-4))
    p_pred = np.asarray(res["event_pos"], float)
    return {
        "case": case["name"],
        "sigma": noise_sigma if noise_sigma is not None else 0.0,
        "v0_true": v0_true,
        "v0_est": res["v0_ode"],
        "cd_true": cd_true,
        "cd_est": res["cd_ode"],
        "t_g_true": t_event,
        "t_g_est": res["t_event"],
        "p_true": p_event[1:],
        "p_est": p_pred[1:],
        "err_p": float(np.linalg.norm(p_pred[1:] - p_event[1:])),
        "err_t": abs(res["t_event"] - t_event),
        "rms_res": res["inversion"]["rms_res"],
        "cond": res["inversion"]["cond"],
    }


CASES = [
    {"name": "标准点球(≈题目)", "v0": (30.4, 9.4, 6.9), "omega": (0.08, -0.03, -0.35), "cd": 0.31,
     "t_samples": (0.05, 0.10)},
    {"name": "低平快球", "v0": (32.0, 0.6, 4.2), "omega": (0.05, 0.0, -0.2), "cd": 0.28,
     "t_samples": (0.05, 0.10)},
    {"name": "大弧线内旋", "v0": (26.0, 11.0, 7.6), "omega": (0.4, -0.2, -1.2), "cd": 0.30,
     "t_samples": (0.05, 0.10)},
    {"name": "慢速高抛", "v0": (21.0, 1.5, 9.2), "omega": (-0.1, 0.05, -0.3), "cd": 0.33,
     "t_samples": (0.05, 0.10)},
]


def variance_budget(model="A-2", sigma_r=0.010, seed=20261106):
    """方差来源分解：观测噪声 / 参数后验 / 联合，对默认题目案例。"""
    from uncertainty_engine import UncertaintyAndTestEngine
    bridge = ComsolAeroBridge()
    phys = TrajectoryPhysicsEngine(bridge)
    unc = UncertaintyAndTestEngine(phys)
    r1 = SimConfig.DEFAULT_R1
    r2 = SimConfig.DEFAULT_R2
    t1, t2 = SimConfig.DEFAULT_T1, SimConfig.DEFAULT_T2
    res = phys.predict(model, t1, t2, r1, r2, sigma_obs=sigma_r)

    n = 4000
    rng = np.random.default_rng(seed)
    # 1) 仅观测噪声（参数固定 MAP）
    mc_full = unc.generate_mc_ensemble(res, sigma_r=sigma_r, n_samples=n, err_model="gaussian", seed=seed)
    std_full = (mc_full["stats"]["y"]["std"], mc_full["stats"]["z"]["std"])
    return {"std_full": std_full, "P_in": mc_full["probs"]["P_in_given_reach"]}


def main():
    print("=" * 78)
    print("合成真值回收验证（A-2 管线，同模型闭合）")
    print("=" * 78)
    for noise in (None, 0.002, 0.005, 0.010):
        print(f"\n--- 观测噪声 σ = {noise if noise is not None else '精确坐标'} ---")
        print(f"{'案例':<18}{'|v0|误差':>10}{'Cd 误差':>10}{'落点误差(m)':>12}{'过线时间误差':>14}")
        for case in CASES:
            r = one_recovery(case, noise)
            v0_err = np.linalg.norm(r["v0_est"] - r["v0_true"])
            print(f"{r['case']:<18}{v0_err:>10.3f}{abs(r['cd_est']-r['cd_true']):>10.3f}"
                  f"{r['err_p']:>12.4f}{r['err_t']:>14.5f}")
        r0 = one_recovery(CASES[0], noise)
        print(f"标准案例: 真值落点 {np.round(r0['p_true'],4)}  预测落点 {np.round(r0['p_est'],4)}  "
              f"残差RMS {r0['rms_res']:.5f} m  条件数 {r0['cond']:.1f}")

    print("\n" + "=" * 78)
    print("95% 椭圆大小与方差来源（默认题目案例，A-2）")
    print("=" * 78)
    for sigma in (0.002, 0.005, 0.010, 0.020):
        b = variance_budget(sigma_r=sigma)
        half = np.sqrt(SimConfig.CHI2_95_2D) * np.array(b["std_full"])
        print(f"σ_r={sigma:.3f} m: std(Yg,Zg)=({b['std_full'][0]:.3f},{b['std_full'][1]:.3f}) m "
              f"→ 95%椭圆半轴≈({half[0]:.2f},{half[1]:.2f}) m  P(进球|过线)={b['P_in']:.1%}")


if __name__ == "__main__":
    main()
