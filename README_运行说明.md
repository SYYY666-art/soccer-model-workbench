# UPC 2026 Problem B · 点球轨迹预测实验台 — 运行说明

## 一、环境要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows 10/11（macOS/Linux 也可，启动命令相同） |
| Python | 3.10 或更高版本（开发环境为 3.13） |
| 网络 | 首次安装依赖时需要联网 |

## 二、快速启动（Windows）

1. 解压本压缩包到任意路径（路径中不要包含中文，避免编码问题）；
2. 双击 `启动实验台.bat`；
3. 首次运行会自动创建虚拟环境并安装依赖（约 1–2 分钟），随后自动打开浏览器；
4. 若浏览器未自动打开，手动访问 `http://localhost:8501`。

## 三、手动启动（可选）

```bat
cd 本目录
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app_main.py
```

## 四、界面速览

- **左侧边栏**
  - 顶部按钮：中文 / English 界面切换（评委为国际评审时使用英文模式）；
  - 1. 观测数据：经典算例下拉框（6 例）自动填入两帧坐标，也可手动修改；可启用第三观测帧 t₃；
  - 2. 误差模型：独立高斯 σᵣ 或均匀舍入 ±0.005 m；蒙特卡洛样本数；
  - 3. 气动模型管线：A-1 / A-2 / B / C 四条管线，每条下方附关键计算参数表与通用物理常数表；
  - 4. 风场与自旋设定。
- **主区**
  - 轨迹时间轴滑块 + 快捷跳转；
  - 6 张指标卡片（事件、v₀、C_D、自旋、SVD 诊断、概率预测）；
  - 3D 球场图（轨迹、矢量、可能位置云团）与 2D 球门平面落点热图（95% 椭圆、HDR）；
  - 折叠区：数据诊断基线（§2）、事件统计与分位数（§6）、A/B/C 模型包络（§6.1）、COMSOL 实测数据对照（§7，含论文用英文图注）。

## 五、目录说明

| 路径 | 内容 |
|---|---|
| `app_main.py` | Streamlit 主程序 |
| `physics_theory.py` | 三维动力学母模型、A/B/C 气动闭合、反演与事件定位 |
| `uncertainty_engine.py` | 蒙特卡洛传播、HDR/置信椭圆、模型包络 |
| `comsol_bridge.py` | COMSOL 系数图谱接口（C 管线） |
| `comsol_lab.py` | 交接数据解析、实测对照、锚点表生成 |
| `visualizer_3d.py` | 3D 球场与 2D 落点图渲染 |
| `i18n.py` | 中英文界面文本 |
| `config.py` | 参数规范与经典算例库 |
| `validation_suite.py` | 合成真值回收验证套件（命令行运行） |
| `data/comsol_table.csv` | C 管线锚点系数表（由交接数据平台期平均自动生成） |
| `data/UPC2026_B_COMSOL_队友交接/` | COMSOL 交接数据（CSV/TXT/PNG） |
| `docs/` | 实验台物理建模思路、COMSOL 交付格式、实测对照分析 |

## 六、常见问题

- **双击 bat 提示找不到 Python**：安装 Python 3.10+，勾选 "Add Python to PATH" 后重试。
- **页面能打开但预测一直不更新**：刷新浏览器页面（WebSocket 断连后交互不会触发重算）。
- **C 管线不可用**：确认 `data/UPC2026_B_COMSOL_队友交接/` 目录完整，启动时会自动重新生成 `data/comsol_table.csv`。
- **验证数值正确性**：在项目目录运行 `python validation_suite.py`（合成真值回收测试，精确坐标下落点误差约 2–7 cm）。
