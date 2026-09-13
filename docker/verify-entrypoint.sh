#!/usr/bin/env bash
# 一次性验收：依次运行前端 Vitest（含类型检查构建）与后端 Pytest。
# 任一步失败立即以该步骤退出码退出，compose 的 verify 任务随之失败。
set -euo pipefail

echo "==> [1/3] 前端类型检查 + 生产构建"
( cd frontend && npx tsc --noEmit && npx vite build )

echo "==> [2/3] Vitest（前端单元 / 组件测试）"
( cd frontend && npx vitest run )

echo "==> [3/3] Pytest（后端对齐算法 / 契约 / API 验收）"
( cd backend && python3 -m pytest )

echo "==> 全部验收通过"
