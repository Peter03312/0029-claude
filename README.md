# 锁线前配帖核验站

锁线装订前，将**期望配帖清单**与书芯**实扫帖标**做序列对齐核验：错帖、漏帖、多帖逐行定位，给出确定性的核验结果与可下载的 JSON 报告。

* 前端：React 18 + TypeScript + Vite
* 后端：FastAPI（显式契约校验 + 动态规划对齐）
* 联调：Docker Compose（nginx 托管前端静态资源并反代 `/api` 到 FastAPI）
* 测试：Vitest（前端）+ Pytest（后端），由一次性 `verify` 服务统一运行

## 目录结构

```
.
├── compose.yaml            # web / backend / 一次性 verify 三个服务
├── Dockerfile.verify       # 同时含 Node 与 Python 的验收镜像
├── docker/verify-entrypoint.sh
├── backend/                # FastAPI：契约校验 + DP 对齐 + 报告
│   ├── app/{contract,alignment,report,main}.py
│   └── tests/              # Pytest（31 项，含四个验收场景）
├── frontend/               # React/TS：双列结果、首异常定位、筛选、报告下载
│   └── src/（Vitest 14 项）
└── examples/               # 期望清单 / 三种实扫 / 非法清单示例
```

## 快速开始（Docker Compose）

```bash
# 默认宿主端口 8080
docker compose up --build

# 覆盖宿主端口（WEB_PORT 可覆盖宿主端口，容器内固定 80）
WEB_PORT=9090 docker compose up --build
# 或复制 .env.example 为 .env 后修改 WEB_PORT
```

打开 http://localhost:8080 ：

1. 在左、右两个导入区分别选择**期望清单 JSON** 与**实扫 JSON**；
2. 点击「开始核验」；
3. 结果页双列显示「期望槽位 / 期望帖标 ↔ 实扫帖标 / 实扫序号」，首个红色异常行自动滚动定位，也可用横幅中的「定位」按钮再次跳转；
4. 用「异常筛选」下拉在 全部 / 仅异常 / 仅错帖 / 仅漏帖 / 仅多帖 间切换；
5. 点击「下载 JSON 报告」保存结构化报告（文件名体现首个异常的槽位与实扫序号）。

## 一次性验收（Vitest + Pytest）

```bash
docker compose build verify
docker compose run --rm verify
```

`verify` 是一次性任务，顺序执行：前端类型检查与构建 → `vitest run` → `pytest`，任一步失败即以非零码退出，不发布端口、非常驻。

### 不使用 Docker 的本地运行

```bash
# 后端
python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000

# 前端（Vite 开发服务器把 /api 代理到 localhost:8000）
cd frontend && npm install && npm run dev

# 测试
(cd frontend && npx vitest run)
(cd backend && python3 -m pytest)
```

## 输入文件契约

两个文件各不超过 **400 项**，编码 UTF-8。

### 期望清单（expected_file）

对象数组，每项**仅含**：

* `slot`：整数；长度为 n 时，第 i 项（i 从 1 起）的 `slot` 必须恰为 `i`。数组顺序即对齐顺序，任何重复、跳号、错位或超出 `1..n` 均非法；
* `mark`：非空字符串。

```json
[ { "slot": 1, "mark": "帖1" }, { "slot": 2, "mark": "帖2" } ]
```

### 实扫（actual_file）

书芯自上而下的非空字符串数组：

```json
["帖1", "帖2"]
```

帖标按 **JSON 解码后的码点原样比较**，不做大小写折叠、空白修剪或 Unicode 规范化。例如全角 `Ａ`(U+FF21) ≠ `A`(U+0041)，预组合 `é`(U+00E9) ≠ 分解形式 `e`+U+0301。

任一文件解析失败（非法 JSON / 非 UTF-8 / 嵌套层数过深）或违约（结构、类型、空值、超量、slot 不对齐等）时：

