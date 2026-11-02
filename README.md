# Budget-Aware Python Coding Agent

课程项目：[IERG4320 / IEMS5726A Data Science in Practice](https://github.com/Koukie23/budget_aware_python_agent)

在预算内完成 Python 单函数编写：本地微调模型负责生成和修复，测试失败且预算允许时再升级到 DeepSeek。修复与升级由规则控制，不训练路由模型。界面为英文。

设计细节见 [`budget_aware_python_agent_plan.md`](budget_aware_python_agent_plan.md)。

## 系统做什么

用户提供需求、函数签名、反馈测试、执行偏好和强模型预算。Agent 最多调用模型三次：

1. 本地 LoRA 生成代码  
2. 对反馈测试真实执行  
3. 失败则用同一本地模型按报错修复一次  
4. 仍失败且偏好允许、预算够用时，调用 DeepSeek  
5. 网页展示代码版本、测试结果、轨迹、token 和费用  

测试通过只表示当前反馈测试通过，不保证对所有输入正确。

## 架构

```
浏览器 (Vite :5173)
    → Express + PostgreSQL (:3000)
        → FastAPI Agent (:8000)
            → 本地 CodeGen-350M + LoRA
            → DeepSeek API（升级）
            → subprocess / Docker 跑测试
```

| 组件 | 路径 | 说明 |
| --- | --- | --- |
| 前端 | `frontend/` | React + TypeScript + Vite + Ant Design |
| 后端 | `backend/` | Express + TypeScript，任务与轨迹入库 |
| Agent | `agent/`、`agent_service/` | 状态机、提示、抽取、测试执行 |
| 训练 | `training/`、`scripts/` | LoRA 训练与 pass@1 评测 |
| 数据 | `data/` | MBPP 官方划分后的 jsonl |

## 策略与预算

| 偏好 | 调用顺序 |
| --- | --- |
| Save cost (`cheap`) | 本地生成 → 本地修复。不调用 DeepSeek |
| Balanced | 本地生成 → 本地修复 → DeepSeek |
| Quality first | 本地生成 → DeepSeek（跳过本地修复） |

只有强模型按 token 计费。本地推理费用记为 0。默认预算 `$0.05`。当前强模型为 `deepseek-flash`，思考模式关闭。

## 模型与评测

基座：`Salesforce/codegen-350M-mono`。在完整 MBPP 训练集（task_id 601–974，374 条）上做 LoRA，验证 / 测试用 sanitized 同 ID 范围（43 / 257）。

贪婪解码，prompt 为需求 + 签名 + 反馈测试，只对补全部分算 loss。

| 模型 | 验证集 pass@1 | 测试集 pass@1 |
| --- | --- | --- |
| E1 基座 | 12/43 = 27.9% | 57/257 = 22.2% |
| E2-v1 LoRA（已弃用） | 18.6% | 10.9% |
| E2-v2 LoRA（当前接入） | **14/43 = 32.6%** | **59/257 = 23.0%** |

v2 权重默认路径：`models/codegen350m_lora_v2/best`（仓库不收录权重，需本地训练或自行放置）。350M 单独解题能力有限，网页四个示例里本地模型通常只能过一部分；Balanced / Quality first 才会升级。

## 本地运行

需要：Python 3.11、Node.js、PostgreSQL（库名 `budget_agent`）、本机 LoRA 权重。Apple Silicon 上用 MPS。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-train.txt
pip install fastapi uvicorn httpx peft

cp .env.example .env
# 填写 DEEPSEEK_API_KEY

cd backend && npm install && npm run db:init && npm run dev
cd frontend && npm install && npm run dev
AGENT_CLIENT=local AGENT_EXECUTOR=subprocess \
  .venv/bin/uvicorn agent_service.main:app --host 127.0.0.1 --port 8000
```

打开 http://localhost:5173/

| 变量 | 作用 |
| --- | --- |
| `DEEPSEEK_API_KEY` | 强模型，必填才能升级 |
| `DEEPSEEK_MODEL` | 默认 `deepseek-flash` |
| `AGENT_CLIENT` | `local` 或 `mock` |
| `AGENT_EXECUTOR` | `subprocess` 或 `docker` |
| `DATABASE_URL` | 默认 `postgres://localhost:5432/budget_agent` |

不要把 `.env` 提交进 git。

命令行（不经过网页）：

```bash
.venv/bin/python scripts/run_agent.py \
  --client local --preference cheap --executor subprocess --task-id 2
```

训练与评测：

```bash
.venv/bin/python scripts/build_splits.py
.venv/bin/python scripts/train_lora.py
.venv/bin/python scripts/eval_base.py --split validation --executor subprocess
.venv/bin/python scripts/eval_base.py --split test --adapter models/codegen350m_lora_v2/best --tag e2_lora_v2 --executor subprocess
```

## 安全说明

当前只适合本机演示：无登录、后端绑在 `127.0.0.1`、测试默认可用本机进程执行。不要把端口暴露到公网，否则别人可以跑你机器上的代码并消耗 DeepSeek 余额。

## 数据

MBPP（Austin et al., 2021），CC-BY-4.0。划分按官方 `task_id`：1–10 prompt，11–510 test，511–600 validation，601–974 train。原始文件说明见 `data/DATA_NOTES.md`。
