# lhr-tech

## 思如泉涌 MCP

已接入远程 MCP：`http://116.198.229.83:9986/mcp`

### 在 Cursor 里使用

项目配置：`.cursor/mcp.json`

1. 用 Cursor 打开本仓库
2. 打开 **Settings → Tools & MCP**，确认 `sruqy-daily-updates` 已启用（绿点）
3. 在 Agent 对话里即可调用工具 `get_daily_updates`

可选参数：`date`（YYYY-MM-DD）、`limit`（默认 30）、`source`（来源过滤）

### 命令行调用（uv）

```bash
cd sruqy_mcp
uv run sruqy-daily
uv run sruqy-daily --date 2026-07-19 --limit 10
```
