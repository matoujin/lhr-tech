#!/usr/bin/env bash
# 侦测指定 GPU 的 PCIe 链路 / AER / P2P；异常即非 0 退出。
# 用法:
#   ./check_gpu_pcie.sh              # 默认检查有问题的 GPU1 与 GPU4
#   ./check_gpu_pcie.sh 1 4          # 显式指定 GPU1、GPU4
#   STRESS=1 ./check_gpu_pcie.sh     # 额外做轻量 cuda P2P（可能打挂主机，慎用）

set -euo pipefail

GPUS=("${@:-1 4}")
STRESS="${STRESS:-0}"
ERR=0

need() { command -v "$1" >/dev/null 2>&1 || { echo "缺少命令: $1"; exit 2; }; }
need nvidia-smi
need lspci
need python3

echo "== 目标 GPU 序号: ${GPUS[*]} =="

# 1) 解析 BDF
declare -A BDF
while IFS=',' read -r idx bus; do
  idx="${idx#"${idx%%[![:space:]]*}"}"
  bus="${bus#"${bus%%[![:space:]]*}"}"
  bus="${bus// /}"
  [[ -n "$idx" ]] || continue
  # nvidia-smi PCI.BUS_ID 形如 00000000:29:00.0
  bdf=$(echo "$bus" | sed -E 's/^0000+//;s/^/0000:/' | sed 's/^0000:0000:/0000:/')
  if [[ "$bus" =~ ([0-9a-fA-F]+):([0-9a-fA-F]+):([0-9a-fA-F]+)\.([0-9]) ]]; then
    bdf=$(printf "%04x:%02x:%02x.%s" "0x${BASH_REMATCH[1]}" "0x${BASH_REMATCH[2]}" "0x${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}")
  else
    bdf="$bus"
  fi
  BDF["$idx"]="$bdf"
done < <(nvidia-smi --query-gpu=index,pci.bus_id --format=csv,noheader)

for g in "${GPUS[@]}"; do
  if [[ -z "${BDF[$g]:-}" ]]; then
    echo "[ERROR] GPU$g 不存在于 nvidia-smi"
    ERR=1
  else
    echo "GPU$g -> ${BDF[$g]}"
  fi
done
[[ $ERR -eq 0 ]] || exit 1

# 2) 链路宽度/速率 + AER 不可纠正状态
echo
echo "== PCIe 链路 / AER =="
for g in "${GPUS[@]}"; do
  bdf="${BDF[$g]}"
  info=$(lspci -s "${bdf#0000:}" -vvv 2>/dev/null || lspci -s "$bdf" -vvv 2>/dev/null || true)
  if [[ -z "$info" ]]; then
    echo "[ERROR] GPU$g ($bdf) lspci 读不到"
    ERR=1
    continue
  fi
  link=$(echo "$info" | grep -E 'LnkSta:' | head -1 || true)
  width=$(echo "$link" | grep -oE 'Width x[0-9]+' || true)
  speed=$(echo "$link" | grep -oE 'Speed [^,]+' || true)
  echo "GPU$g $bdf | $speed | $width"

  # 宽度异常（5090 正常多为 x16；掉到 x8/x4/x1 视为嫌疑）
  if echo "$width" | grep -Eq 'Width x(1|2|4|8)\b'; then
    echo "[ERROR] GPU$g PCIe 宽度降级: $width"
    ERR=1
  fi
  if echo "$link" | grep -qi 'Downgraded'; then
    echo "[ERROR] GPU$g LnkSta 标记 Downgraded"
    ERR=1
  fi

  # AER Uncorrectable 状态非 0
  ue=$(echo "$info" | awk '/UESta:/{print; exit}')
  if [[ -n "$ue" ]] && echo "$ue" | grep -Eqv 'UESta:.*-+.*-+' ; then
    # 任一非 - 的标志位
    if echo "$ue" | grep -Eq '[+]'; then
      echo "[ERROR] GPU$g AER UESta 有置位: $ue"
      ERR=1
    fi
  fi
