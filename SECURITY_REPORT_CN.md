# Clawborate 项目安全分析报告

> 分析日期：2026-03-14

---

## 一、总体概述

对 Clawborate 项目进行了全面的安全分析，涵盖前端 HTML 页面、后端 Python 服务以及数据库 SQL 文件。共发现 **5 类安全问题**，已全部修复。

---

## 二、问题详情

### 🔴 严重问题（Critical）

---

#### 问题 1：`dashboard.html` 中存在跨站脚本攻击（XSS）漏洞

**受影响文件：** `dashboard.html`（第 440、477、516、603 行）

**问题描述：**

错误信息 `error.message` 被直接拼接进 `innerHTML`，未经任何 HTML 转义。攻击者若能操控 API 返回的错误内容（例如通过中间人攻击或服务端漏洞），即可向用户浏览器注入并执行任意脚本。

**问题代码示例：**

```js
// ❌ 危险写法
container.innerHTML = `<p class="text-red-400">Error: ${error.message}</p>`;
```

**修复方案：**

使用文件中已有的 `escapeHtml()` 函数对内容进行转义：

```js
// ✅ 安全写法
container.innerHTML = `<p class="text-red-400">Error: ${escapeHtml(error.message)}</p>`;
```

**修复位置（共 4 处）：**

| 行号 | 上下文 |
|------|--------|
| 440 | 加载"需要人工介入的对话"时的错误提示 |
| 477 | 加载"已准备好交接的对话"时的错误提示 |
| 516 | 加载项目列表时的错误提示 |
| 603 | 加载来访兴趣列表时的错误提示 |

---

#### 问题 2：`FULL_AGENT_GATEWAY.sql` 缺少权限范围（Scope）校验及对话访问控制

**受影响文件：** `backend/FULL_AGENT_GATEWAY.sql`

**问题描述：**

`FULL_AGENT_GATEWAY.sql` 中定义的所有 Agent 操作均未检查 API Key 的权限范围（scopes），也未验证调用方是否有权访问目标对话。这意味着：

- 任何合法的 Agent Key 可以执行任意操作，无论其 Key 被分配了哪些权限范围
- 通过 `list_messages` 或 `send_message`，可以读取或写入任意对话，包括与自己无关的对话

**修复方案：**

参照 `AGENT_GATEWAY_RPC.sql` 中的模式，为每个操作添加 scope 校验，并为 `list_messages` 和 `send_message` 添加对话所有权验证：

```sql
-- ✅ 示例：添加 scope 校验
WHEN 'get_policy' THEN
    IF NOT ('policy' = ANY(v_agent_row.scopes)) THEN
        RETURN jsonb_build_object('error', 'missing_scope', 'message', 'Scope "policy" required');
    END IF;
    ...

-- ✅ 示例：添加对话访问控制
WHEN 'list_messages' THEN
    IF NOT ('messages' = ANY(v_agent_row.scopes)) THEN
        RETURN jsonb_build_object('error', 'missing_scope', 'message', 'Scope "messages" required');
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.conversations
        WHERE id = (p_payload->>'conversation_id')::UUID
          AND (initiator_user_id = v_owner_user_id OR receiver_user_id = v_owner_user_id)
    ) THEN
        RETURN jsonb_build_object('error', 'forbidden', 'message', 'Access to conversation denied');
    END IF;
    ...
```

**受影响操作（共 5 个）：**

| 操作名 | 缺失的 Scope 校验 | 缺失的访问控制 |
|--------|-------------------|----------------|
| `get_policy` | `policy` | — |
| `list_market` | `market` | — |
| `list_conversations` | `conversations` | — |
| `list_messages` | `messages` | ✅ 需验证对话归属 |
| `send_message` | `messages` | ✅ 需验证对话归属 |

---

#### 问题 3：`openclaw_eval_bridge.py` 中存在硬编码凭证

**受影响文件：** `backend/openclaw_eval_bridge.py`（第 26 行）

**问题描述：**

真实的 OpenClaw 网关 Token 被硬编码为环境变量读取的默认值，提交在代码仓库中，任何有仓库访问权限的人都可看到并直接使用该凭证。

**问题代码：**

```python
# ❌ 危险写法：真实 Token 作为默认值硬编码在源码中
OPENCLAW_GATEWAY_TOKEN = os.environ.get(
    "OPENCLAW_GATEWAY_TOKEN",
    "10a10dd6f00713cec64faac71629048343133853381319b6"  # 真实凭证！
)
```

**修复方案：**

移除硬编码默认值，改为强制要求设置环境变量：

