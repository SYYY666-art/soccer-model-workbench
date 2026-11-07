import numpy as np
import plotly.graph_objects as go
from config import SimConfig


class PenaltyVisualizer3D:
    """清爽白底学术风格三维点球实验台渲染引擎。

    图中所有矢量与轨迹均基于 A/B/C 管线反演结果：
    - "升力/有效旋转项"：A 管线为 Ω_eff×u（低阶有效旋转），B/C 为经典 Magnus 升力；
    - 落点统计图区分均值/中位数/核密度众数，并叠加 95% 联合椭圆与 95% HDR。"""

    VIZ = {
        "zh": {
            "goal_frame": "球门框 (7.32m×2.44m)",
            "ca_baseline": "三点恒加速基线",
            "aero_traj": "{m} 气动主轨迹",
            "obs_pts": "初始观测点",
            "cloud": "t = {t:.3f} s 可能位置云",
            "vel": "速度矢量 v(t)",
            "lift": "升力/有效旋转项",
            "acc": "合加速度 a(t)",
            "mk_goal": "过门线落点", "mk_ground": "触地点", "mk_timeout": "飞行终点",
            "ev_goal": "首次过门线", "ev_ground": "触地终止", "ev_timeout": "超时未达",
            "title": "三维点球仿真球场（{m} 管线 · 事件：{e} · t = {t:.4f} s）",
            "ax_x": "X: 距点球点距离 (m)", "ax_y": "Y: 球门横向坐标 (m)", "ax_z": "Z: 离地高度 (m)",
            "kde": "落点核密度", "mc_pts": "蒙特卡洛落点样本",
            "hdr": "95% 最高密度区域 (HDR)",
            "ell95": "95% 联合置信椭圆 (χ²=5.991)", "ell50": "50% 联合区域 (χ²=1.386)",
            "clear": "整球净空边界 (扣除球半径)",
            "mean": "均值 ({y:.3f}, {z:.3f})", "median": "中位数 ({y:.3f}, {z:.3f})",
            "mode": "密度众数 ({y:.3f}, {z:.3f})", "map": "MAP 预测落点 ({y:.3f}, {z:.3f})",
            "title2d": "球门平面 (x = 11 m) 落点分布与门框几何判据",
            "p_reach": "P(过线)={v:.1%}", "p_in": "P(进球|过线)={v:.1%}", "p_ground": "P(触地)={v:.1%}",
            "ax2d_y": "球门水平坐标 Y (m)", "ax2d_z": "球门高度坐标 Z (m)",
        },
        "en": {
            "goal_frame": "Goal frame (7.32 m × 2.44 m)",
            "ca_baseline": "Constant-acceleration baseline",
            "aero_traj": "{m} aerodynamic trajectory",
            "obs_pts": "Initial observations",
            "cloud": "t = {t:.3f} s position cloud",
            "vel": "Velocity vector v(t)",
            "lift": "Lift / effective-spin term",
            "acc": "Total acceleration a(t)",
            "mk_goal": "Goal-crossing point", "mk_ground": "Ground-contact point", "mk_timeout": "End of flight",
            "ev_goal": "First crossing", "ev_ground": "Ground contact", "ev_timeout": "Timeout",
            "title": "3-D penalty stadium ({m} pipeline · Event: {e} · t = {t:.4f} s)",
            "ax_x": "X: distance from penalty spot (m)", "ax_y": "Y: lateral goal coordinate (m)",
            "ax_z": "Z: height above ground (m)",
            "kde": "Impact-point kernel density", "mc_pts": "Monte Carlo impact samples",
            "hdr": "95% highest-density region (HDR)",
            "ell95": "95% joint confidence ellipse (χ²=5.991)", "ell50": "50% joint region (χ²=1.386)",
            "clear": "Full-ball clearance boundary (ball radius subtracted)",
            "mean": "Mean ({y:.3f}, {z:.3f})", "median": "Median ({y:.3f}, {z:.3f})",
            "mode": "Density mode ({y:.3f}, {z:.3f})", "map": "MAP impact point ({y:.3f}, {z:.3f})",
            "title2d": "Goal plane (x = 11 m): impact distribution and frame criteria",
            "p_reach": "P(cross)={v:.1%}", "p_in": "P(goal|cross)={v:.1%}", "p_ground": "P(ground)={v:.1%}",
            "ax2d_y": "Lateral coordinate Y (m)", "ax2d_z": "Height coordinate Z (m)",
        },
    }

    # ------------------------------------------------------------------
    @staticmethod
    def _create_sphere_mesh(center, radius=0.17, res=14):
        u = np.linspace(0, 2 * np.pi, res)
        v = np.linspace(0, np.pi, res)
        x = center[0] + radius * np.outer(np.cos(u), np.sin(v))
        y = center[1] + radius * np.outer(np.sin(u), np.sin(v))
        z = center[2] + radius * np.outer(np.ones(np.size(u)), np.cos(v))
        return x, y, z

    @staticmethod
    def _add_3d_arrow(fig, start, vec, scale, color, name, showlegend=True):
        end = start + vec * scale
        fig.add_trace(go.Scatter3d(
            x=[start[0], end[0]], y=[start[1], end[1]], z=[start[2], end[2]],
            mode="lines", line=dict(color=color, width=7), name=name, showlegend=showlegend
        ))
        fig.add_trace(go.Cone(
            x=[end[0]], y=[end[1]], z=[end[2]],
            u=[vec[0]], v=[vec[1]], w=[vec[2]],
            sizemode="absolute", sizeref=0.20, anchor="tip",
            colorscale=[[0, color], [1, color]], showscale=False, name=name, showlegend=False
        ))

    # ------------------------------------------------------------------
    @classmethod
    def build_3d_stadium_figure(cls, base_res, mc_cloud_curr, frame_idx, t1, t2, r1, r2,
                                show_cloud=True, lang="zh"):
        L = cls.VIZ.get(lang, cls.VIZ["zh"])
        fig = go.Figure()
        model_id = base_res.get("model_id", "A-2")

        # 1. 球场草坪条纹
        stripe_edges = np.linspace(-1.0, 12.5, 9)
        for i in range(len(stripe_edges) - 1):
            c_turf = "#2d6a4f" if i % 2 == 0 else "#40916c"
            px = np.array([[stripe_edges[i], stripe_edges[i + 1]], [stripe_edges[i], stripe_edges[i + 1]]])
            py = np.array([[-5.5, -5.5], [5.5, 5.5]])
            pz = np.zeros((2, 2))
            fig.add_trace(go.Surface(
                x=px, y=py, z=pz,
                colorscale=[[0, c_turf], [1, c_turf]],
                showscale=False, opacity=0.90, showlegend=False, hoverinfo="skip"
            ))

        # 球门底线与小禁区白线
        fig.add_trace(go.Scatter3d(
            x=[11.0, 11.0], y=[-5.5, 5.5], z=[0.01, 0.01],
            mode="lines", line=dict(color="white", width=5), showlegend=False, hoverinfo="skip"
        ))
        fig.add_trace(go.Scatter3d(
            x=[11.0, 5.5, 5.5, 11.0], y=[-4.5, -4.5, 4.5, 4.5], z=[0.01, 0.01, 0.01, 0.01],
            mode="lines", line=dict(color="rgba(255,255,255,0.75)", width=3), showlegend=False, hoverinfo="skip"
        ))

        # 2. 立体球门框与后方球网
        fig.add_trace(go.Scatter3d(
            x=[11.0, 11.0, 11.0, 11.0, 11.0],
            y=[-3.66, -3.66, 3.66, 3.66, -3.66],
            z=[0.0, 2.44, 2.44, 0.0, 0.0],
            mode="lines", line=dict(color="#1e293b", width=9), name=L["goal_frame"]
        ))
        net_x = 12.1
        for ny in np.linspace(-3.66, 3.66, 15):
            fig.add_trace(go.Scatter3d(
                x=[11.0, net_x, net_x], y=[ny, ny, ny], z=[2.44, 2.44, 0.0],
                mode="lines", line=dict(color="rgba(100,116,139,0.35)", width=1.5),
                showlegend=False, hoverinfo="skip"
            ))
        for nz in np.linspace(0.0, 2.44, 7):
            fig.add_trace(go.Scatter3d(
                x=[11.0, net_x, net_x, 11.0], y=[-3.66, -3.66, 3.66, 3.66], z=[nz, nz, nz, nz],
                mode="lines", line=dict(color="rgba(100,116,139,0.35)", width=1.5),
                showlegend=False, hoverinfo="skip"
            ))

        # 3. 匀加速基线 vs 气动主轨迹 + 地面投影
        fig.add_trace(go.Scatter3d(
            x=base_res["pos_ca"][0], y=base_res["pos_ca"][1], z=base_res["pos_ca"][2],
            mode="lines", line=dict(color="#64748b", width=4, dash="dash"), name=L["ca_baseline"]
        ))
        fig.add_trace(go.Scatter3d(
            x=base_res["states_ode"][0], y=base_res["states_ode"][1], z=base_res["states_ode"][2],
            mode="lines", line=dict(color="#00b4d8", width=8), name=L["aero_traj"].format(m=model_id)
        ))
        fig.add_trace(go.Scatter3d(
            x=base_res["states_ode"][0], y=base_res["states_ode"][1],
            z=np.zeros_like(base_res["states_ode"][0]) + 0.015,
            mode="lines", line=dict(color="rgba(0,0,0,0.35)", width=4, dash="dot"),
            showlegend=False, hoverinfo="skip"
        ))

        # 4. 初始观测点（含可选第三帧）
        obs_list = [SimConfig.R0, np.asarray(r1, float), np.asarray(r2, float)]
        text_list = ["t0=0s", f"t1={t1}s", f"t2={t2}s"]
        if base_res.get("t3") is not None:
            obs_list.append(np.asarray(base_res["r3"], float))
            text_list.append(f"t3={base_res['t3']}s")
        obs_pts = np.vstack(obs_list)
        fig.add_trace(go.Scatter3d(
            x=obs_pts[:, 0], y=obs_pts[:, 1], z=obs_pts[:, 2],
            mode="markers+text",
            marker=dict(size=6, color="#f59e0b", symbol="diamond", line=dict(color="white", width=1)),
            text=text_list, textposition="top center",
            name=L["obs_pts"]
        ))

        # 5. 当前时刻蒙特卡洛可能位置云团（可开关，便于观察矢量箭头）
        t_curr = base_res["t_eval"][frame_idx]
        if show_cloud:
            fig.add_trace(go.Scatter3d(
                x=mc_cloud_curr[:, 0], y=mc_cloud_curr[:, 1], z=mc_cloud_curr[:, 2],
                mode="markers", marker=dict(size=3.0, color="#ef4444", opacity=0.38),
                name=L["cloud"].format(t=t_curr)
            ))

        # 6. 当前时刻立体足球与三维矢量
        pos_curr = base_res["states_ode"][:3, frame_idx]
        vel_curr = base_res["states_ode"][3:, frame_idx]
        acc_curr = base_res["acc_total"][:, frame_idx]
        amag_curr = base_res["acc_magnus"][:, frame_idx]

        sx, sy, sz = cls._create_sphere_mesh(pos_curr, radius=0.17)
        fig.add_trace(go.Surface(
            x=sx, y=sy, z=sz,
            colorscale=[[0, "#ffffff"], [1, "#f97316"]],
            showscale=False, name="当前足球", showlegend=False
        ))

        cls._add_3d_arrow(fig, pos_curr, vel_curr, scale=0.045, color="#16a34a", name=L["vel"])
        cls._add_3d_arrow(fig, pos_curr, amag_curr, scale=0.18, color="#d97706", name=L["lift"])
        cls._add_3d_arrow(fig, pos_curr, acc_curr, scale=0.08, color="#dc2626", name=L["acc"])

        # 7. 事件标签与落点标记
        label = base_res.get("event_label", "goal")
        event_marker_name = {"goal": L["mk_goal"], "ground": L["mk_ground"],
                             "timeout": L["mk_timeout"]}.get(label, label)
        if base_res.get("event_pos") is not None:
            pe = np.asarray(base_res["event_pos"], float)
            fig.add_trace(go.Scatter3d(
                x=[pe[0]], y=[pe[1]], z=[pe[2]],
                mode="markers", marker=dict(size=7, color="#e63946", symbol="diamond"),
                name=event_marker_name
            ))

        event_note = {"goal": L["ev_goal"], "ground": L["ev_ground"],
                      "timeout": L["ev_timeout"]}.get(label, label)
        fig.update_layout(
            title=L["title"].format(m=model_id, e=event_note, t=t_curr),
            scene=dict(
                xaxis=dict(title=L["ax_x"], range=[-0.8, 12.5]),
                yaxis=dict(title=L["ax_y"], range=[-5.2, 5.2]),
                zaxis=dict(title=L["ax_z"], range=[0.0, 3.1]),
                aspectmode="manual", aspectratio=dict(x=2.2, y=1.55, z=0.65),
                camera=dict(eye=dict(x=-1.55, y=-1.65, z=0.82))
            ),
            margin=dict(l=0, r=0, b=0, t=65), height=580,
            legend=dict(
                orientation="h", yanchor="bottom", y=0.94, xanchor="center", x=0.5,
                bgcolor="rgba(255,255,255,0.85)"
            )
        )
        return fig

    # ------------------------------------------------------------------
    @staticmethod
    def build_2d_goal_heatmap(mc_data, base_res, show_legend=True, lang="zh"):
        L = PenaltyVisualizer3D.VIZ.get(lang, PenaltyVisualizer3D.VIZ["zh"])
        fig = go.Figure()

        gy = mc_data["goal_y_mc"]
        gz = mc_data["goal_z_mc"]
        stats = mc_data.get("stats", {})
        probs = mc_data.get("probs", {})

        # 动态坐标范围：覆盖落点主体、事件落点与球门框，留白与椭圆最小半径联动
        ev_pos = np.asarray(base_res["event_pos"], float) if base_res.get("event_pos") is not None else None
        y_lo = min(-3.66, float(np.nanpercentile(gy, 1))) if len(gy) else -3.66
        y_hi = max(3.66, float(np.nanpercentile(gy, 99))) if len(gy) else 3.66
        z_lo = min(0.0, float(np.nanpercentile(gz, 1))) if len(gz) else 0.0
        z_hi = max(2.44, float(np.nanpercentile(gz, 99))) if len(gz) else 2.44
        if ev_pos is not None:
            y_lo, y_hi = min(y_lo, ev_pos[1]), max(y_hi, ev_pos[1])
            z_lo, z_hi = min(z_lo, ev_pos[2]), max(z_hi, ev_pos[2])
        pad = max(0.4, 0.10 * max(y_hi - y_lo, z_hi - z_lo))
        y_min, y_max = y_lo - pad, y_hi + pad
        z_min, z_max = z_lo - pad, z_hi + pad
        span = max(y_max - y_min, z_max - z_min)

        # 1. 核密度等高线与落点散点
        fig.add_trace(go.Histogram2dContour(
            x=gy, y=gz,
            colorscale="YlOrRd", showscale=False,
            contours=dict(coloring="fill"), opacity=0.6, name=L["kde"]
        ))
        fig.add_trace(go.Scatter(
            x=gy, y=gz,
            mode="markers", marker=dict(size=3, color="#1d3557", opacity=0.35),
            name=L["mc_pts"]
        ))

        # 2. 95% HDR 等高线（最高密度区域）
        hdr = stats.get("hdr") if stats else None
        if hdr is not None:
            fig.add_trace(go.Contour(
                x=hdr["y"], y=hdr["z"], z=hdr["density"],
                contours=dict(start=hdr["level"], end=hdr["level"], size=1.0,
                              coloring="lines"),
                line=dict(color="#e11d48", width=2.5),
                showscale=False, hoverinfo="skip",
                name=L["hdr"]
            ))

        # 3. 50% / 95% 高斯联合椭圆（χ²₂ 阈值；最小可视半径保证极端退化下可见）
        ell = stats.get("ellipse_pts") if stats else None
        if ell is not None:
            mean_yz = np.mean(ell, axis=1)
            rel = ell - mean_yz[:, None]
            radii = np.sqrt(np.max(np.sum(rel ** 2, axis=0)))
            k = max(radii, 0.08 * span)
            ell_show = mean_yz[:, None] + rel * (k / max(radii, 1e-9))
            fig.add_trace(go.Scatter(
                x=ell_show[0], y=ell_show[1],
                mode="lines", line=dict(color="#e11d48", width=2.5, dash="dashdot"),
                name=L["ell95"]
            ))
        ell50 = stats.get("ellipse_pts_50") if stats else None
        if ell50 is not None:
            mean50 = np.mean(ell50, axis=1)
            rel50 = ell50 - mean50[:, None]
            radii50 = np.sqrt(np.max(np.sum(rel50 ** 2, axis=0)))
            k50 = max(radii50, 0.04 * span)
            ell50_show = mean50[:, None] + rel50 * (k50 / max(radii50, 1e-9))
            fig.add_trace(go.Scatter(
                x=ell50_show[0], y=ell50_show[1],
                mode="lines", line=dict(color="#e11d48", width=1.5, dash="dot"),
                name=L["ell50"]
            ))

        # 4. 球门框与整球净空边界
        fig.add_trace(go.Scatter(
            x=[-3.66, -3.66, 3.66, 3.66, -3.66], y=[0.0, 2.44, 2.44, 0.0, 0.0],
            mode="lines", line=dict(color="black", width=4), name=L["goal_frame"]
        ))
        r_b = SimConfig.RADIUS
        fig.add_trace(go.Scatter(
            x=[-3.66 + r_b, -3.66 + r_b, 3.66 - r_b, 3.66 - r_b, -3.66 + r_b],
            y=[r_b, 2.44 - r_b, 2.44 - r_b, r_b, r_b],
            mode="lines", line=dict(color="#16a34a", width=2, dash="dot"),
            name=L["clear"]
        ))

        # 5. 均值 / 中位数 / 核密度众数
        if stats:
            if not np.isnan(stats["y"]["mean"]):
                fig.add_trace(go.Scatter(
                    x=[stats["y"]["mean"]], y=[stats["z"]["mean"]],
                    mode="markers", marker=dict(size=12, color="#7c3aed", symbol="diamond"),
                    name=L["mean"].format(y=stats["y"]["mean"], z=stats["z"]["mean"])
                ))
            if not np.isnan(stats["y"]["median"]):
                fig.add_trace(go.Scatter(
                    x=[stats["y"]["median"]], y=[stats["z"]["median"]],
                    mode="markers", marker=dict(size=12, color="#0d9488", symbol="triangle-up"),
                    name=L["median"].format(y=stats["y"]["median"], z=stats["z"]["median"])
                ))
            if stats.get("mode"):
                fig.add_trace(go.Scatter(
                    x=[stats["mode"]["y"]], y=[stats["mode"]["z"]],
                    mode="markers", marker=dict(size=12, color="#2563eb", symbol="circle"),
                    name=L["mode"].format(y=stats["mode"]["y"], z=stats["mode"]["z"])
                ))

        # 6. 气动最可能落点（MAP 事件落点）
        if base_res.get("event_pos") is not None:
            pe = np.asarray(base_res["event_pos"], float)
            fig.add_trace(go.Scatter(
                x=[pe[1]], y=[pe[2]],
                mode="markers", marker=dict(size=15, color="#e63946", symbol="star"),
                name=L["map"].format(y=pe[1], z=pe[2])
            ))

        title = L["title2d"]
        if probs:
            title += (f" | {L['p_reach'].format(v=probs.get('P_reach', 0))} "
                      f"{L['p_in'].format(v=probs.get('P_in_given_reach', 0))} "
                      f"{L['p_ground'].format(v=probs.get('P_ground', 0))}")

        fig.update_layout(
            title=title,
            xaxis=dict(title=L["ax2d_y"], range=[y_min, y_max]),
            yaxis=dict(title=L["ax2d_z"], range=[z_min, z_max]),
            height=580, margin=dict(l=20, r=20, b=20, t=65), showlegend=show_legend,
            legend=dict(
                orientation="h", yanchor="bottom", y=0.62, xanchor="center", x=0.5,
                bgcolor="rgba(255,255,255,0.85)"
            )
        )
        return fig
