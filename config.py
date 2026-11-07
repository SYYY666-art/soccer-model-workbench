import numpy as np

class SimConfig:
    """
    UPC 2026 Problem B 实验平台参数规范
    —— 与《稀疏观测条件下的足球点球三维轨迹预测》进阶理论稿 §3/§5/§7/§8 对齐。

    约定：
    - 所有用户可设定的物理输入与模型反演得到的估计量严格区分；
    - 未被观测数据识别的参数只能以诊断/敏感性量展示，不得显示为确定值。
    """

    # ==================== 1. 场地几何 (m) ====================
    GOAL_X = 11.0                                        # 球门平面 x = 11 m
    GOAL_Y_MIN, GOAL_Y_MAX = -3.66, 3.66                 # 门框宽度开口
    GOAL_Z_MIN, GOAL_Z_MAX = 0.0, 2.44                   # 门框高度开口
    R0 = np.array([0.0, 0.0, 0.11])                      # t=0 球心位置

    # ==================== 2. 足球物理参数 ====================
    # IFAB 规则：比赛用球周长 0.68–0.70 m、质量 0.410–0.450 kg。
    # 半径换算约 0.1082–0.1114 m；0.43 kg / 0.110 m 为演示中值，非题目精确给定。
    MASS = 0.43
    MASS_RANGE = (0.410, 0.450)
    CIRC_RANGE = (0.68, 0.70)
    RADIUS = 0.110
    RADIUS_RANGE = (0.68 / (2.0 * np.pi), 0.70 / (2.0 * np.pi))
    AREA = np.pi * RADIUS ** 2
    DIAMETER = 2.0 * RADIUS
    # 转动惯量：薄球壳 / 实心球两个理想上限，仅用于自旋衰减敏感性说明
    I_SHELL = (2.0 / 3.0) * MASS * RADIUS ** 2
    I_SOLID = (2.0 / 5.0) * MASS * RADIUS ** 2

    # ==================== 3. 空气参数 (SI) ====================
    RHO_AIR = 1.225
    MU_AIR = 1.81e-5
    GRAVITY = np.array([0.0, 0.0, -9.81])
    WIND_DEFAULT = np.array([0.0, 0.0, 0.0])             # 无风是基准情景，不是已知事实

    # ==================== 4. 题目默认观测 ====================
    DEFAULT_T1, DEFAULT_T2 = 0.05, 0.10
    DEFAULT_R1 = np.array([1.50, 0.45, 0.44])
    DEFAULT_R2 = np.array([2.96, 0.86, 0.74])

    # 经典算例库：基准算例 + 五例典型球路（切换后自动填入坐标，仍可手动修改）
    CASE_PRESETS = {
        "基准算例（赛题数据）": {
            "name_en": "Baseline case (problem data)",
            "t1": 0.05, "r1": [1.50, 0.45, 0.44],
            "t2": 0.10, "r2": [2.96, 0.86, 0.74],
            "desc": "赛题给定的两帧观测，用于复现基准分析流程",
            "desc_en": "The two observations given in the problem statement, for reproducing the baseline analysis",
        },
        "左脚大弧线（内旋左偏）": {
            "name_en": "Left-foot in-swinger (left curve)",
            "t1": 0.05, "r1": [1.412, -0.179, 0.403],
            "t2": 0.10, "r2": [2.790, -0.414, 0.673],
            "desc": "内旋球，飞行末段显著向左侧弯曲",
            "desc_en": "In-swinging ball with strong leftward curvature in the late flight phase",
        },
        "电梯球（高抛急坠）": {
            "name_en": "Knuckle-drop (high arc, sharp descent)",
            "t1": 0.05, "r1": [1.576, 0.148, 0.501],
            "t2": 0.10, "r2": [3.108, 0.292, 0.816],
            "desc": "高抛后急剧下坠的落叶球，竖直方向变化剧烈",
            "desc_en": "Knuckle-drop shot: high arc followed by a sharp vertical descent",
        },
        "贴地低平球（左下角）": {
            "name_en": "Low drive (bottom-left corner)",
            "t1": 0.05, "r1": [1.674, -0.419, 0.196],
            "t2": 0.10, "r2": [3.302, -0.826, 0.252],
            "desc": "低平快球，贴地直奔球门左下角",
            "desc_en": "Low, flat and fast shot skimming toward the bottom-left corner",
        },
        "擦门柱极限算例（净空判据）": {
            "name_en": "Post-grazing limit case (clearance criterion)",
            "t1": 0.05, "r1": [1.479, 0.501, 0.398],
            "t2": 0.10, "r2": [2.921, 0.975, 0.662],
            "desc": "落点位于门框内缘，检验整球净空判据的极限情形",
            "desc_en": "Impact point at the inner edge of the frame, testing the limiting case of the full-ball clearance criterion",
        },
        "正脚背爆射（直线上角）": {
            "name_en": "Power drive (top corner)",
            "t1": 0.05, "r1": [1.771, 0.049, 0.391],
            "t2": 0.10, "r2": [3.489, 0.097, 0.646],
            "desc": "高速直球，横向弯曲极小，直指球门上角",
            "desc_en": "High-speed straight drive with negligible lateral curvature toward the top corner",
        },
    }

    # ==================== 5. 观测误差模型 (论文 §5.1) ====================
    # 坐标保留两位小数并不自动意味着 ±0.005 m 均匀分布；
    # 平台区分两种情景：独立均匀舍入、独立高斯，并支持扫描 σ_r。
    ROUNDING_HALFWIDTH = 0.005
    SIGMA_R_DEFAULT = 0.010
    SIGMA_R_SCAN = [0.005, 0.010, 0.020]

    # ==================== 6. 数值求解规范 (论文 §8) ====================
    ODE_RTOL, ODE_ATOL = 1e-8, 1e-10
    ODE_METHOD = "DOP853"
    ODE_MAX_STEP = 0.01                       # 限制最大步长以解析同一步的过门/触地事件
    T_MAX_FLIGHT = 1.5                        # 最大飞行时间，超过判为 timeout 事件
    FD_EPS = 1e-5                             # 中心差分相对步长（灵敏度计算）
    NEAR_TANGENT_VX = 2.0                     # |v_x(t_g)| 低于该值标记近切触轨迹（线性传播失效警示）

    # ==================== 7. 模型 A 气动闭合 (论文 §4.1) ====================
    # A：C_D 常数阻力 + Ω_eff 有效旋转项（不另叠加 C_L，避免重复计算）
    CD_A_PRIOR_MEAN = 0.25                    # NASA 教学基准，仅作先验中心，非实测值
    CD_A_PRIOR_SIGMA_LOG = 0.6                # log C_D 高斯先验标准差
    CD_A_BOUNDS = (0.05, 0.95)
    OMEGA_EFF_PRIOR_SIGMA = 3.0               # Ω_eff 横向分量弱先验 (s⁻¹)
    OMEGA_EFF_BOUNDS = (-8.0, 8.0)

    # ==================== 8. 有效旋转参数化 (论文 §5.2/§5.4) ====================
    # Ω_eff 为低阶有效旋转向量（s⁻¹），约束 Ω_eff·u_ref=0，只反演两个横向分量；
    # 它不是球的真实角速度。轴向分量 ω∥ 不直接贡献经典 Magnus 力，仅作诊断/敏感性量。
    OMEGA_PARALLEL_DEFAULT = 0.0
    OMEGA_PARALLEL_BOUNDS = (-10.0, 10.0)

    # ==================== 9. 蒙特卡洛预算 (论文 §6.2) ====================
    MC_SEED = 20261106
    MC_N_OPTIONS = [300, 600, 1000, 2000]     # 平台交互预览
    MC_N_DEFAULT = 600
    MC_N_PAPER = 50000                        # 论文离线统计建议量级

    # ==================== 10. 概率阈值 ====================
    CHI2_95_2D = 5.991                         # 二维高斯 95% 联合椭圆阈值 χ²₂(0.95)
    CHI2_50_2D = 1.3863                        # 二维高斯 50% 联合区域阈值 χ²₂(0.50)
