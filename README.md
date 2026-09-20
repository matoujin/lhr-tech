# lhr-tech

本仓库包含 **Tesla 只读采集栈**（不发送任何车辆控制指令）。

完整运行说明（从 iPhone「Auth for Tesla」导出 refresh token、环境变量、Docker Compose、只读 HTTP 路径）见：

**[tesla-readonly/README.md](tesla-readonly/README.md)**

```bash
cd tesla-readonly
cp .env.example .env   # 填入 TESLA_REFRESH_TOKEN，切勿提交
docker compose up -d --build
```

没有 token 时：`TESLA_MOCK=1 docker compose up -d --build`，然后访问 `http://localhost:8080/health`。
