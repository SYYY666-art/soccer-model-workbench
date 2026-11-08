# -*- coding: utf-8 -*-
"""实验台界面中英双语文本（学术风格）。

用法：
    lang = st.session_state.get("lang", "zh")
    L = TEXT[lang]
    st.header(L["sec1_obs"])
支持 {} 占位符的字符串用 L["key"].format(...)。
HTML 下标（<sub>）只在 unsafe_allow_html=True 的组件中使用。
"""

ZH = {
    # ---- 语言按钮与标题 ----
    "btn_lang": "English",
    "app_title": "UPC 2026 Problem B · Team 991 · 点球轨迹预测实验台",
    # ---- 侧边栏 1：观测数据 ----
    "sec1_obs": "1. 观测数据",
    "preset_label": "经典算例（选择后自动填入，可再手动修改）",
    "t1_label": "观测时刻 t₁ (s)",
    "t2_label": "观测时刻 t₂ (s)",
    "pos_t1_md": "**$t_1$ 时刻球心坐标 $(x_1, y_1, z_1)$ (m)**",
    "pos_t2_md": "**$t_2$ 时刻球心坐标 $(x_2, y_2, z_2)$ (m)**",
    "pos_t3_md": "**$t_3$ 时刻球心坐标 $(x_3, y_3, z_3)$ (m)**",
    "t3_label": "观测时刻 t₃ (s)",
    "use_t3": "启用第三观测帧 t₃（信息量增加，置信区域收窄）",
    "use_t3_help": "两帧观测的误差在过门线时刻约被放大 60~80 倍；"
                   "增加第三帧经最小二乘约束可显著抑制该放大",
    # ---- 侧边栏 2：误差模型 ----
    "sec2_err": "2. 误差模型与样本预算",
    "err_label": "观测误差模型",
    "err_gauss": "独立高斯 σᵣ",
    "err_uniform": "独立均匀舍入 ±0.005 m",
    "err_help": "坐标保留两位小数并不自动意味着 ±0.005 m 均匀分布",
    "sigma_label": "观测位置标准差 σᵣ (m)",
    "sigma_equiv": "等效标准差 σ ≈ {v} m",
    "n_samples": "蒙特卡洛样本数（平台预览）",
    # ---- 侧边栏 3：管线 ----
    "sec3_pipe": "3. 气动模型管线",
    "pipe_label": "选择 A/B/C 管线",
    "pipe_help": "A-1：固定 C_D 反演 v₀ + 2 横向有效旋转；A-2：六参数候选（需 SVD 诊断）；"
                 "B：文献气动曲线；C：COMSOL 系数图谱",
    "pipe_intro": "**模型管线说明**（三条气动闭合共享同一状态接口与观测似然，仅闭合关系不同，"
                  "以保证模型间比较公平）\n\n"
                  "- **A-1**：阻力系数 $C_D$ 固定为 0.25；反演初速度 $v_0$ 与两个横向有效旋转分量 "
                  "$\\Omega_{\\rm eff}$（共 5 参数），构成稳健基准模型。\n"
                  "- **A-2**：$\\log C_D$ 在对数正态先验下联合反演（共 6 参数）；由 SVD 条件数 $\\kappa$ "
                  "给出可辨识性诊断，区分“可拟合”与“可辨识”。\n"
                  "- **B**：阻力与升力系数由文献曲线给定（Asai 2007；Goff & Carré 2009/2010）；"
                  "反演初速度与横向真实自旋 $\\omega_\\perp$。\n"
                  "- **C**：阻力与升力系数由 COMSOL 风洞实测锚点表给定；"
                  "反演初速度与横向真实自旋 $\\omega_\\perp$。",
    "ack_title": "鸣谢（参考文献）",
    "ack_body": "B 管线的气动系数曲线基于以下文献工作，谨致谢意：\n\n"
                "- Asai, Seo, Kobayashi & Sakashita, *Fundamental aerodynamics of the soccer ball*, "
                "Sports Engineering **10**, 101–110 (2007).\n"
                "- Goff & Carré, *Trajectory analysis of a soccer ball*, American Journal of Physics "
                "**77**, 1020–1027 (2009).\n"
                "- Goff & Carré, *Soccer ball lift coefficients via trajectory analysis*, European "
                "Journal of Physics **31**, 775–784 (2010).\n"
                "- Ward et al., *The effect of surface geometry on the aerodynamic behaviour of a "
                "football*, Sports Engineering **26**, 33 (2023).\n\n"
                "其余引用：\n\n"
                "- Asai & Seo, *Aerodynamic drag of modern soccer balls*, SpringerPlus **2**, 171 (2013).\n"
                "- Mizota et al., *The strange flight behaviour of slowly spinning soccer balls*, "
                "Scientific Reports **3**, 1871 (2013).\n"
                "- Darbois Texier et al., *Physics of knuckleballs*, New Journal of Physics **18**, "
                "073027 (2016).\n"
                "- Dupeux et al., *Football curves*, Journal of Fluids and Structures **27**, 659–667 "
                "(2011).\n"
                "- Grad, *Physics-based 3D ball trajectory reconstruction from monocular soccer video: "
                "A multi-model benchmark*, CVPR Workshops (2026).",
    "cap_a1": "A-1：阻力系数固定 C<sub>D</sub> = 0.25，反演初速度与两个横向有效旋转分量（5 参数）",
    "cap_a2": "A-2：六参数候选模型（初速度、log C<sub>D</sub>、横向 Ω<sub>eff</sub>），"
              "需经 SVD 条件数诊断参数可辨识性",
    "cap_b": "B：文献气动系数曲线（Asai 2007 风洞拟合 + Goff & Carré 2009/2010 轨迹分析）",
    "cap_c_ok": "C：COMSOL 锚点系数表已自动加载（grid_version = {v}，由交接数据平台期平均自动生成），"
                "覆盖 Re ∈ [4.2×10⁵, 4.7×10⁵]、|S| ≤ 0.175；越界查询按边界值处理并标记外推。",
    "cap_c_fail": "C：COMSOL 锚点表生成失败，请检查交接数据目录是否完整。",
    "params_title": "该管线的关键计算参数",
    "params_hint": "通用物理常数与数值规范见下方折叠区。",
    "common_title": "通用物理常数与数值规范",
    "p_param": "参数",
    "p_value": "取值",
    "pc_rho": "空气密度 ρ (kg/m³)",
    "pc_mu": "空气动力黏度 μ (Pa·s)",
    "pc_g": "重力加速度 g (m/s²)",
    "pc_m": "球质量 m (kg)",
    "pc_r": "球半径 R (m)",
    "pc_re": "雷诺数定义 Re",
    "pc_s": "旋转比定义 S",
    "pc_ode": "数值积分规范",
    "pc_fric": "表面摩擦",
    "pc_rho_v": "1.225",
    "pc_mu_v": "1.81×10⁻⁵",
    "pc_g_v": "9.81",
    "pc_m_v": "0.43",
    "pc_r_v": "0.11（直径 D = 0.22）",
    "pc_re_v": "ρ|u|D / μ",
    "pc_s_v": "ωR / |u|",
    "pc_ode_v": "DOP853；rtol = 1×10⁻⁸，atol = 1×10⁻⁹，h<sub>max</sub> = 0.01 s",
    "pc_fric_v": "飞行段球体不触地，不引入滚动/表面摩擦系数；黏性贡献已含于气动力系数",
    "ps_cd": "阻力系数 C<sub>D</sub>",
    "ps_params": "反演参数",
    "ps_diag": "可辨识性诊断",
    "ps_closure": "气动闭合",
    "ps_source": "系数来源",
    "ps_omega_sigma": "Ω<sub>eff</sub> 先验 σ (s⁻¹)",
    "ps_omega_sigma_b": "ω⊥ 先验 σ (rad/s)",
    "ps_domain": "覆盖域",
    "ps_ref": "参考值",
    "ps_status": "当前状态",
    "ps_a1_cd_v": "外部固定 = 0.25（先验中心）",
    "ps_a1_par_v": "初速度 v₀ (3) + 横向有效旋转 Ω<sub>eff</sub> (2)，共 5 维",
    "ps_a1_sig_v": "3.0",
    "ps_a1_clo_v": "a<sub>drag</sub> = −(ρA C<sub>D</sub>/2m)|u|u；a<sub>lift</sub> = Ω<sub>eff</sub>×u",
    "ps_a2_cd_v": "对数正态先验 ln C<sub>D</sub> ~ N(ln 0.25, 0.6)",
    "ps_a2_par_v": "初速度 v₀ (3) + log C<sub>D</sub> + 横向 Ω<sub>eff</sub> (2)，共 6 维",
    "ps_a2_diag_v": "SVD 条件数 κ、参数标准误 SE",
    "ps_a2_clo_v": "同 A-1（常系数阻力 + 有效旋转项）",
    "ps_b_src_v": "Asai 2007 风洞数据拟合（Goff & Carré 2010）；临界转捩 Re_c ≈ 1.73×10⁵",
    "ps_b_par_v": "初速度 v₀ (3) + 横向真实自旋 ω⊥ (2)，共 5 维",
    "ps_b_sig_v": "40.0",
    "ps_b_sta_v": "文献曲线已替换；Sp > 0.3 的 C_D 为文献外推，Sp > 1 无实验数据",
    "ps_c_src_v": "COMSOL 锚点系数表（grid_version = {v}）",
    "ps_c_par_v": "初速度 v₀ (3) + 横向真实自旋 ω⊥ (2)，共 5 维",
    "ps_c_dom_v": "Re ∈ [4.2×10⁵, 4.7×10⁵]，|S| ≤ 0.175",
    "ps_c_ref_v": "C<sub>D</sub> = 0.126（零转平台期平均）",
    # ---- 侧边栏 4：风场 ----
    "sec4_wind": "4. 风场与自旋设定",
    "wind_x": "风速 x 分量 (m/s)",
    "wind_y": "风速 y 分量 (m/s)",
    "wind_z": "风速 z 分量 (m/s)",
    "lam_label": "自旋轴向分量 ω∥ (rad/s)（诊断/敏感性）",
    "lam_help": "平行于速度的自旋分量对经典 Magnus 力无直接贡献；此处仅作诊断/敏感性量，"
                "不得解释为已被观测识别的真实角速度",
    "cloud_check": "显示可能位置云团",
    "cloud_help": "关闭后 3D 球场中的速度/升力/加速度矢量箭头更清晰",
    "legend_check": "显示球门平面图图例",
    "legend_help": "图例条目较多，默认隐藏避免遮挡标题；需要时勾选显示",
    # ---- 校验与错误 ----
    "err_t12": "观测时刻须满足 0 < t₁ < t₂，请调整左侧边栏中 t₁ 与 t₂ 的取值。",
    "err_t123": "观测时刻须满足 0 < t₁ < t₂ < t₃，请调整左侧边栏中 t₃ 的取值。",
    "inv_fail": "参数反演失败：{e}",
    # ---- 时间轴 ----
    "jump_cap": "快捷跳转时刻",
    "jump_goal": "过线时刻",
    "slider_label": "轨迹时间轴：拖动查看任意时刻的球体位置、速度/加速度/升力矢量与可能位置云团",
    # ---- 指标卡片 ----
    "event_goal": "首次过门线",
    "event_ground": "触地终止",
    "event_timeout": "超时未达",
    "card_event": "过门线事件",
    "card_tg_sub": "过门线时刻 t<sub>g</sub> = {v} s",
    "card_v0": "反演初速度 v₀",
    "card_rms": "位置残差 RMS = {v} m",
    "card_cd_log": "阻力系数 C<sub>D</sub>（log 参数化）",
    "card_cd": "阻力系数 C<sub>D</sub>",
    "card_cd_prior": "先验中心 0.25 · 管线 {m}",
    "cd_sub_a1": "外部固定值 · 管线 A-1",
    "cd_sub_b": "文献曲线给定 · 管线 B",
    "cd_sub_c": "COMSOL 锚点图谱 · 管线 C",
    "card_omeff": "有效旋转 Ω<sub>eff</sub> (s⁻¹)",
    "card_omeff_sub": "低阶有效参数，非真实自旋",
    "card_omega": "横向自旋 ω⊥ (rad/s)",
    "card_omega_sub": "曲线固定后弱可辨识，见 κ 诊断",
    "card_svd": "可辨识性诊断 (SVD)",
    "card_svd_sub": "奇异值数: {n} · 多起点: {m}",
    "card_prob": "概率预测",
    "card_prob_v": "进球|过线 {v}",
    "card_prob_sub": "P(过线) = {a}，P(触地) = {b}",
    # ---- 主区说明 ----
    "cap_ellipse": "95% 置信区域尺度较大的原因：两帧观测间隔仅约 0.05 s，观测误差在过门线时刻被放大约 60~80 倍。"
                   "提高精度的途径：① 选择更精确的误差模型（如均匀舍入 ±0.005 m，或调小 σᵣ）；"
                   "② 在左侧启用第三观测帧 t₃（信息量增加，置信区域显著收窄）。",
    "warn_tangent": "$|v_x(t_g)|$ 低于阈值：该轨迹接近切触球门平面，一阶灵敏度线性传播可能失效。",
    # ---- 第 7 部分：基线 ----
    "exp_base": "数据诊断基线（区间平均速度、三点恒加速度、重力基线）",
    "th_method": "基线方法",
    "th_v0": "v₀ (m/s)",
    "th_tg": "t<sub>g</sub> (s)",
    "th_impact": "落点 (y, z) (m)",
    "row_iv01": "区间平均速度，t∈[0, t₁]",
    "row_iv12": "区间平均速度，t∈[t₁, t₂]",
    "row_iv23": "区间平均速度，t∈[t₂, t₃]",
    "row_ca": "三点恒加速度插值（最小二乘）",
    "row_g1": "重力基线（仅用 r₁）",
    "row_gls": "重力基线（全部观测最小二乘）",
    "cap_base": "区间平均速度不同说明恒速模型不足以解释观测；三点恒加速度严格穿过全部观测点，"
                "是运动学基线而非空气动力学真值。",
    # ---- 第 8 部分：事件统计 ----
    "exp_events": "事件标签统计与蒙特卡洛分位数",
    "ev_title": "事件标签统计（保留全部样本）",
    "th_event": "事件",
    "th_count": "数量",
    "th_prob": "概率",
    "ev_total": "总样本",
    "ev_reach": "首次过门线",
    "ev_in_full": "整球净空（进球）",
    "ev_in_center": "球心判据（进球）",
    "ev_ground": "触地终止",
    "ev_timeout": "超时未达",
    "ev_near": "近切触（线性失效警示）",
    "qt_title": "落点与过线时刻分位数（过线样本）",
    "th_var": "变量",
    "th_q025": "2.5%",
    "th_q25": "25%",
    "th_med": "中位数",
    "th_q75": "75%",
    "th_q975": "97.5%",
    "qt_y": "水平落点 Y<sub>g</sub> (m)",
    "qt_z": "竖直落点 Z<sub>g</sub> (m)",
    "qt_t": "过线时刻 t<sub>g</sub> (s)",
    "cap_quant": "均值、中位数与密度众数见球门平面图；二维分布偏斜或多峰时 95% 高斯椭圆仅作参考，"
                 "应以 HDR 等高线为准。",
    # ---- 第 9 部分：包络 ----
    "exp_env": "A/B/C 模型包络对比与方差分解",
    "env_check": "运行模型包络计算（A-1 / A-2 / B / C，约需数秒）",
    "env_spinner": "多模型反演与概率传播计算中……",
    "th_model": "模型",
    "th_ey": "E[Y<sub>g</sub>] (m)",
    "th_sy": "Std[Y<sub>g</sub>] (m)",
    "th_ez": "E[Z<sub>g</sub>] (m)",
    "th_sz": "Std[Z<sub>g</sub>] (m)",
    "th_tg_med": "t<sub>g</sub> 中位数 (s)",
    "th_preach": "P(过线)",
    "th_pin": "P(进球|过线)",
    "th_event": "事件",
    "env_md": "**方差分解** $\\mathrm{{Var}}(P_g|D) = E_M[\\mathrm{{Var}}] + \\mathrm{{Var}}_M[E]$（逐轴）：\n"
             "- Y 轴：$E[\\mathrm{{Var}}]={ey:.5f}$ m²，$\\mathrm{{Var}}[E]={vy:.5f}$ m²，\n"
             "  模型间方差占比 {fy:.1%}\n"
             "- Z 轴：$E[\\mathrm{{Var}}]={ez:.5f}$ m²，$\\mathrm{{Var}}[E]={vz:.5f}$ m²，\n"
             "  模型间方差占比 {fz:.1%}\n\n"
             "若模型权重无独立数据校准，应分别报告条件分布或模型集合包络，\n"
             "不可主观指定权重并称其为概率。",
    "cap_env": "注：B 管线采用文献曲线（Asai 2007; Goff & Carré 2009/2010），Sp>0.3 区为文献外推；"
               "包络结果仅用于模型间比较。",
    # ---- 第 10 部分：COMSOL ----
    "exp_comsol": "COMSOL 实测数据对照（光滑球风洞）",
    "comsol_fail": "交接数据解析失败：{e}（请确认交接数据目录完整）",
    "comsol_cond": "风洞工况（05 全局参数）：U∞ = {u} m/s，Re ≈ {re:.2e}，"
                   "旋转比 S = ±{s:.3f}（ω<sub>z</sub> = ±{om} rad/s），光滑球、标准 k–ε 湍流模型，"
                   "气动力归一化分母 ½ρU²A = {q:.3f} N。平台期取 0.024–0.040 s（自旋平台之后）。",
    "co_cd0": "C<sub>D</sub>（零转平台期平均）",
    "co_clp": "C<sub>L</sub>（正转 ω<sub>z</sub> = +50）",
    "co_cln": "C<sub>L</sub>（反转 ω<sub>z</sub> = −50）",
    "co_pfrac": "侧向力压力贡献占比",
    "co_fx": "F<sub>x</sub> = {v} N",
    "co_fy": "F<sub>y</sub> = {v} N",
    "co_axial": "轴向 {v}（零转）",
    "cmp_title": "与本次反演结果的自动对照",
    "th_item": "对照项",
    "th_value": "数值",
    "th_read": "解读",
    "cmp_cd": "反演 C<sub>D</sub> 对比",
    "cmp_cd_val": "本次 {a} vs COMSOL 光滑球 {b}",
    "cmp_cd_why": "差异解释：真实足球的拼缝与面板粗糙度使超临界 C<sub>D</sub> 高于光滑球，"
                  "且反演参数会吸收部分建模误差与观测误差。",
    "cmp_cd_ok": "反演 C<sub>D</sub> 与 COMSOL 光滑球平台值量级一致。",
    "cmp_om": "有效旋转量级对比",
    "cmp_om_val": "本次 |Ω<sub>eff</sub>| = {a:.3f} s⁻¹ vs COMSOL 等效 ≈ {b:.3f} s⁻¹（平台均值）"
                  "/ {c:.3f} s⁻¹（末帧瞬时）",
    "cmp_om_why": "量级可比；但 COMSOL 实测为反向 Magnus（见下方警示），"
                  "低阶 Ω<sub>eff</sub>×u 项方向固定为经典方向，无法表征该效应。",
    "warn_reverse": "反向 Magnus 判据成立：正转（$\\omega_z = +50$ rad/s，经典方向为 +y）实测 $\\Delta F_y < 0$，"
                    "反转实测 $\\Delta F_y > 0$，均与经典 $\\omega \\times u$ 方向相反，可能与临界雷诺数附近"
                    "边界层转捩不对称有关。论文应在模型边界一节讨论：A 管线的 $\\Omega_{\\mathrm{eff}} \\times u$ 项"
                    "固定为经典方向，无法表征反向 Magnus，其反演结果只应解释为低阶有效参数。",
    "cap_title": "英文图注（供论文直接引用）",
}