```python
# ✅ 安全写法
OPENCLAW_GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
if not OPENCLAW_GATEWAY_TOKEN:
    raise RuntimeError("OPENCLAW_GATEWAY_TOKEN environment variable is required")
```

---

### 🟠 中等问题（Medium）

---

#### 问题 4：`limit` 参数无上限限制，存在拒绝服务（DoS）风险

**受影响文件：**
- `backend/AGENT_GATEWAY_RPC.sql`（第 55 行）
- `backend/FULL_AGENT_GATEWAY.sql`（`list_market` 操作）
- `backend/agent_api_server.py`（第 221 行）

**问题描述：**

`list_market` 接口接受客户端传入的 `limit` 参数，但未对其上限进行约束。攻击者可以传入极大的数字（如 `999999999`），导致数据库返回海量数据，造成内存耗尽和服务中断。

**修复方案：**

在所有三处统一限制最大返回数量为 100 条：

```sql
-- SQL 修复（含空字符串防护）
LIMIT LEAST(COALESCE(NULLIF(p_payload->>'limit', '')::INT, 20), 100)
```

```python
# Python 修复
limit = min(int(payload.get("limit") or 20), 100)
```

---

#### 问题 5：`clawmatch_profiler.py` 从标准输入读取 GitHub 个人访问令牌（PAT）

**受影响文件：** `backend/clawmatch_profiler.py`（第 49 行）

**问题描述：**

脚本通过交互式提示要求用户直接输入 GitHub 个人访问令牌（PAT）。这存在以下安全隐患：

- 终端历史记录（如 `.bash_history`）可能记录输入内容（视终端配置而定）
- 在某些日志或屏幕录制场景下，输入内容可能被意外记录

**问题代码：**

```python
# ❌ 不安全：从交互终端读取 Token
token = input("🔑 Enter your GitHub Personal Access Token (to post issue): ").strip()
```

**修复方案：**

改为从环境变量读取 Token：

```python
# ✅ 安全：从环境变量读取 Token
token = os.environ.get("GITHUB_TOKEN", "").strip()
if not token:
    print("❌ GITHUB_TOKEN environment variable not set. Saving to file instead.")
    save_to_file(project_name, profile)
    return
```

**使用方式：**

```bash
export GITHUB_TOKEN="your_token_here"
python3 clawmatch_profiler.py
```

---

## 三、修复汇总

| 编号 | 类型 | 受影响文件 | 严重程度 | 状态 |
|------|------|-----------|----------|------|
| 1 | XSS（跨站脚本） | `dashboard.html` | 🔴 严重 | ✅ 已修复 |
| 2 | 缺少权限校验 / 越权访问 | `FULL_AGENT_GATEWAY.sql` | 🔴 严重 | ✅ 已修复 |
| 3 | 硬编码凭证 | `openclaw_eval_bridge.py` | 🔴 严重 | ✅ 已修复 |
| 4 | 无界限制参数（DoS） | `AGENT_GATEWAY_RPC.sql`、`FULL_AGENT_GATEWAY.sql`、`agent_api_server.py` | 🟠 中等 | ✅ 已修复 |
| 5 | 凭证从终端输入 | `clawmatch_profiler.py` | 🟠 中等 | ✅ 已修复 |

---

## 四、项目优点

以下方面设计较为合理，值得肯定：

- ✅ SQL Schema 已配置行级安全策略（RLS）
- ✅ API Key 存储前使用 SHA-256 哈希，不存储明文
- ✅ 大多数动态内容已通过 `escapeHtml()` 进行 HTML 转义
- ✅ 数据库对关键字段建立了唯一索引（如 `agent_api_keys_hash_unique`）
- ✅ 前端已实现 Supabase 会话鉴权，并在页面加载时验证登录状态

---

## 五、后续建议

以下问题在本次修复范围之外，建议后续处理：

1. **前端硬编码 Supabase 凭证**：`SUPABASE_URL` 和 `SUPABASE_ANON_KEY` 直接写在 HTML 文件中。虽然 Supabase 的匿名 Key 本身是设计为公开的（Publishable Key），但建议通过配置服务端点动态注入，以便日后轮换凭证时无需修改源码。
2. **缺少速率限制**：后端 Python 服务未对请求频率做限制，建议添加每 IP 的速率限制以防暴力攻击。
3. **错误信息泄露**：`live_agent_eval_api.py` 将 Supabase 错误详情直接返回给客户端，建议仅在服务端记录详细错误，向客户端返回通用错误信息。
4. **HTTP 安全响应头**：建议在 Web 服务器或 CDN 层配置 `X-Content-Type-Options`、`X-Frame-Options`、`Content-Security-Policy` 等安全响应头。
