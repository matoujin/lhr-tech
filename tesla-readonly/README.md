# Tesla 只读采集栈

用 iPhone「Auth for Tesla」导出的 **Refresh Token**，只读拉取车辆状态、充电、行驶、电池/位置/空调遥测，写入 SQLite 与 `latest.json`，并用本机 HTTP 接口查看。

**不做：** Fleet/开发者应用注册、上车锁车、开关空调、启停充电、鸣笛、闪灯、唤醒以外的任何车辆指令。本栈 **不会调用** `/command/*` 或 `/wake_up`。车辆休眠时只记录列表里的 `state`，等它自己上线后再拉 `vehicle_data`。

## 为什么不是 TeslaMate + Grafana

官方 TeslaMate Compose **不能**用环境变量 `TESLA_REFRESH_TOKEN` 自动登录：必须打开 `:4000` 网页手工粘贴 Access Token + Refresh Token。本仓库约束是「token 只走环境变量、可移植、不开 Fleet」，因此采用 **teslapy 同款 Owner API refresh grant** 的小型 Python（uv）轮询器。

栈只有一个服务，用 Docker Compose 即可在任意主机上跑。

## 从 Auth for Tesla 导出 Refresh Token

1. iPhone 安装 [Auth for Tesla](https://apps.apple.com/app/auth-for-tesla/id1552058613)，用 Tesla 账号登录（含 MFA）。
2. 打开对应车辆或账号页，找到 **Refresh Token**（通常比 Access Token 更长）。
3. 复制 Refresh Token。不要发给任何第三方上传站点。
4. **不要提交** token 到 git。只放进本机 `.env`。

Access Token 几小时就会过期；本服务用 refresh token 向 `https://auth.tesla.com/oauth2/v3/token` 换新 access token（`client_id=ownerapi`，与 teslapy 相同）。中国区账号把 `TESLA_SSO_BASE_URL` 改成 `https://auth.tesla.cn/`。

## 配置与启动

```bash
cd tesla-readonly
cp .env.example .env
# 编辑 .env，填入 TESLA_REFRESH_TOKEN=...
docker compose up -d --build
```

没有真 token 时先验证脚手架：

```bash
cd tesla-readonly
TESLA_MOCK=1 docker compose up -d --build
curl -s localhost:8080/health
curl -s localhost:8080/vehicles/1001/charge
```

不用 Docker、本机用 uv：

```bash
cd tesla-readonly
uv sync --extra dev
export TESLA_MOCK=1
uv run tesla-readonly
```

### 环境变量

| 变量 | 说明 |
| --- | --- |
| `TESLA_REFRESH_TOKEN` | Auth for Tesla 的 refresh token |
| `TESLA_MOCK` | `1` 时写入内置样例，不访问 Tesla |
| `TESLA_POLL_SECONDS` | 轮询间隔，默认 120 |
| `TESLA_SSO_BASE_URL` | 默认 `https://auth.tesla.com/` |
| `TESLA_OWNER_API_BASE` | 默认 `https://owner-api.teslamotors.com/` |
| `HTTP_PORT` | 宿主机端口，默认 8080 |
| `DATA_DIR` | 容器内默认 `/data` |

Tesla 若轮换 refresh token，新值只写在数据卷的 SQLite `meta` 表里，**不会回写 `.env`**。

## 启动后能看到什么

只读 HTTP（默认 `http://localhost:8080`）：

| 路径 | 数据 |
| --- | --- |
| `GET /health` | 运行状态、是否只读、上次成功/错误 |
| `GET /latest` 或 `GET /vehicles` | 最近一轮全部车辆快照 |
| `GET /vehicles/{id}` | 单车合并后的列表字段 + 遥测 |
| `GET /vehicles/{id}/charge` 或 `/battery` | `charge_state`（电量、续航、充电状态） |
| `GET /vehicles/{id}/drive` 或 `/location` | `drive_state`（经纬度、档位、车速） |
| `GET /vehicles/{id}/climate` | `climate_state`（内外温、空调是否开） |
| `GET /vehicles/{id}/vehicle` | `vehicle_state`（里程、锁定、版本） |
| `GET /snapshots?limit=20` | SQLite 历史快照 |

`POST` / `PUT` / `DELETE` 一律 405。

落盘：

- `data/latest.json` — 最近一轮 JSON
- `data/telemetry.sqlite` — 表 `snapshots`、`meta`

上游只读 Owner API（本服务会打的）：

1. `POST /oauth2/v3/token` — 换 access token
2. `GET /api/1/vehicles` — 车辆列表与 `state`
3. `GET /api/1/vehicles/{id}/vehicle_data?endpoints=location_data;charge_state;climate_state;vehicle_state;gui_settings;vehicle_config;drive_state`

无凭证探测到的公开错误形态（2026-09）：

- token：`401` `{"error":"login_required","error_description":"The refresh_token is invalid"}`
- vehicles：`401`，`WWW-Authenticate: Bearer ... error="invalid_token"`，空 body

## 开发测试

```bash
cd tesla-readonly
uv sync --extra dev
uv run pytest
```

## 安全

- `.env` 已在 `.gitignore` 中。
- 不要把 refresh token 贴到 issue、聊天或第三方「token 生成网站」。
- 本栈没有车辆控制 API，也不包含 TeslaMate（其 Web UI 需要手工贴 token）。
