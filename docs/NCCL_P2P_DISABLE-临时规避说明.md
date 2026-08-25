# NCCL_P2P_DISABLE 临时规避说明

> 适用场景：8×RTX 5090 服务器存在 BMC `Bus Uncorrectable` / IERR 等 PCIe 平台硬件故障，在厂商修机前需尽量降低多卡 vLLM 触发链路问题的概率。  
> **注意：此为软件规避，不能替代硬件工单，不能修复根因。**

---

## 1. 背景

| 项目 | 说明 |
|------|------|
| 硬件现状 | BMC 累计大量 `Bus Uncorrectable error`，伴 IERR/CATERR；8 卡 PCIe 链路存在严重降速（日志见 `sec_4935.log`） |
| 5090 互联 | 消费级 **无 NVLink**，卡间通信走 **PCIe（经 PEX890xx Switch）** |
| P2P | GPU 间 **PCIe 直拷**；与 NVLink 无关 |
| 本次挂死 | vLLM 加载权重时宿主机挂死（非容器 OOM）；根因在硬件平台 |

---

## 2. NCCL_P2P_DISABLE 做什么

```bash
export NCCL_P2P_DISABLE=1
```

| | 说明 |
|---|---|
| **关闭** | GPU↔GPU 的 PCIe P2P 直连拷贝 |
| **改为** | 经 CPU 内存中转的 NCCL 通信路径 |
| **不影响** | 多卡能否启动（TP=2/4/8 一般仍可起） |
| **不能解决** | BMC Bus Uncorrectable、IERR、整机挂死 |
| **可能效果** | 降低部分 PCIe 直拷压力；仍走 PCIe（CPU↔GPU），只是路径不同 |

---

## 3. 推荐环境变量（多卡 vLLM）

### 最小配置

```bash
export NCCL_P2P_DISABLE=1
```

### 平台仍不稳定时可叠加

```bash
export NCCL_P2P_DISABLE=1
export NCCL_SHM_DISABLE=1          # 可选，减少部分共享内存路径
export NCCL_IB_DISABLE=1           # 单机多卡、无 IB 时可选
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,max_split_size_mb:64"
```

### vLLM 启动参数建议

```bash
vllm serve /path/to/model \
  --tensor-parallel-size 8 \
  --disable-custom-all-reduce \
  ... # 其他原有参数
```

| 参数/变量 | 作用 |
|-----------|------|
| `NCCL_P2P_DISABLE=1` | 禁用 NCCL 的 GPU P2P |
| `--disable-custom-all-reduce` | 禁用 vLLM 自定义 allreduce（常依赖 P2P） |
| `NCCL_SHM_DISABLE=1` | 进一步保守时可开 |

---

## 4. Docker 示例

```bash
docker run -d --name vllm-joyai1 \
  --gpus all \
  -e NCCL_P2P_DISABLE=1 \
  -e NCCL_SHM_DISABLE=1 \
  -e PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,max_split_size_mb:64" \
  -v /export/package/joyai1:/models/joyai:ro \
  -p 127.0.0.1:8001:8001 \
  m.daocloud.io/docker.io/vllm/vllm-openai:nightly \
  vllm serve /models/joyai \
    --host 0.0.0.0 \
    --port 8001 \
    --tensor-parallel-size 8 \
    --disable-custom-all-reduce \
    --trust-remote-code \
    --gpu-memory-utilization 0.80
```

### docker-compose 片段

```yaml
environment:
  NCCL_P2P_DISABLE: "1"
  NCCL_SHM_DISABLE: "1"
  PYTORCH_CUDA_ALLOC_CONF: "expandable_segments:True,max_split_size_mb:64"
```

---

## 5. systemd 示例

```ini
[Service]
Environment=NCCL_P2P_DISABLE=1
Environment=NCCL_SHM_DISABLE=1
Environment=PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:64
ExecStart=/usr/bin/docker run ... vllm serve ... --disable-custom-all-reduce ...
```

---

## 6. 验证 P2P 是否已禁用

```bash
# 拓扑
nvidia-smi topo -m

# 查询 P2P（宿主机，需 PyTorch）
python3 -c "
import torch
for i in range(torch.cuda.device_count()):
    for j in range(torch.cuda.device_count()):
        if i != j:
            print(f'GPU{i}<->GPU{j}:', torch.cuda.can_device_access_peer(i,j))
"
```

`NCCL_P2P_DISABLE=1` 后 NCCL **不会使用** P2P 路径；`can_device_access_peer` 仍可能为 True（硬件能力仍在），以 NCCL 实际行为为准。

启动时加调试：

```bash
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=INIT,GRAPH
```

日志中不应再出现 P2P/NVLS 直连相关成功路径（视 NCCL 版本略有差异）。

---

## 7. 性能与限制

| 项目 | 说明 |
|------|------|
| 预期 | 多卡吞吐/延迟可能变差（视拓扑，常见几个点到更多） |
| 5090 无 NVLink | 本就全靠 PCIe；禁 P2P 后更依赖 CPU 中转，带宽瓶颈更明显 |
| 硬件仍坏 | 即使开 P2P_DISABLE，**仍可能**因 Bus Uncorrectable / IERR 整机挂死 |
| 修机前建议 | **不要** 8 卡满载压测；优先单卡冒烟 + 避开已知问题卡（如 GPU4） |

---

## 8. 与硬件工单的关系（给厂商说明）

本次已在软件侧启用 **`NCCL_P2P_DISABLE=1`** 作为临时规避，用于：

1. 降低多卡训练/推理时 GPU 间 P2P 直拷对异常 PCIe 链路的刺激；
2. 证明问题在修 P2P 开关后**仍存在**（若仍挂），则进一步排除「纯 NCCL 配置问题」，指向平台硬件。

**请厂商仍按硬件故障处理**：SEL 中 3531 条 Bus Uncorrectable、IERR/CATERR、8 卡 PCIe 降速至 5 GT/s、GPU4 `0xbadf2100` 等证据不因本规避而消失。

---

## 9. 操作建议（修机前）

1. 硬件工单照常提交（附 `sec_4935.log` + 本文档）。
2. 若必须跑业务：`NCCL_P2P_DISABLE=1` + `--disable-custom-all-reduce` + 降低 `--gpu-memory-utilization`（如 0.75~0.80）。
3. 可选 `CUDA_VISIBLE_DEVICES` 临时避开历史异常卡（如 GPU4），**需交叉换槽验证后再定责**。
4. 厂商签收硬件稳定后，再逐步恢复 P2P 并做对比测试。

---

## 10. 参考

- NCCL 环境变量：<https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html>
- vLLM 多卡：<https://docs.vllm.ai/en/latest/serving/distributed_serving.html>
- 本机诊断包：`sec_4935.log`（2026-08-25）

---

**文档版本**：2026-08-25  
**机器**：master-01 / 6410 X2 / 8×RTX 5090 / Broadcom PEX890xx