EN = {
    "btn_lang": "中文",
    "app_title": "UPC 2026 Problem B · Team 991 · Penalty-Trajectory Prediction Workbench",
    "sec1_obs": "1. Observation Data",
    "preset_label": "Benchmark cases (auto-filled; editable)",
    "t1_label": "Observation time t₁ (s)",
    "t2_label": "Observation time t₂ (s)",
    "pos_t1_md": "**Ball center at $t_1$: $(x_1, y_1, z_1)$ (m)**",
    "pos_t2_md": "**Ball center at $t_2$: $(x_2, y_2, z_2)$ (m)**",
    "pos_t3_md": "**Ball center at $t_3$: $(x_3, y_3, z_3)$ (m)**",
    "t3_label": "Observation time t₃ (s)",
    "use_t3": "Enable third observation t₃ (more information, tighter confidence region)",
    "use_t3_help": "Errors from two frames are amplified by a factor of 60–80 at the goal plane; "
                   "a third frame constrains the least-squares fit and strongly suppresses this amplification",
    "sec2_err": "2. Error Model and Sample Budget",
    "err_label": "Observation error model",
    "err_gauss": "Independent Gaussian σᵣ",
    "err_uniform": "Independent uniform rounding ±0.005 m",
    "err_help": "Two-decimal coordinates do not automatically imply a ±0.005 m uniform distribution",
    "sigma_label": "Position standard deviation σᵣ (m)",
    "sigma_equiv": "Equivalent σ ≈ {v} m",
    "n_samples": "Monte Carlo sample size (preview)",
    "sec3_pipe": "3. Aerodynamic Model Pipelines",
    "pipe_label": "Select pipeline A/B/C",
    "pipe_help": "A-1: fixed C_D, invert v₀ + 2 transverse effective spins; A-2: six-parameter candidate "
                 "(requires SVD diagnostics); B: literature aerodynamic curves; C: COMSOL coefficient map",
    "pipe_intro": "**Model pipelines** (the three aerodynamic closures share one state interface and "
                  "observation likelihood; only the closure relation differs, ensuring a fair "
                  "inter-model comparison)\n\n"
                  "- **A-1**: drag coefficient $C_D$ fixed at 0.25; initial velocity $v_0$ and two "
                  "transverse effective-spin components $\\Omega_{\\rm eff}$ inverted (5 parameters) — "
                  "a robust baseline model.\n"
                  "- **A-2**: $\\log C_D$ jointly inverted under a lognormal prior (6 parameters); the SVD "
                  "condition number $\\kappa$ diagnoses identifiability, distinguishing “fittable” from "
                  "“identifiable”.\n"
                  "- **B**: drag and lift coefficients given by literature curves (Asai 2007; "
                  "Goff & Carré 2009/2010); initial velocity and transverse physical spin "
                  "$\\omega_\\perp$ inverted.\n"
                  "- **C**: drag and lift coefficients given by the COMSOL wind-tunnel anchor table; "
                  "initial velocity and transverse physical spin $\\omega_\\perp$ inverted.",
    "ack_title": "Acknowledgments (References)",
    "ack_body": "The aerodynamic coefficient curves of pipeline B are based on the following works, "
                "with gratitude:\n\n"
                "- Asai, Seo, Kobayashi & Sakashita, *Fundamental aerodynamics of the soccer ball*, "
                "Sports Engineering **10**, 101–110 (2007).\n"
                "- Goff & Carré, *Trajectory analysis of a soccer ball*, American Journal of Physics "
                "**77**, 1020–1027 (2009).\n"
                "- Goff & Carré, *Soccer ball lift coefficients via trajectory analysis*, European "
                "Journal of Physics **31**, 775–784 (2010).\n"
                "- Ward et al., *The effect of surface geometry on the aerodynamic behaviour of a "
                "football*, Sports Engineering **26**, 33 (2023).\n\n"
                "Additional references:\n\n"
                "- Asai & Seo, *Aerodynamic drag of modern soccer balls*, SpringerPlus **2**, 171 (2013).\n"
                "- Mizota et al., *The strange flight behaviour of slowly spinning soccer balls*, "
                "Scientific Reports **3**, 1871 (2013).\n"
                "- Darbois Texier et al., *Physics of knuckleballs*, New Journal of Physics **18**, "
                "073027 (2016).\n"
                "- Dupeux et al., *Football curves*, Journal of Fluids and Structures **27**, 659–667 "
                "(2011).\n"
                "- Grad, *Physics-based 3D ball trajectory reconstruction from monocular soccer video: "
                "A multi-model benchmark*, CVPR Workshops (2026).",
    "cap_a1": "A-1: drag coefficient fixed at C<sub>D</sub> = 0.25; inverts initial velocity and two "
              "transverse effective-spin components (5 parameters)",
    "cap_a2": "A-2: six-parameter candidate (initial velocity, log C<sub>D</sub>, transverse Ω<sub>eff</sub>); "
              "identifiability must be diagnosed via the SVD condition number",
    "cap_b": "B: literature aerodynamic coefficient curves (Asai 2007 wind-tunnel fit; Goff & Carré 2009/2010)",
    "cap_c_ok": "C: COMSOL anchor coefficient table loaded automatically (grid_version = {v}, averaged over the "
                "plateau of the hand-off data); coverage Re ∈ [4.2×10⁵, 4.7×10⁵], |S| ≤ 0.175; "
                "out-of-range queries use boundary values and are flagged as extrapolation.",
    "cap_c_fail": "C: failed to generate the COMSOL anchor table; check that the hand-off data directory is complete.",
    "params_title": "Key Parameters of This Pipeline",
    "params_hint": "Common physical constants and numerical specifications are in the collapsible section below.",
    "common_title": "Common Physical Constants and Numerical Specifications",
    "p_param": "Parameter",
    "p_value": "Value",
    "pc_rho": "Air density ρ (kg/m³)",
    "pc_mu": "Dynamic viscosity μ (Pa·s)",
    "pc_g": "Gravitational acceleration g (m/s²)",
    "pc_m": "Ball mass m (kg)",
    "pc_r": "Ball radius R (m)",
    "pc_re": "Reynolds number Re",
    "pc_s": "Spin ratio S",
    "pc_ode": "Numerical integration",
    "pc_fric": "Surface friction",
    "pc_rho_v": "1.225",
    "pc_mu_v": "1.81×10⁻⁵",
    "pc_g_v": "9.81",
    "pc_m_v": "0.43",
    "pc_r_v": "0.11 (diameter D = 0.22)",
    "pc_re_v": "ρ|u|D / μ",
    "pc_s_v": "ωR / |u|",
    "pc_ode_v": "DOP853; rtol = 1×10⁻⁸, atol = 1×10⁻⁹, h<sub>max</sub> = 0.01 s",
    "pc_fric_v": "The ball does not touch the ground in flight, so no rolling/surface friction coefficient "
                 "is introduced; viscous contributions are already contained in the aerodynamic coefficients",
    "ps_cd": "Drag coefficient C<sub>D</sub>",
    "ps_params": "Inverted parameters",
    "ps_diag": "Identifiability diagnostics",
    "ps_closure": "Aerodynamic closure",
    "ps_source": "Coefficient source",
    "ps_omega_sigma": "Ω<sub>eff</sub> prior σ (s⁻¹)",
    "ps_omega_sigma_b": "ω⊥ prior σ (rad/s)",
    "ps_domain": "Coverage",
    "ps_ref": "Reference value",
    "ps_status": "Status",
    "ps_a1_cd_v": "Externally fixed = 0.25 (prior mean)",
    "ps_a1_par_v": "Initial velocity v₀ (3) + transverse Ω<sub>eff</sub> (2); 5 parameters",
    "ps_a1_sig_v": "3.0",
    "ps_a1_clo_v": "a<sub>drag</sub> = −(ρA C<sub>D</sub>/2m)|u|u; a<sub>lift</sub> = Ω<sub>eff</sub>×u",
    "ps_a2_cd_v": "Lognormal prior ln C<sub>D</sub> ~ N(ln 0.25, 0.6)",
    "ps_a2_par_v": "Initial velocity v₀ (3) + log C<sub>D</sub> + transverse Ω<sub>eff</sub> (2); 6 parameters",
    "ps_a2_diag_v": "SVD condition number κ, parameter standard errors",
    "ps_a2_clo_v": "Same as A-1 (constant drag + effective spin term)",
    "ps_b_src_v": "Fit to Asai 2007 wind-tunnel data (Goff & Carré 2010); critical transition Re_c ≈ 1.73×10⁵",
    "ps_b_par_v": "Initial velocity v₀ (3) + transverse physical spin ω⊥ (2); 5 parameters",
    "ps_b_sig_v": "40.0",
    "ps_b_sta_v": "Literature curves in place; C_D for Sp > 0.3 is a literature extrapolation, no data for Sp > 1",
    "ps_c_src_v": "COMSOL anchor coefficient table (grid_version = {v})",
    "ps_c_par_v": "Initial velocity v₀ (3) + transverse physical spin ω⊥ (2); 5 parameters",
    "ps_c_dom_v": "Re ∈ [4.2×10⁵, 4.7×10⁵], |S| ≤ 0.175",
    "ps_c_ref_v": "C<sub>D</sub> = 0.126 (zero-spin plateau mean)",
    "sec4_wind": "4. Wind and Spin Settings",
    "wind_x": "Wind x-component (m/s)",
    "wind_y": "Wind y-component (m/s)",
    "wind_z": "Wind z-component (m/s)",
    "lam_label": "Axial spin component ω∥ (rad/s) (diagnostic)",
    "lam_help": "The spin component parallel to the velocity makes no direct contribution to the classical "
                "Magnus force; it is a diagnostic/sensitivity quantity only and must not be interpreted as "
                "an observationally identified physical spin",
    "cloud_check": "Show possible position cloud",
    "cloud_help": "Disabling makes the velocity/lift/acceleration arrows in the 3-D stadium clearer",
    "legend_check": "Show goal-plane legend",
    "legend_help": "The legend has many entries; hidden by default to avoid covering the title",
    "err_t12": "Observation times must satisfy 0 < t₁ < t₂; adjust t₁ and t₂ in the sidebar.",
    "err_t123": "Observation times must satisfy 0 < t₁ < t₂ < t₃; adjust t₃ in the sidebar.",
    "inv_fail": "Parameter inversion failed: {e}",
    "jump_cap": "Jump to time",
    "jump_goal": "Goal crossing",
    "slider_label": "Time axis: drag to inspect ball position, velocity/acceleration/lift vectors, "
                    "and the possible position cloud",
    "event_goal": "First goal-line crossing",
    "event_ground": "Ground contact",
    "event_timeout": "Timeout",
    "card_event": "Goal-crossing event",
    "card_tg_sub": "Crossing time t<sub>g</sub> = {v} s",
    "card_v0": "Inferred initial velocity v₀",
    "card_rms": "Position residual RMS = {v} m",
    "card_cd_log": "Drag coefficient C<sub>D</sub> (log-parametrized)",
    "card_cd": "Drag coefficient C<sub>D</sub>",
    "card_cd_prior": "Prior mean 0.25 · Pipeline {m}",
    "cd_sub_a1": "Externally fixed · Pipeline A-1",
    "cd_sub_b": "Given by literature curves · Pipeline B",
    "cd_sub_c": "COMSOL anchor map · Pipeline C",
    "card_omeff": "Effective spin Ω<sub>eff</sub> (s⁻¹)",
    "card_omeff_sub": "Low-order effective parameter, not physical spin",
    "card_omega": "Transverse spin ω⊥ (rad/s)",
    "card_omega_sub": "Weakly identifiable with fixed curves; see κ diagnostics",
    "card_svd": "Identifiability diagnostics (SVD)",
    "card_svd_sub": "Singular values: {n} · Multi-starts: {m}",
    "card_prob": "Probabilistic prediction",
    "card_prob_v": "Goal|crossing {v}",
    "card_prob_sub": "P(cross) = {a}, P(ground) = {b}",
    "cap_ellipse": "Why the 95% confidence region is large: the two observations are only ≈ 0.05 s apart, so "
                   "observation errors are amplified by a factor of 60–80 at the goal plane. Ways to improve "
                   "precision: ① use a more accurate error model (e.g., uniform rounding ±0.005 m, or reduce σᵣ); "
                   "② enable the third observation t₃ in the sidebar (more information, much tighter region).",
    "warn_tangent": "$|v_x(t_g)|$ below threshold: the trajectory nearly grazes the goal plane, so first-order "
                    "sensitivity propagation may fail.",
    "exp_base": "Data diagnostics baselines (interval mean velocity, constant acceleration, gravity)",
    "th_method": "Baseline method",
    "th_v0": "v₀ (m/s)",
    "th_tg": "t<sub>g</sub> (s)",
    "th_impact": "Impact point (y, z) (m)",
    "row_iv01": "Interval mean velocity, t∈[0, t₁]",
    "row_iv12": "Interval mean velocity, t∈[t₁, t₂]",
    "row_iv23": "Interval mean velocity, t∈[t₂, t₃]",
    "row_ca": "Three-point constant-acceleration fit (LS)",
    "row_g1": "Gravity baseline (r₁ only)",
    "row_gls": "Gravity baseline (all observations, LS)",
    "cap_base": "Differing interval mean velocities show that a constant-velocity model cannot explain the "
                "observations; the three-point constant-acceleration fit passes through all observation points "
                "and is a kinematic baseline, not an aerodynamic truth.",
    "exp_events": "Event-label statistics and Monte Carlo quantiles",
    "ev_title": "Event-label statistics (all samples kept)",
    "th_event": "Event",
    "th_count": "Count",
    "th_prob": "Probability",
    "ev_total": "Total samples",
    "ev_reach": "First goal-line crossing",
    "ev_in_full": "Full-ball clearance (goal)",
    "ev_in_center": "Center criterion (goal)",
    "ev_ground": "Ground contact",
    "ev_timeout": "Timeout",
    "ev_near": "Near-tangent (linearization warning)",
    "qt_title": "Impact-point and crossing-time quantiles (crossing samples)",
    "th_var": "Variable",
    "th_q025": "2.5%",
    "th_q25": "25%",
    "th_med": "Median",
    "th_q75": "75%",
    "th_q975": "97.5%",
    "qt_y": "Horizontal impact Y<sub>g</sub> (m)",
    "qt_z": "Vertical impact Z<sub>g</sub> (m)",
    "qt_t": "Crossing time t<sub>g</sub> (s)",
    "cap_quant": "Mean, median and density mode are shown in the goal-plane figure; for skewed or multimodal "
                 "2-D distributions the 95% Gaussian ellipse is only a reference and the HDR contour should be "
                 "used.",
    "exp_env": "A/B/C model-envelope comparison and variance decomposition",
    "env_check": "Run model-envelope computation (A-1 / A-2 / B / C, a few seconds)",
    "env_spinner": "Multi-model inversion and uncertainty propagation…",
    "th_model": "Model",
    "th_ey": "E[Y<sub>g</sub>] (m)",
    "th_sy": "Std[Y<sub>g</sub>] (m)",
    "th_ez": "E[Z<sub>g</sub>] (m)",
    "th_sz": "Std[Z<sub>g</sub>] (m)",
    "th_tg_med": "Median t<sub>g</sub> (s)",
    "th_preach": "P(cross)",
    "th_pin": "P(goal|cross)",
    "th_event": "Event",
    "env_md": "**Variance decomposition** $\\mathrm{{Var}}(P_g|D) = E_M[\\mathrm{{Var}}] + \\mathrm{{Var}}_M[E]$ "
             "(per axis):\n"
             "- Y axis: $E[\\mathrm{{Var}}]={ey:.5f}$ m², $\\mathrm{{Var}}[E]={vy:.5f}$ m², "
             "between-model fraction {fy:.1%}\n"
             "- Z axis: $E[\\mathrm{{Var}}]={ez:.5f}$ m², $\\mathrm{{Var}}[E]={vz:.5f}$ m², "
             "between-model fraction {fz:.1%}\n\n"
             "If model weights are not calibrated on independent data, report conditional distributions or the "
             "model ensemble envelope separately; do not assign subjective weights and call the result a "
             "probability.",
    "cap_env": "Note: pipeline B uses literature curves (Asai 2007; Goff & Carré 2009/2010) with a "
               "literature extrapolation for Sp > 0.3; envelope results are for inter-model comparison.",
    "exp_comsol": "COMSOL measured-data comparison (smooth-sphere wind tunnel)",
    "comsol_fail": "Failed to parse hand-off data: {e} (check that the hand-off data directory is complete)",
    "comsol_cond": "Wind-tunnel conditions (global parameters file 05): U∞ = {u} m/s, Re ≈ {re:.2e}, "
                   "spin ratio S = ±{s:.3f} (ω<sub>z</sub> = ±{om} rad/s), smooth sphere, standard k–ε turbulence "
                   "model, force normalization ½ρU²A = {q:.3f} N. Plateau window 0.024–0.040 s "
                   "(after spin ramp-up).",
    "co_cd0": "C<sub>D</sub> (zero-spin plateau mean)",
    "co_clp": "C<sub>L</sub> (positive spin ω<sub>z</sub> = +50)",
    "co_cln": "C<sub>L</sub> (negative spin ω<sub>z</sub> = −50)",
    "co_pfrac": "Pressure share of lateral force",
    "co_fx": "F<sub>x</sub> = {v} N",
    "co_fy": "F<sub>y</sub> = {v} N",
    "co_axial": "axial {v} (zero spin)",
    "cmp_title": "Automatic comparison with the current inversion",
    "th_item": "Item",
    "th_value": "Value",
    "th_read": "Interpretation",
    "cmp_cd": "Inverted C<sub>D</sub> comparison",
    "cmp_cd_val": "current {a} vs COMSOL smooth sphere {b}",
    "cmp_cd_why": "Interpretation: the seams and panel roughness of a real soccer ball raise the supercritical "
                  "C<sub>D</sub> above that of a smooth sphere, and inverted parameters absorb part of the "
                  "modeling and observation error.",
    "cmp_cd_ok": "The inverted C<sub>D</sub> is consistent in magnitude with the COMSOL smooth-sphere plateau value.",
    "cmp_om": "Effective-spin magnitude comparison",
    "cmp_om_val": "current |Ω<sub>eff</sub>| = {a:.3f} s⁻¹ vs COMSOL equivalent ≈ {b:.3f} s⁻¹ (plateau mean)"
                  " / {c:.3f} s⁻¹ (last frame)",
    "cmp_om_why": "Magnitudes are comparable; however, COMSOL measurements show a reverse Magnus effect (warning "
                  "below), and the low-order Ω<sub>eff</sub>×u term is fixed to the classical direction and "
                  "cannot represent that effect.",
    "warn_reverse": "Reverse Magnus criterion satisfied: for positive spin ($\\omega_z = +50$ rad/s, classical "
                    "direction +y) the measured $\\Delta F_y < 0$, and for negative spin $\\Delta F_y > 0$; both are "
                    "opposite to the classical $\\omega \\times u$ direction, possibly due to asymmetric "
                    "boundary-layer transition near the critical Reynolds number. The paper should discuss in the "
                    "model-limitations section that the $\\Omega_{\\mathrm{eff}} \\times u$ term of pipeline A is "
                    "fixed to the classical direction and cannot represent the reverse Magnus effect, so its "
                    "inverted values must be interpreted only as low-order effective parameters.",
    "cap_title": "Figure captions (for direct use in the paper)",
}

TEXT = {"zh": ZH, "en": EN}


def t(lang):
    """返回指定语言的文本字典；未知语言回退中文。"""
    return TEXT.get(lang, ZH)
