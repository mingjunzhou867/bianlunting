# Debate Persistence and Retrieval

这个仓库实现的是一个面向补贴资格认定场景的多 Agent 辩论系统。当前里程碑的重点已经从“只做实时辩论”推进到了“把完成后的辩论会话完整保存、可按需读取、并在前端历史区展示”。

## 当前能力

- `POST /api/debate`：返回一次完整辩论结果
- `POST /api/debate_stream`：以 SSE 形式返回实时辩论过程
- `GET /api/debates?id_card=...`：按身份证号读取历史会话摘要列表
- `GET /api/debates/{session_id}`：按会话 ID 读取保存快照
- 前端左侧栏可浏览当前 `id_card` 的历史会话，中间区复用同一套会话详情渲染

## 先看哪里

- 保存/读取/历史 UI 的完整说明： [saved-session-history.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/docs/saved-session-history.md)
- 当前规划与阶段状态：
  - [.planning/PROJECT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/PROJECT.md)
  - [.planning/ROADMAP.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/ROADMAP.md)
  - [.planning/STATE.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/STATE.md)

## 本地启动前提

历史会话功能依赖新的 MySQL 表结构已经落库。至少要先执行：

1. [mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
2. 如果需要演示数据，再执行 [personas_mock.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/mock_data/personas_mock.sql)

注意：

- `mysql_ddl.sql` 当前是破坏性重建脚本，会先 `DROP TABLE`
- `personas_mock.sql` 会清空并重灌 mock 数据，不适合直接跑到保留业务数据的库

## 常用验证命令

后端测试：

```powershell
C:\Users\afrangry\anaconda3\envs\desheng\python.exe -m unittest tests.test_debate tests.test_persistence_contract tests.test_retrieval_api
```

前端轻量 smoke 测试：

```powershell
npm.cmd --prefix frontend run test
```

前端生产构建：

```powershell
npm.cmd --prefix frontend run build
```

## 说明

- 当前阶段不包含历史数据访问控制和保留策略
- 前端构建目前可通过，但 Vite 仍有大包 warning，已作为已知风险记录在文档中