* 错误显示在**对应导入区**（响应体带 `source: "expected" | "actual"` 与错误码；深嵌套返回 `nesting_too_deep`，同样归入对应导入区，不会变成通用请求失败）；
* **整次拒绝**：不产生任何结果行，也没有报告与下载入口。

## 对齐语义

编辑距离动态规划，插入（多帖）、删除（漏帖）、替换（错帖）代价均为 1：

* **相同项必须匹配**（沿对角代价 0，且相同帖标绝不允许被当作替换）；
* 采用标准前缀 DP（自左向右、自上而下填表），回溯**从表末端 `(n, m)` 开始**沿前驱回到 `(0, 0)`，逆序收集后翻转为自上而下的行序；
* 回溯到同一格若多条路径代价相同，按规格依次优先 **替换 → 缺失（漏帖）→ 额外（多帖）**，因此结果行完全确定、可复现；
* **重复标定位**：帖标段出现重复（期望清单里的重复 `mark`，或实扫重复扫入）时，末端回溯把相等匹配锚在重复段的**下边界**，多/漏的一份暴露在重复段**上边界**——即更靠近书芯上方的实际拆书位。重复段再长，首个异常也不会被推移到段的下端；
* 每行含 `slot`（期望槽位，多帖行为 `null`）、`scan_index`（实扫序号，1 起，漏帖行为 `null`）、两侧帖标与 `status`（`match/replace/missing/extra`）。

### 报告 JSON

```json
{
  "summary": { "expected_count": 3, "actual_count": 4, "match": 2, "replace": 1,
               "missing": 0, "extra": 1, "anomaly": 2, "edit_cost": 2, "passed": false },
  "first_anomaly": { "row_index": 1, "slot": 2, "scan_index": 2, "status": "replace",
                     "expected_mark": "B", "actual_mark": "X" },
  "rows": [ /* 逐行结果，顺序即书芯自上而下 */ ]
}
```

报告无时间戳等易变量，同输入两次请求结果逐字节一致。`first_anomaly` 可直接把书芯拆到出错书帖（期望槽位 + 实扫第几件）。

## 验收场景（测试覆盖）

| 场景 | 示例 | 期望结果 |
| --- | --- | --- |
| 完全一致 | `examples/actual-perfect.json` | `passed: true`，全部 match |
| 重复标漏帖 | `examples/expected-duplicate-mark.json` + `actual-duplicate-missing.json`（槽位 2、3 同为 B，实扫少一件 B） | 1 行 missing，首异常定位在重复段**上边界**槽位 2（而非槽位 3），拆书位不上移 |
| 实扫重复多帖 | `examples/expected-abc.json` + `actual-duplicate-extra.json`（书芯上方多扫一件 A） | 1 行 extra，首异常为实扫第 1 件（重复段上边界），A 锚在实扫第 2 件 |
| 同次错帖 + 末尾多帖 | `examples/actual-wrong-and-extra.json` | 1 行 replace + 1 行 extra，首异常为错帖行 |
| 坏文件 / 违约 | `examples/expected-bad-slot.json`，或深嵌套 JSON | 422，错误归入对应导入区（深嵌套为 `nesting_too_deep`），整单拒绝 |

后端：`backend/tests/test_alignment.py`（含与独立 Levenshtein 实现的交叉校验、随机确定性、码点原样比较）、`backend/tests/test_api.py`（端到端 + 违约矩阵）。
前端：`frontend/src/App.test.tsx`（四个验收场景的页面行为、筛选、错误归属、报告下载）、`frontend/src/lib/report.test.ts`。

## API 速览

`POST /api/verify`（`multipart/form-data`，字段 `expected_file`、`actual_file`）

* `200` → `{ "ok": true, "report": { … } }`
* `422` → `{ "ok": false, "source": "expected" | "actual", "error": { "code", "message" } }`

`GET /health` → `{ "status": "ok" }`
