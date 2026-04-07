# Saved Session History Guide

## 1. 这份文档解决什么问题

这份文档是“已保存辩论会话”能力的维护入口，目标是让后续开发者不用翻 planning 或源码，也能快速理解下面这条链路：

`save -> retrieve -> render`

也就是：

1. 实时或一次性辩论完成后，后端如何保存
2. 后端如何按 `id_card` / `session_id` 读取
3. 前端历史区如何依赖这些保存结果进行展示

## 2. 数据库前提

历史会话功能依赖新的数据库结构，核心脚本是：

- [mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
- [personas_mock.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/mock_data/personas_mock.sql)

推荐执行顺序：

1. 先执行 `data/schema/mysql_ddl.sql`
2. 需要演示数据时，再执行 `data/mock_data/personas_mock.sql`

重要说明：

- `mysql_ddl.sql` 当前是破坏性脚本，会先 `DROP TABLE`
- `personas_mock.sql` 会清空现有 mock/演示数据后再插入新数据
- 如果目标库没有先应用新 DDL，`GET /api/debates`、`GET /api/debates/{session_id}` 和前端历史列表都会失败

## 3. 存储模型

保存逻辑集中在：

- [debate_persistence.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_persistence.py)
- [debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py)

### 3.1 `debate_session`

`debate_session` 是一场成功完成辩论的主记录表，用来支撑：

- 按 `id_card` 的历史摘要列表
- 按 `session_id` 的详情读取
- 一次性保存完整快照

关键字段包括：

- `session_id`
- `id_card`
- `status`
- `source_endpoint`
- `final_conclusion`
- `final_stance`
- `consensus_rate`
- `is_consensus_reached`
- `rounds_taken`
- `evidence_count`
- `agent_count`
- `started_at`
- `completed_at`
- `snapshot_payload`

其中 `snapshot_payload` 是完整 JSON 快照，详情读取优先依赖它，而不是再回表重建每一段视图数据。

### 3.2 `agent_debate_log`

`agent_debate_log` 用来保留逐轮、逐 Agent 的结构化判断记录，方便未来扩展更细的详情页或审计视图。

关键字段包括：

- `session_id`
- `id_card`
- `debate_round`
- `agent_id`
- `agent_role`
- `conclusion`
- `stance`
- `confidence`
- `evidence_refs`
- `reasoning`
- `dissent_points`
- `key_finding`
- `round_majority_stance`
- `round_consensus_rate`
- `round_is_consensus_reached`

## 4. 后端 API 契约

路由定义在：

- [main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)

### 4.1 `POST /api/debate`

返回一次完整辩论结果，并在成功完成后写入历史会话。

### 4.2 `POST /api/debate_stream`

以 SSE 流式返回证据、逐 Agent 判断和最终结论，并在成功完成后写入历史会话。

### 4.3 `GET /api/debates?id_card=...`

返回某个身份证号对应的历史摘要列表。第一版约定：

- 只返回 summary-only 字段
- 按 `completed_at` 倒序
- 查不到时返回空数组

### 4.4 `GET /api/debates/{session_id}`

返回一场历史会话的完整快照详情。第一版约定：

- 以 `snapshot_payload` 为主
- 查不到时返回 404

## 5. 前端如何消费这些数据

前端入口在：

- [App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue)
- [HistorySessionList.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/components/HistorySessionList.vue)
- [DebateSessionView.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/components/DebateSessionView.vue)
- [sessionState.js](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/sessionState.js)

当前交互约定：

1. 输入 `id_card` 后，实时流继续走 `/api/debate_stream`
2. 左侧历史列表走 `/api/debates?id_card=...`
3. 点击某条历史记录后，详情走 `/api/debates/{session_id}`
4. 中间区域使用同一套渲染，同时承接 live session 和 saved session
5. 实时流完成后，前端会刷新当前 `id_card` 的历史列表

## 6. 自动化验证

### 6.1 后端

重点测试文件：

- [test_debate.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_debate.py)
- [test_persistence_contract.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_persistence_contract.py)
- [test_retrieval_api.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_retrieval_api.py)

建议命令：

```powershell
C:\Users\afrangry\anaconda3\envs\desheng\python.exe -m unittest tests.test_debate tests.test_persistence_contract tests.test_retrieval_api
```

### 6.2 前端

Phase 3 新增的是轻量 smoke 测试，不是完整组件测试平台。它主要验证历史/实时状态机里最关键的纯逻辑：

- 空白会话初始化
- 历史详情标准化
- 流式事件更新
- 历史刷新后的选中策略

测试命令：

```powershell
npm.cmd --prefix frontend run test
```

构建命令：

```powershell
npm.cmd --prefix frontend run build
```

## 7. 已知风险与当前处理方式

### 7.1 DDL 依赖

这是当前最容易踩坑的点。代码已经按新结构实现，但如果目标 MySQL 还是旧表结构，读取 API 和历史 UI 都无法正常工作。

当前处理方式：文档明确要求先执行新的 schema 脚本。

### 7.2 Mock 重置是破坏性的

`personas_mock.sql` 不只是插入数据，它会先删表内现有记录再灌入演示数据。

当前处理方式：仅在本地 demo、联调和演示环境使用。

### 7.3 前端构建 chunk warning

当前 `npm run build` 可以通过，但 Vite 仍会提示大包 warning。

当前处理方式：

- 本阶段先明确记录为已知事项
- 不把它升级成单独的性能优化项目
- 只有在后续确实需要时，再评估 chunk 拆分或按需加载

## 8. 后续扩展时的建议

如果后面要继续往历史能力上扩展，建议优先考虑这些方向：

- 更丰富的历史筛选或 recent 视图
- 审计/权限控制
- 历史详情页的更细粒度回放
- retention / cleanup 策略

这些都不属于当前里程碑，但都建立在现有 save/read/render 契约已经稳定的前提上。
