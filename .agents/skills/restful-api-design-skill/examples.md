# 示例：RESTful API 设计 / 检查 / 生成

## 示例 1：define 模式 —— 用户管理 API

### 输入提示词

```markdown
模式：define
API 名称：用户管理 API
业务目标：提供后台用户列表查询、用户详情查询、创建用户、更新用户状态能力
资源模型：用户、角色
核心操作：分页查询用户、查看用户详情、创建用户、冻结/解冻用户
鉴权方式：Bearer Token
分页/过滤/排序要求：支持分页，按用户名和状态过滤，支持创建时间倒序
版本策略：v1
约束条件：需要保留审计字段，禁止返回密码摘要
```

### 期望输出结构（节选）

````markdown
## Part 1. Markdown API 设计文档

# API Design Doc

## 1. 概述
- API 名称：用户管理 API
- 业务目标：为后台运营提供用户管理能力
- 范围：用户查询、详情、创建、状态更新
- 非范围：用户登录、密码重置、角色权限配置

## 2. 设计规范摘要
- 资源命名规则：使用 `/users` 作为主资源集合
- HTTP Method 使用规则：查询使用 GET，创建使用 POST，状态更新使用 PATCH
- 状态码策略：查询成功 200，创建成功 201，不存在 404，语义校验失败 422
- 错误响应策略：统一返回 `code/message/details/requestId`

## 3. 资源模型
| 资源 | 描述 | 标识符 | 关系 |
|---|---|---|---|
| User | 后台管理的用户对象 | userId | 可关联多个 Role |
| Role | 用户角色 | roleId | 被 User 引用 |

## 4. 接口清单
| 名称 | Method | Path | 目的 |
|---|---|---|---|
| 用户列表 | GET | /api/v1/users | 分页查询用户 |
| 用户详情 | GET | /api/v1/users/{userId} | 查询单个用户 |
| 创建用户 | POST | /api/v1/users | 创建用户 |
| 更新用户状态 | PATCH | /api/v1/users/{userId}/status | 冻结或解冻用户 |

## Part 2. OpenAPI 3.1 草案
```yaml
openapi: 3.1.0
info:
  title: 用户管理 API
  version: 1.0.0
paths:
  /api/v1/users:
    get:
      summary: 分页查询用户
    post:
      summary: 创建用户
  /api/v1/users/{userId}:
    get:
      summary: 查询用户详情
  /api/v1/users/{userId}/status:
    patch:
      summary: 更新用户状态
```

## Part 3. 待确认项
- Q1：状态更新是否需要记录操作原因
- Q2：用户名是否要求全局唯一且大小写不敏感
```

### 关键质量点

- 是否先定义资源模型，再设计 endpoint
- 是否同时输出 Markdown 文档与 OpenAPI 草案
- 是否明确排除敏感字段返回

---

## 示例 2：check 模式 —— 文档与代码对照检查

### 输入提示词

```markdown
模式：check
API 名称：订单查询 API
现有规范路径：docs/order-api.md
现有代码路径：src/routes/order.ts
现有文档路径：docs/order-api.md
约束条件：重点检查 RESTful 命名、状态码、错误响应结构、分页字段一致性
```

### 期望输出结构（节选）

````markdown
## Part 1. 检查摘要
- 规范自检：存在 2 个 RESTful 命名问题
- 代码对照：存在 3 处接口契约不一致
- 文档对照：存在 2 处字段定义不一致

## Part 2. 规范自检结果
| ID | 类型 | 严重级别 | 位置/证据 | 问题描述 | 影响 | 修正建议 |
|---|---|---|---|---|---|---|
| F-01 | 规范问题 | 中 | `GET /api/v1/getOrders` | 使用动词型路径，不符合资源导向命名 | 增加接口理解成本 | 改为 `GET /api/v1/orders` |

## Part 3. 代码对照结果
| ID | 类型 | 严重级别 | 位置/证据 | 问题描述 | 影响 | 修正建议 |
|---|---|---|---|---|---|---|
| C-01 | 代码不一致 | 高 | `src/routes/order.ts` 中返回 201 | 查询接口返回 201，与文档定义的 200 不一致 | 调用方可能误判语义 | 改为 200 |

## Part 4. 文档对照结果
| ID | 类型 | 严重级别 | 位置/证据 | 问题描述 | 影响 | 修正建议 |
|---|---|---|---|---|---|---|
| D-01 | 文档不一致 | 中 | `docs/order-api.md` | 文档写的是 `pageIndex/pageSize`，代码使用 `page/pageSize` | 调用方可能传错参数 | 统一为 `page/pageSize` |

## Part 5. 修正建议 / 建议修正版规范
- Endpoint 调整：`GET /api/v1/getOrders` -> `GET /api/v1/orders`
- 状态码调整：查询成功统一返回 200
- 错误模型调整：统一补充 `requestId`
- 文档调整：统一分页参数命名为 `page/pageSize`
```

### 关键质量点

- 是否只对用户提供的材料做定向检查
- 是否同时给出问题、证据和修正建议
- 是否区分规范问题、代码不一致、文档不一致

---

## 示例 3：generate 模式 —— 订单 API 全流程草案

### 输入提示词

```markdown
模式：generate
API 名称：订单 API
业务目标：支持订单创建、订单详情查询、订单列表查询、取消订单
资源模型：订单、订单项
核心操作：创建订单、查询订单详情、分页查询订单、取消订单
鉴权方式：Bearer Token
分页/过滤/排序要求：订单列表支持分页，按订单状态过滤，按创建时间倒序
技术栈：FastAPI
约束条件：取消订单仅允许待支付状态；需要保留操作审计信息
```

### 期望输出结构（节选）

````markdown
## Part 1. Markdown API 设计文档
- 定义 `/api/v1/orders`、`/api/v1/orders/{orderId}`、`/api/v1/orders/{orderId}/cancellations`
- 明确订单状态流转与取消约束

## Part 2. OpenAPI 3.1 草案
```yaml
openapi: 3.1.0
paths:
  /api/v1/orders:
    get:
      summary: 分页查询订单
    post:
      summary: 创建订单
  /api/v1/orders/{orderId}:
    get:
      summary: 查询订单详情
  /api/v1/orders/{orderId}/cancellations:
    post:
      summary: 创建取消申请
```

## Part 3. 请求/响应示例
- 创建订单请求示例
- 创建订单响应示例
- 取消订单失败响应示例

## Part 4. 测试用例草案
- 成功创建订单
- 缺少必填字段时返回 422
- 未认证时返回 401
- 取消已支付订单时返回 409
- 重复取消订单的幂等性验证

## Part 5. 服务端骨架草案
- `routes/orders.py`
- `controllers/order_controller.py`
- `services/order_service.py`
- `schemas/order_schema.py`
- `middlewares/auth.py`
- `tests/test_orders.py`

## Part 6. 假设与待确认项
- Q1：取消订单是否需要退款联动
- Q2：订单列表是否需要按用户隔离查询
```

### 关键质量点

- 是否在生成前先完成规范化设计
- 是否同时给出示例、测试草案和服务端骨架
- 是否把业务假设单独标出来
