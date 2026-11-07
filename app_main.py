import numpy as np
import pandas as pd
import streamlit as st
from pathlib import Path
from config import SimConfig
from comsol_bridge import ComsolAeroBridge
import comsol_lab
from i18n import t
from physics_theory import TrajectoryPhysicsEngine
from uncertainty_engine import UncertaintyAndTestEngine
from visualizer_3d import PenaltyVisualizer3D


@st.cache_resource
def init_engines():
    bridge = ComsolAeroBridge()
    table_path = Path("data") / "comsol_table.csv"
    if not table_path.exists():
        try:
            comsol_lab.generate_comsol_table(table_path)
        except Exception:
            pass
    if table_path.exists():
        try:
            bridge.load_comsol_table(str(table_path))
        except Exception:
            pass
    phys = TrajectoryPhysicsEngine(bridge)
    unc = UncertaintyAndTestEngine(phys)
    return bridge, phys, unc


@st.cache_data(show_spinner=False, max_entries=32)
def cached_pipeline(model_id, t1, t2, x1, y1, z1, x2, y2, z2, sigma_obs,
                    wx, wy, wz, fix_cd, lam_parallel, sigma_r, n_samples, err_model,
                    t3_arg, r3_arg):
    """反演 + 蒙特卡洛传播缓存：相同参数组合只计算一次。"""
    bridge, phys, unc = init_engines()
    r1 = np.array([x1, y1, z1])
    r2 = np.array([x2, y2, z2])
    wind = np.array([wx, wy, wz])
    r3 = np.array(r3_arg) if r3_arg is not None else None
    base_res = phys.predict(model_id, t1, t2, r1, r2, sigma_obs=sigma_obs,
                            wind=wind, fix_cd=fix_cd, lam_parallel=lam_parallel,
                            t3=t3_arg, r3=r3)
    mc_data = unc.generate_mc_ensemble(base_res, sigma_r=sigma_r,
                                       n_samples=n_samples, err_model=err_model)
    return base_res, mc_data


@st.cache_data(show_spinner=False, max_entries=8)
def cached_envelope(t1, t2, x1, y1, z1, x2, y2, z2, sigma_obs,
                    wx, wy, wz, sigma_r, n_samples, err_model, models_tuple):
    """模型包络缓存：models 组合相同时直接复用结果。"""
    bridge, phys, unc = init_engines()
    r1 = np.array([x1, y1, z1])
    r2 = np.array([x2, y2, z2])
    wind = np.array([wx, wy, wz])
    return unc.model_envelope(t1, t2, r1, r2, sigma_r, n_samples, err_model, wind,
                              models=list(models_tuple))


def inject_clean_css():
    st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
        }
        .clean-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-top: 3px solid #0d9488;
            border-radius: 8px;
            padding: 8px 10px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
            min-height: 96px;
            height: auto;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 3px;
        }
        .clean-label {
            font-size: 0.75rem;
            color: #64748b;
            font-weight: 600;
            letter-spacing: -0.2px;
            line-height: 1.3;
        }
        .clean-value {
            font-size: 1.05rem;
            color: #0f172a;
            font-weight: 700;
            font-family: 'Consolas', 'Microsoft YaHei', sans-serif;
            white-space: normal;
            word-break: break-word;
            line-height: 1.25;
        }
        .clean-sub {
            font-size: 0.72rem;
            color: #0d9488;
            font-weight: 500;
            white-space: normal;
            word-break: break-word;
            line-height: 1.3;
        }
    </style>
    """, unsafe_allow_html=True)


def render_card(col, label, value, sub_text, color="#0d9488"):
    col.markdown(f"""
    <div class="clean-card" style="border-top-color: {color};">
        <div class="clean-label">{label}</div>
        <div class="clean-value">{value}</div>
        <div class="clean-sub" style="color: {color};">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)