done

# 3) dmesg 近期 PCIe/AER/NVRM
echo
echo "== 近期内核 PCIe/AER/Xid（最近 200 条匹配）=="
if dmesg -T 2>/dev/null | grep -Ei 'AER|PCIe|Uncorrectable|Fatal|NVRM: Xid|badf2100|Broken device' | tail -n 200; then
  :
else
  echo "(无匹配或无权限读 dmesg)"
fi
if dmesg 2>/dev/null | grep -Ei 'AER:.*error|Uncorrectable|Fatal event|NVRM: Xid' | tail -n 5 | grep -q .; then
  echo "[ERROR] dmesg 中已有 AER/Fatal/Xid 记录（见上）"
  ERR=1
fi

# 4) CUDA peer access 矩阵（只查询，不传大数据）
echo
echo "== CUDA P2P 可达性（query only）=="
export CHECK_GPUS="${GPUS[*]}"
python3 - <<'PY'
import os, sys
gpus = [int(x) for x in os.environ["CHECK_GPUS"].split()]
try:
    import torch
except Exception as e:
    print(f"[WARN] 无 torch，跳过 P2P query: {e}")
    sys.exit(0)

ok = True
print("   " + " ".join(f"G{g}" for g in gpus))
for i in gpus:
    row = []
    for j in gpus:
        if i == j:
            row.append("  .")
            continue
        try:
            can = torch.cuda.can_device_access_peer(i, j)
        except Exception as e:
            print(f"[ERROR] can_device_access_peer({i},{j}) 异常: {e}")
            ok = False
            can = False
        row.append("  Y" if can else "  N")
        # 默认：GPU1↔GPU4 一旦 P2P 可达就 FAIL（FAIL_ON_P2P=0 可关闭）
        if can and os.environ.get("FAIL_ON_P2P", "1") == "1":
            print(f"[ERROR] GPU{i}<->GPU{j} P2P=Y（FAIL_ON_P2P=1，按策略直接失败）")
            ok = False
    print(f"G{i}" + "".join(row))
sys.exit(0 if ok else 1)
PY
p2p_rc=$?
if [[ $p2p_rc -ne 0 ]]; then
  ERR=1
fi

# 5) 可选：轻量 P2P 拷贝压力（默认关）
if [[ "$STRESS" == "1" ]]; then
  echo
  echo "== STRESS=1：轻量 P2P copy（可能触发整机挂死，Ctrl+C 可停）=="
  export CHECK_GPUS="${GPUS[*]}"
  python3 - <<'PY' || ERR=1
import os, sys, time
import torch
gpus = [int(x) for x in os.environ["CHECK_GPUS"].split()]
n = 64 * 1024 * 1024  # 64MiB
for i in gpus:
    for j in gpus:
        if i >= j:
            continue
        if not torch.cuda.can_device_access_peer(i, j):
            print(f"skip P2P copy GPU{i}->GPU{j} (no peer)")
            continue
        print(f"P2P copy GPU{i}->GPU{j} ...", flush=True)
        with torch.cuda.device(i):
            a = torch.randn(n, device=f"cuda:{i}")
            torch.cuda.synchronize(i)
        with torch.cuda.device(j):
            torch.cuda.device(j).enable_peer_access(torch.device(f"cuda:{i}")) if False else None
        # 标准 peer copy
        with torch.cuda.device(i):
            b = torch.empty(n, device=f"cuda:{j}")
            b.copy_(a)
            torch.cuda.synchronize(i)
            torch.cuda.synchronize(j)
        print(f"OK GPU{i}->GPU{j}")
print("stress done")
PY
fi

echo
if [[ $ERR -ne 0 ]]; then
  echo "结果: FAIL（发现 PCIe/P2P/内核错误迹象）"
  exit 1
fi
echo "结果: PASS（当前采样未见明显异常；不能证明机器长期稳定）"
exit 0
