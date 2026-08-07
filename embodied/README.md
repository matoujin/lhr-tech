# 具身技术概览

按「攻击面 → 本体/OS → 模型 → 平台」组织公开资料，便于快速扫清地图。偏情报索引，不替代原文。

---

## 1. 具身攻击

感知即指令面：模型读到的画面/声音可被当作任务上下文，输出会变成有质量的动作。

### 1.1 动能提示注入（Kinetic Prompt Injection）

- 来源：[Black Hat USA 2026 · Kinetic Prompt Injection（PDF）](https://i.blackhat.com/BH-USA-26/Presentations/BH'26_Kinetic_Prompt_Injection.pdf)（BT6 / Pliny）
- 对象：库存 Unitree Go2 + Gemini Robotics-ER（无固件改动、无网络 foothold）
- 输入路径：仅摄像头 / 麦克风
- 三类控制权失败：
  - **Locomotion Override**：感知侧指令导致与任务/安全预期不符的运动
  - **Principal Override**：攻击者上下文取代操作者/安全权威
  - **Programming Override**：停机/纠正指令被忽略、重解释或延后
- 研究建议路径：仿真复现（MuJoCo / SDK / 录制音视频）→ 注入场景线索 → 度量策略漂移与急停可靠性 → 保留可复现轨迹

### 1.2 宇树机器狗越狱与固件面

- 微信深述（深蓝）：[越狱的宇树机器狗](https://mp.weixin.qq.com/s/0XOoNyCRadLr6GvdhkmEYg)（部分环境需验证后阅读）
- BLE Wi‑Fi 配置命令注入（可蠕虫）：[UniPwn](https://github.com/Bin4ry/UniPwn) · CVE-2025-35027 / CVE-2025-60017（Go2 / G1 / H1 / B2 等共用固件血统）
- OTA UPK 解密与固件研究：[UniTEABag](https://github.com/Bin4ry/UniTEABag) · 相关 CVE-2026-1442（TEA + 硬编码常量；MQTT 下发链路是交付瓶颈）
- BH 演讲同步提到：MQTT OTA 任务拦截、定位 IDOR、局域网/Wi‑Fi/蓝牙多条 RCE→root 路径、工厂复位分区污染等（以厂商披露与 CVE 为准）

### 1.3 无人车攻击面（提纲）

| 层 | 典型面 |
| --- | --- |
| 感知 | 对抗样本、传感器欺骗（激光/相机/毫米波）、标定污染 |
| 定位/地图 | GNSS 欺骗、HD Map 投毒、回环/重定位误导 |
| 规划决策 | 目标替换、安全规则绕过、人机接管边界模糊 |
| 通信/OTA | V2X、诊断总线、远程更新供应链 |
| 执行 | 制动/转向控制链完整性、急停失效 |

> 防御侧共性：把「模型输出 → 工具/执行器」当成可信边界；急停与权限不可被上下文覆盖；固件/OTA 需签名与可审计交付。

---

## 2. 具身实现 / 操作系统

### 2.1 宇树（Unitree）

| 资源 | 说明 | 链接 |
| --- | --- | --- |
| UniTEABag | UPK OTA 包加解密研究工具 | https://github.com/Bin4ry/UniTEABag |
| UniPwn | BLE Wi‑Fi 配置面安全研究 | https://github.com/Bin4ry/UniPwn |
| Go2 电机逆向 | Go2 电机（近 GO-M8010-6）分析 | https://github.com/thomasfla/go2_motor_analysis/ |
| UnifoLM‑VLA‑0 | 宇树开源操作向 VLA | https://github.com/unitreerobotics/unifolm-vla |

### 2.2 智元（Agibot）

| 资源 | 说明 | 链接 |
| --- | --- | --- |
| 灵渠 Link‑U OS | 本体操作系统组织账号 / 主仓 | https://github.com/Link-U-OS · [Link-U-OS](https://github.com/Link-U-OS/Link-U-OS) |
| AimRT | 现代机器人高性能运行时 | https://github.com/AimRT/AimRT |
| Agibot World | 大规模操作数据/平台（IROS 2025 Best Paper Finalist 等） | https://github.com/OpenDriveLab/Agibot-World |

配套商业平台见 §4.2。

---

## 3. VLA / VLM 模型

按「世界模型 / 通用人形 / 开源操作 / 国内厂商线」粗分。

| 模型 | 要点 | 入口 |
| --- | --- | --- |
| **NVIDIA Cosmos 3** | 开放世界模型族：理解 + 世界生成 + 动作预测；Super 64B / Nano 16B / Edge 4B；OpenMDW | [NVIDIA Blog](https://blogs.nvidia.com/blog/open-world-models-physical-ai/) |
| **Isaac GR00T** | NVIDIA 人形/机器人基础模型与技能栈 | NVIDIA Isaac / GR00T 文档与模型页 |
| **π0 / π0.5** | Physical Intelligence；常见开源 VLA 对比基线 | Physical Intelligence 论文与权重发布 |
| **OpenVLA** | 早期开源操作向 VLA 代表，生态与复现基线 | 社区 OpenVLA 仓库 |
| **UnifoLM‑VLA‑0** | 宇树；Qwen2.5‑VL 系 + Action Head；G1 上 12 类操作单策略 | [GitHub](https://github.com/unitreerobotics/unifolm-vla) · [主页](https://unigen-x.github.io/unifolm-vla.github.io/) |
| **RynnBrain** | 阿里达摩；2B–122B 具身基础模型族；Nav / Plan / VLA 变体 | [GitHub](https://github.com/alibaba-damo-academy/RynnBrain) · [arXiv](https://arxiv.org/abs/2602.14979) |
| **LingBot‑VLA** | Robbyant；偏实用训练效率；RoboTwin / 多本体基准 | [GitHub](https://github.com/Robbyant/lingbot-vla/) |
| **Xiaomi‑Robotics‑0（R0）** | 小米；~4.7B，Qwen3‑VL + DiT flow‑matching；异步推理真机实时 | [官网](https://robotics.xiaomi.com/xiaomi-robotics-0.html) · [GitHub](https://github.com/XiaomiRobotics/Xiaomi-Robotics-0) |
| **Hy‑VLA（Hy‑Embodied‑0.5‑VLA）** | 腾讯混元具身线；UMI 预训练 + RoboTwin 后训；Tairos 模型族一环 | [GitHub](https://github.com/Tencent-Hunyuan/Hy-Embodied-0.5-VLA) |

选型粗规则：

1. 要仿真数据/世界预测 → Cosmos / Omniverse 工具链  
2. 要双臂操作基准对齐 → RoboTwin 上比 π0.5 / LingBot / Hy‑VLA  
3. 要真机低延迟 → 看异步 chunk（小米 R0）与边缘尺寸（Cosmos Edge）  
4. 要接国产本体生态 → 宇树 UnifoLM、智元 Agibot World、腾讯 Tairos / Hy‑VLA  

---

## 4. 具身平台

### 4.1 腾讯 Tairos

- 门户：https://tairos.tencent.com/  
- 文档：https://tairos.tencent.com/docs  
- 架构要点：HAL 硬件抽象 + Skill 跨本体；Hy‑Embodied 模型服务；Apexio / TairosAgent；RoboFusion 通信；Isaac Sim 云仿真  
- 规划大模型：WebSocket 双向会话（init → 环境 BDDL/Graph → 人机交互 → actions → action_feedback）

### 4.2 智元三件套

| 产品 | 定位 | 链接 |
| --- | --- | --- |
| 灵心 LinkSoul | 交互智能：人设/知识库/表情动作/设备下发 | https://linksoul.agibot.com/ |
| 灵创 LinkCraft | 运动智能 | https://linkcraft.agibot.com/ |
| 精灵 Genie Studio | 作业智能 | https://genie.agibot.com/geniestudio |

### 4.3 仿真与评测

| 平台 | 用途 | 链接 |
| --- | --- | --- |
| Isaac Sim + Isaac Lab | 高保真仿真、策略训练与规模化评测 | https://docs.isaacsim.omniverse.nvidia.com/latest/index.html |
| MuJoCo | 高精度刚体动力学；常作策略/接触基线 | https://mujoco.org/ |
| RoboTwin 2.0 | 双臂数据生成与 50 任务基准（SAPIEN；有 IsaacLab‑Arena 分支） | https://robotwin-platform.github.io/ · [GitHub](https://github.com/RoboTwin-Platform/RoboTwin) |
| SAPIEN / ManiSkill | 可交互物体物理引擎与大规模操作任务集 | SAPIEN / ManiSkill 官方仓库 |

---

## 5. 一张关系图

```text
感知(VLM/世界模型) ──► 规划(Agent/Planner) ──► VLA/策略 ──► 运行时(OS/AimRT/HAL)
        ▲                      │                      │
        │                      ▼                      ▼
   仿真数据合成          人机/工具调用            电机/关节/末端
   (Cosmos/Isaac/…)      (Tairos/灵心/…)         (本体固件/总线)

攻击面贯穿：感知上下文投毒 · 模型合规失败 · OTA/固件供应链 · 急停与权限覆写
```

---

## 6. 延伸阅读清单

1. BH'26 Kinetic Prompt Injection PDF（上）  
2. UniPwn / UniTEABag（宇树固件与配置面）  
3. Cosmos 3 Physical AI 博文  
4. Tairos 规划 API 文档  
5. Agibot World + AimRT + Link‑U OS  
6. RoboTwin 2.0 与各开源 VLA 排行对照  

---

*整理自公开链接与仓库说明；CVE 状态与厂商补丁以官方公告为准。安全相关条目仅作防御与研究索引。*