def render_html_table(headers, rows, min_width="560px"):
    """以 HTML 表格渲染（支持 <sub> 等数学下标），替代 st.table 的纯文本渲染。"""
    head = "".join(
        f"<th style='text-align:left;padding:4px 8px;border:1px solid #e2e8f0;"
        f"background:#f8fafc;font-weight:600;white-space:nowrap;'>{h}</th>"
        for h in headers)
    body = "".join(
        "<tr>" + "".join(
            f"<td style='padding:4px 8px;border:1px solid #e2e8f0;white-space:nowrap;'>{c}</td>"
            for c in r) + "</tr>"
        for r in rows)
    st.markdown(
        f"<div style='overflow-x:auto;'><table "
        f"style='border-collapse:collapse;width:100%;min-width:{min_width};"
        f"font-size:0.85rem;'>{head}{body}</table></div>",
        unsafe_allow_html=True)


def common_param_rows(L):
    """通用物理常数与数值规范（双语）。"""
    return [
        (L["pc_rho"], L["pc_rho_v"]),
        (L["pc_mu"], L["pc_mu_v"]),
        (L["pc_g"], L["pc_g_v"]),
        (L["pc_m"], L["pc_m_v"]),
        (L["pc_r"], L["pc_r_v"]),
        (L["pc_re"], L["pc_re_v"]),
        (L["pc_s"], L["pc_s_v"]),
        (L["pc_ode"], L["pc_ode_v"]),
        (L["pc_fric"], L["pc_fric_v"]),
    ]


def pipeline_specific_params(model_id, bridge, lang="zh"):
    """各管线的专属关键参数表（论文 §4，双语）。"""
    L = t(lang)
    if model_id == "A-1":
        return [
            (L["ps_cd"], L["ps_a1_cd_v"]),
            (L["ps_params"], L["ps_a1_par_v"]),
            (L["ps_omega_sigma"], L["ps_a1_sig_v"]),
            (L["ps_closure"], L["ps_a1_clo_v"]),
        ]
    if model_id == "A-2":
        return [
            (L["ps_cd"], L["ps_a2_cd_v"]),
            (L["ps_params"], L["ps_a2_par_v"]),
            (L["ps_diag"], L["ps_a2_diag_v"]),
            (L["ps_closure"], L["ps_a2_clo_v"]),
        ]
    if model_id == "B":
        return [
            (L["ps_source"], L["ps_b_src_v"]),
            (L["ps_params"], L["ps_b_par_v"]),
            (L["ps_omega_sigma_b"], L["ps_b_sig_v"]),
            (L["ps_status"], L["ps_b_sta_v"]),
        ]
    ver = bridge.grid_version if bridge.data_loaded else "—"
    return [
        (L["ps_source"], L["ps_c_src_v"].format(v=ver)),
        (L["ps_domain"], L["ps_c_dom_v"]),
        (L["ps_params"], L["ps_c_par_v"]),
        (L["ps_ref"], L["ps_c_ref_v"]),
    ]


def main():
    st.set_page_config(page_title="Team 991 | UPC 2026 Problem B Workbench", layout="wide")
    inject_clean_css()

    # ---- 语言切换（中 / 英） ----
    if "lang" not in st.session_state:
        st.session_state.lang = "zh"
    lang = st.session_state.lang
    L = t(lang)
    st.title(L["app_title"])

    bridge, phys_engine, unc_engine = init_engines()

    # ==================== 1. 侧边栏 ====================
    with st.sidebar:
        if st.button(L["btn_lang"], width="stretch"):
            st.session_state.lang = "en" if lang == "zh" else "zh"
            st.rerun()

        st.header(L["sec1_obs"])

        # 经典算例库：选择后自动填入坐标，仍可手动微调任意输入
        preset_names = list(SimConfig.CASE_PRESETS)
        # 首次进入：输入框预置基准算例（赛题数据）的取值
        _default_obs = {
            "t1_in": SimConfig.DEFAULT_T1, "t2_in": SimConfig.DEFAULT_T2,
            "x1_in": float(SimConfig.DEFAULT_R1[0]), "y1_in": float(SimConfig.DEFAULT_R1[1]),
            "z1_in": float(SimConfig.DEFAULT_R1[2]), "x2_in": float(SimConfig.DEFAULT_R2[0]),
            "y2_in": float(SimConfig.DEFAULT_R2[1]), "z2_in": float(SimConfig.DEFAULT_R2[2]),
        }
        for _k, _v in _default_obs.items():
            if _k not in st.session_state:
                st.session_state[_k] = _v
        # 选项显示名随语言变化（内部 key 固定），用 index 在 session 中保留选择
        display_names = [SimConfig.CASE_PRESETS[k].get("name_en", k) if lang == "en" else k
                         for k in preset_names]
        if "preset_idx" not in st.session_state:
            st.session_state.preset_idx = 0
        prev_preset = preset_names[min(int(st.session_state.preset_idx), len(preset_names) - 1)]
        picked = st.selectbox(L["preset_label"], display_names,
                              index=st.session_state.preset_idx)
        st.session_state.preset_idx = display_names.index(picked)
        preset = preset_names[st.session_state.preset_idx]
        if preset != prev_preset and preset in SimConfig.CASE_PRESETS:
            c = SimConfig.CASE_PRESETS[preset]
            st.session_state["t1_in"] = float(c["t1"])
            st.session_state["t2_in"] = float(c["t2"])
            st.session_state["x1_in"] = float(c["r1"][0])
            st.session_state["y1_in"] = float(c["r1"][1])
            st.session_state["z1_in"] = float(c["r1"][2])
            st.session_state["x2_in"] = float(c["r2"][0])
            st.session_state["y2_in"] = float(c["r2"][1])
            st.session_state["z2_in"] = float(c["r2"][2])
        preset_cfg = SimConfig.CASE_PRESETS[preset]
        st.caption(preset_cfg["desc"] if lang == "zh" else preset_cfg.get("desc_en", preset_cfg["desc"]))

        c_t1, c_t2 = st.columns(2)
        t1 = c_t1.number_input(L["t1_label"], step=0.01, format="%.2f", key="t1_in")
        t2 = c_t2.number_input(L["t2_label"], step=0.01, format="%.2f", key="t2_in")

        st.markdown(L["pos_t1_md"])
        cx1, cy1, cz1 = st.columns(3)
        x1 = cx1.number_input("x₁", step=0.01, format="%.3f", key="x1_in")
        y1 = cy1.number_input("y₁", step=0.01, format="%.3f", key="y1_in")
        z1 = cz1.number_input("z₁", step=0.01, format="%.3f", key="z1_in")

        st.markdown(L["pos_t2_md"])
        cx2, cy2, cz2 = st.columns(3)
        x2 = cx2.number_input("x₂", step=0.01, format="%.3f", key="x2_in")
        y2 = cy2.number_input("y₂", step=0.01, format="%.3f", key="y2_in")
        z2 = cz2.number_input("z₂", step=0.01, format="%.3f", key="z2_in")

        r1 = np.array([x1, y1, z1])
        r2 = np.array([x2, y2, z2])

        # 可选第三观测帧：信息量显著增加，预测不确定性大幅缩小（论文 §1.3/§5.2）
        use_t3 = st.checkbox(L["use_t3"], value=False, help=L["use_t3_help"], key="use_t3_in")
        if use_t3:
            t3 = st.number_input(L["t3_label"], value=0.15, step=0.01, format="%.2f", key="t3_in")
            st.markdown(L["pos_t3_md"])
            cx3, cy3, cz3 = st.columns(3)
            x3 = cx3.number_input("x₃", value=4.41, step=0.01, format="%.3f", key="x3_in")
            y3 = cy3.number_input("y₃", value=1.24, step=0.01, format="%.3f", key="y3_in")
            z3 = cz3.number_input("z₃", value=1.02, step=0.01, format="%.3f", key="z3_in")
            r3 = np.array([x3, y3, z3])
        else:
            t3, r3 = None, None

        st.divider()
        st.header(L["sec2_err"])
        # radio 选项文本随语言变化，不能绑定 key；用 index 手动在 session 中保留选择
        if "err_idx" not in st.session_state:
            st.session_state.err_idx = 0
        err_choice = st.radio(
            L["err_label"],
            [L["err_gauss"], L["err_uniform"]],
            help=L["err_help"], index=st.session_state.err_idx)
        st.session_state.err_idx = [L["err_gauss"], L["err_uniform"]].index(err_choice)
        if err_choice == L["err_gauss"]:
            err_model = "gaussian"
            sigma_r = st.slider(L["sigma_label"], 0.001, 0.050, SimConfig.SIGMA_R_DEFAULT,
                                0.001, format="%.3f", key="sigma_r_in")
        else:
            err_model = "uniform"
            sigma_r = SimConfig.ROUNDING_HALFWIDTH
            st.caption(L["sigma_equiv"].format(v=f"{SimConfig.ROUNDING_HALFWIDTH / np.sqrt(3.0):.4f}"))
        n_samples = st.select_slider(L["n_samples"],
                                     options=SimConfig.MC_N_OPTIONS, value=SimConfig.MC_N_DEFAULT,
                                     key="n_samples_in")

        st.divider()
        st.header(L["sec3_pipe"])
        model_id = st.selectbox(
            L["pipe_label"],
            ["A-2", "A-1", "B", "C"],
            help=L["pipe_help"], key="model_id_pipe")
        st.markdown(L["pipe_intro"])
        if model_id == "A-1":
            st.caption(L["cap_a1"], unsafe_allow_html=True)
        if model_id == "A-2":
            st.caption(L["cap_a2"], unsafe_allow_html=True)
        if model_id == "B":
            st.caption(L["cap_b"])
        if model_id == "C":
            if bridge.data_loaded:
                st.caption(L["cap_c_ok"].format(v=bridge.grid_version))
            else:
                st.caption(L["cap_c_fail"])

        with st.expander(L["params_title"], expanded=True):
            render_html_table([L["p_param"], L["p_value"]],
                              pipeline_specific_params(model_id, bridge, lang),
                              min_width="420px")
            st.caption(L["params_hint"])
        with st.expander(L["common_title"], expanded=False):
            render_html_table([L["p_param"], L["p_value"]],
                              common_param_rows(L), min_width="420px")

        with st.popover(L["ack_title"], use_container_width=True):
            st.markdown(L["ack_body"])

        st.divider()
        st.header(L["sec4_wind"])
        wx = st.number_input(L["wind_x"], value=0.0, step=0.5, format="%.1f", key="wx_in")
        wy = st.number_input(L["wind_y"], value=0.0, step=0.5, format="%.1f", key="wy_in")
        wz = st.number_input(L["wind_z"], value=0.0, step=0.5, format="%.1f", key="wz_in")
        wind = np.array([wx, wy, wz])
        lam_parallel = st.slider(
            L["lam_label"],
            -10.0, 10.0, SimConfig.OMEGA_PARALLEL_DEFAULT, 0.5,
            help=L["lam_help"], key="lam_in")
        show_cloud = st.checkbox(L["cloud_check"], value=True, help=L["cloud_help"], key="cloud_in")
        show_legend_2d = st.checkbox(L["legend_check"], value=False, help=L["legend_help"],
                                     key="legend_in")

    # ==================== 2. 合法性校验 ====================
    if t1 <= 0 or t2 <= t1:
        st.error(L["err_t12"])
        st.stop()
    if use_t3 and t3 <= t2:
        st.error(L["err_t123"])
        st.stop()

    # ==================== 3. 主模型反演与概率传播 ====================
    sigma_obs = sigma_r if err_model == "gaussian" else SimConfig.ROUNDING_HALFWIDTH / np.sqrt(3.0)
    fix_cd = SimConfig.CD_A_PRIOR_MEAN if model_id == "A-1" else None
    t3_arg = float(t3) if use_t3 else None
    r3_arg = tuple(float(v) for v in r3) if use_t3 else None

    try:
        base_res, mc_data = cached_pipeline(
            model_id, t1, t2, float(x1), float(y1), float(z1), float(x2), float(y2), float(z2),
            sigma_obs, float(wx), float(wy), float(wz), fix_cd, float(lam_parallel),
            sigma_r, n_samples, err_model, t3_arg, r3_arg)
    except Exception as e:
        st.error(L["inv_fail"].format(e=e))
        st.stop()

    inv = base_res["inversion"]
    probs = mc_data["probs"]
    stats = mc_data["stats"]
    se = inv["se_theta"]
    theta = inv["theta_map"]
    if model_id == "A-2":
        cd_se = float(np.exp(theta[3] + se[3]) - np.exp(theta[3] - se[3])) / 2.0
        o_se = (se[4], se[5])
        o_val = (theta[4], theta[5])
    else:
        cd_se, o_se, o_val = 0.0, (se[3], se[4]), (theta[3], theta[4])

    # ==================== 4. 顶部时间进度条与快捷跳转 ====================
    t_end = float(base_res["t_eval"][-1])
    slider_step = max(0.001, round(t_end / 200.0, 3))
    if "frame_time" not in st.session_state:
        st.session_state.frame_time = t_end

    col_slider, col_btns = st.columns([3.2, 1.2])
    with col_btns:
        st.caption(L["jump_cap"])
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("t=0 s", width="stretch"):
            st.session_state.frame_time = 0.0
        if b2.button(f"t={t1} s", width="stretch"):
            st.session_state.frame_time = float(t1)
        if b3.button(f"t={t2} s", width="stretch"):
            st.session_state.frame_time = float(t2)
        if b4.button(L["jump_goal"], width="stretch"):
            st.session_state.frame_time = t_end

    with col_slider:
        frame_time = st.slider(
            L["slider_label"],
            min_value=0.0, max_value=t_end, step=slider_step, format="%.3f",
            value=float(st.session_state.get("frame_time", t_end)))
        frame_time = float(frame_time)
        st.session_state.frame_time = frame_time

    frame_idx = int(np.argmin(np.abs(base_res["t_eval"] - frame_time)))
    t_curr = base_res["t_eval"][frame_idx]
    pos_curr = base_res["states_ode"][:3, frame_idx]
    vel_curr = base_res["states_ode"][3:, frame_idx]
    acc_curr = base_res["acc_total"][:, frame_idx]
    amag_curr = base_res["acc_magnus"][:, frame_idx]
    mc_cloud_curr = unc_engine.get_cloud_at_frame(mc_data, t_curr, frame_idx)

    # ==================== 5. 指标卡片 ====================
    st.write("")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    render_card(k1, L["card_event"], L["event_" + base_res["event_label"]],
                L["card_tg_sub"].format(v=f"{base_res['t_event']:.3f}"), "#2563eb")
    render_card(k2, L["card_v0"],
                f"({base_res['v0_ode'][0]:.2f}, {base_res['v0_ode'][1]:.2f}, {base_res['v0_ode'][2]:.2f}) m/s",
                L["card_rms"].format(v=f"{inv['rms_res']:.4f}"), "#0d9488")
    if model_id == "A-2":
        render_card(k3, L["card_cd_log"],
                    f"{base_res['cd_ode']:.3f} ± {cd_se:.3f}",
                    L["card_cd_prior"].format(m=model_id), "#16a34a")
    else:
        if model_id == "A-1":
            cd_sub = L["cd_sub_a1"]
        elif model_id == "B":
            cd_sub = L["cd_sub_b"]
        else:
            cd_sub = L["cd_sub_c"]
        render_card(k3, L["card_cd"],
                    f"{base_res['cd_ode']:.3f}",
                    cd_sub, "#16a34a")
    if model_id.startswith("A"):
        render_card(k4, L["card_omeff"],
                    f"({o_val[0]:.3f}±{o_se[0]:.2f}, {o_val[1]:.3f}±{o_se[1]:.2f})",
                    L["card_omeff_sub"], "#d97706")
    else:
        render_card(k4, L["card_omega"],
                    f"({o_val[0]:.2f}±{o_se[0]:.1f}, {o_val[1]:.2f}±{o_se[1]:.1f})",
                    L["card_omega_sub"], "#d97706")
    render_card(k5, L["card_svd"],
                f"κ = {inv['cond']:.1e}",
                L["card_svd_sub"].format(n=len(inv["sv"]), m=inv["n_starts"]), "#7c3aed")
    render_card(k6, L["card_prob"],
                L["card_prob_v"].format(v=f"{probs['P_in_given_reach']:.1%}"),
                L["card_prob_sub"].format(a=f"{probs['P_reach']:.1%}", b=f"{probs['P_ground']:.1%}"),
                "#e11d48")

    st.write("")

    # ==================== 6. 主视图 ====================
    col_left, col_right = st.columns([1.42, 1.0])
    with col_left:
        fig_3d = PenaltyVisualizer3D.build_3d_stadium_figure(
            base_res, mc_cloud_curr, frame_idx, t1, t2, r1, r2, show_cloud=show_cloud, lang=lang)
        st.plotly_chart(fig_3d, width="stretch")
    with col_right:
        fig_2d = PenaltyVisualizer3D.build_2d_goal_heatmap(
            mc_data, base_res, show_legend=show_legend_2d, lang=lang)
        st.plotly_chart(fig_2d, width="stretch")

    if base_res["near_tangent"]:
        st.warning(L["warn_tangent"])

    # ==================== 7. 数据诊断基线（论文 §2） ====================
    with st.expander(L["exp_base"]):
        bs = base_res["baselines"]
        v01, v12, v23 = bs["interval"]
        gb = bs["gravity"]
        rows_name = [L["row_iv01"], L["row_iv12"]]
        rows_v0 = [f"({v01[0]:.2f}, {v01[1]:.2f}, {v01[2]:.2f})",
                   f"({v12[0]:.2f}, {v12[1]:.2f}, {v12[2]:.2f})"]
        rows_tg = [f"{(SimConfig.GOAL_X - SimConfig.R0[0]) / v01[0]:.4f}",
                   f"{(SimConfig.GOAL_X - SimConfig.R0[0]) / v12[0]:.4f}"]
        rows_pg = ["—", "—"]
        if v23 is not None:
            rows_name.append(L["row_iv23"])
            rows_v0.append(f"({v23[0]:.2f}, {v23[1]:.2f}, {v23[2]:.2f})")
            rows_tg.append(f"{(SimConfig.GOAL_X - SimConfig.R0[0]) / v23[0]:.4f}")
            rows_pg.append("—")
        rows_name += [L["row_ca"], L["row_g1"], L["row_gls"]]
        rows_v0 += [
            f"({base_res['v0_ca'][0]:.2f}, {base_res['v0_ca'][1]:.2f}, {base_res['v0_ca'][2]:.2f})",
            f"({gb['v0_r1'][0]:.2f}, {gb['v0_r1'][1]:.2f}, {gb['v0_r1'][2]:.2f})",
            f"({gb['v0_ls'][0]:.2f}, {gb['v0_ls'][1]:.2f}, {gb['v0_ls'][2]:.2f})"]
        rows_tg += [f"{base_res['t_goal_ca']:.4f}", f"{gb['t_g_r1']:.4f}", f"{gb['t_g_ls']:.4f}"]
        rows_pg += [
            f"({base_res['pos_ca'][1, -1]:.4f}, {base_res['pos_ca'][2, -1]:.4f})",
            f"({gb['p_g_r1'][1]:.4f}, {gb['p_g_r1'][2]:.4f})",
            f"({gb['p_g_ls'][1]:.4f}, {gb['p_g_ls'][2]:.4f})"]

        render_html_table(
            [L["th_method"], L["th_v0"], L["th_tg"], L["th_impact"]],
            [[n, v, tg, pg] for n, v, tg, pg in zip(rows_name, rows_v0, rows_tg, rows_pg)],
            min_width="680px")
        st.caption(L["cap_base"])

    # ==================== 8. 事件标签统计与分位数 ====================
    with st.expander(L["exp_events"]):
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown(f"**{L['ev_title']}**")
            render_html_table(
                [L["th_event"], L["th_count"], L["th_prob"]],
                [
                    [L["ev_total"], probs["n_total"], "1.000"],
                    [L["ev_reach"], probs["n_reach"], f"{probs['P_reach']:.3f}"],
                    [L["ev_in_full"], probs["n_in_full"], f"{probs['P_in_and_reach']:.3f}"],
                    [L["ev_in_center"], probs["n_in_center"], f"{probs['n_in_center'] / probs['n_total']:.3f}"],
                    [L["ev_ground"], probs["n_ground"], f"{probs['P_ground']:.3f}"],
                    [L["ev_timeout"], probs["n_timeout"], f"{probs['P_timeout']:.3f}"],
                    [L["ev_near"], int(probs["P_near_tangent"] * probs["n_total"]),
                     f"{probs['P_near_tangent']:.3f}"],
                ], min_width="460px")
        with t_col2:
            st.markdown(f"**{L['qt_title']}**")
            render_html_table(
                [L["th_var"], L["th_q025"], L["th_q25"], L["th_med"], L["th_q75"], L["th_q975"]],
                [
                    [L["qt_y"], f"{stats['y']['q025']:.4f}", f"{stats['y']['q25']:.4f}",
                     f"{stats['y']['median']:.4f}", f"{stats['y']['q75']:.4f}", f"{stats['y']['q975']:.4f}"],
                    [L["qt_z"], f"{stats['z']['q025']:.4f}", f"{stats['z']['q25']:.4f}",
                     f"{stats['z']['median']:.4f}", f"{stats['z']['q75']:.4f}", f"{stats['z']['q975']:.4f}"],
                    [L["qt_t"], f"{stats['t_g']['q025']:.4f}", f"{stats['t_g']['q25']:.4f}",
                     f"{stats['t_g']['median']:.4f}", f"{stats['t_g']['q75']:.4f}", f"{stats['t_g']['q975']:.4f}"],
                ], min_width="640px")
            st.caption(L["cap_quant"])

    # ==================== 9. 模型包络与方差分解（论文 §6.1） ====================
    with st.expander(L["exp_env"]):
        do_env = st.checkbox(L["env_check"], value=False)
        if do_env:
            env_models = ["A-1", "A-2", "B"]
            if bridge.data_loaded:
                env_models.append("C")
            with st.spinner(L["env_spinner"]):
                rows, decomp = cached_envelope(
                    t1, t2, float(x1), float(y1), float(z1), float(x2), float(y2), float(z2),
                    sigma_obs, float(wx), float(wy), float(wz), sigma_r, n_samples, err_model,
                    tuple(env_models))
            render_html_table(
                [L["th_model"], L["th_ey"], L["th_sy"], L["th_ez"], L["th_sz"],
                 L["th_tg_med"], L["th_preach"], L["th_pin"], L["th_event"]],
                [[
                    r["model"],
                    f"{r['mean_y']:.4f}", f"{r['std_y']:.4f}",
                    f"{r['mean_z']:.4f}", f"{r['std_z']:.4f}",
                    f"{r['t_g_median']:.4f}",
                    f"{r['P_reach']:.3f}", f"{r['P_in_given_reach']:.3f}",
                    L.get("event_" + r["status"], r["status"]),
                ] for r in rows], min_width="900px")
            st.markdown(L["env_md"].format(
                ey=decomp['E_var_y'], vy=decomp['var_E_y'], fy=decomp['fraction_between_y'],
                ez=decomp['E_var_z'], vz=decomp['var_E_z'], fz=decomp['fraction_between_z']))
            st.caption(L["cap_env"])

    # ==================== 10. COMSOL 实测数据对照（论文 §7） ====================
    @st.cache_data(show_spinner=False)
    def _comsol_handoff():
        return comsol_lab.analyze()

    with st.expander(L["exp_comsol"]):
        try:
            hf = _comsol_handoff()
        except Exception as e:
            st.warning(L["comsol_fail"].format(e=e))
        else:
            cond = hf["conditions"]
            st.caption(L["comsol_cond"].format(u=cond['U'], re=cond['Re'], s=cond['S'],
                                               om=cond['omega'], q=cond['q_ref']),
                       unsafe_allow_html=True)

            P0 = hf["plateau"]["zero"]
            Pp = hf["plateau"]["pos"]
            Pn = hf["plateau"]["neg"]
            h1, h2, h3, h4 = st.columns(4)
            render_card(h1, L["co_cd0"], f"{P0['C'][0]:.3f}",
                        L["co_fx"].format(v=f"{P0['F'][0]:.2f}"), "#0d9488")
            render_card(h2, L["co_clp"], f"{Pp['C'][1]:+.3f}",
                        L["co_fy"].format(v=f"{Pp['F'][1]:+.2f}"), "#dc2626")
            render_card(h3, L["co_cln"], f"{Pn['C'][1]:+.3f}",
                        L["co_fy"].format(v=f"{Pn['F'][1]:+.2f}"), "#2563eb")
            render_card(h4, L["co_pfrac"], f"{hf['pressure_frac']['fy']:.0%}",
                        L["co_axial"].format(v=f"{hf['pressure_frac']['fx']:.0%}"), "#7c3aed")
            st.write("")

            st.plotly_chart(comsol_lab.build_force_timeseries_fig(hf, lang=lang), width="stretch")
            st.plotly_chart(comsol_lab.build_mesh_sensitivity_fig(hf, lang=lang), width="stretch")

            # ---- 与当前反演结果的自动对照（论文 §7 讨论点） ----
            st.markdown(f"**{L['cmp_title']}**")
            cmp_rows = []
            if model_id == "A-2":
                cd_dev = abs(base_res["cd_ode"] - P0["C"][0]) / max(P0["C"][0], 1e-9)
                cmp_rows.append((
                    L["cmp_cd"],
                    L["cmp_cd_val"].format(a=f"{base_res['cd_ode']:.3f}", b=f"{P0['C'][0]:.3f}"),
                    L["cmp_cd_why"] if cd_dev > 0.3 else L["cmp_cd_ok"]))
            if model_id.startswith("A"):
                om_est = max(abs(o_val[0]), abs(o_val[1]))
                cmp_rows.append((
                    L["cmp_om"],
                    L["cmp_om_val"].format(a=om_est,
                                            b=hf['omega_equiv']['plateau_neg'],
                                            c=hf['omega_equiv']['last_neg']),
                    L["cmp_om_why"]))
            if cmp_rows:
                render_html_table([L["th_item"], L["th_value"], L["th_read"]],
                                  [list(r) for r in cmp_rows], min_width="760px")

            if hf["reverse_magnus"]:
                st.warning(L["warn_reverse"])

            # ---- 英文图注 ----
            st.markdown(f"**{L['cap_title']}**")
            caps = comsol_lab.captions_en(hf)
            st.code(
                f"Fig. A1 — {caps['mesh']}\n\n"
                f"Fig. A2 — {caps['forces']}\n\n"
                f"Fig. A3 — {caps['pressure']}",
                language=None)


if __name__ == "__main__":
    main()
