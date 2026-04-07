# Frontend History UI

前端目前不是一个独立的“历史系统”，而是在现有单页应用里，把实时辩论和已保存会话统一渲染到同一个中心区域。

## 当前入口

- 实时运行：`POST /api/debate_stream`
- 历史摘要列表：`GET /api/debates?id_card=...`
- 历史详情：`GET /api/debates/{session_id}`

核心文件：

- [App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue)
- [DebateSessionView.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/components/DebateSessionView.vue)
- [HistorySessionList.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/components/HistorySessionList.vue)
- [sessionState.js](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/sessionState.js)

## 开发前提

如果后端数据库没有先应用新的 schema，左侧历史列表和历史详情都会失效。完整前置条件见：

- [saved-session-history.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/docs/saved-session-history.md)

## 常用命令

安装依赖后可以使用：

```powershell
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run build
```

其中：

- `run test` 是 Phase 3 新增的轻量 smoke 测试，覆盖历史/实时状态机的关键纯逻辑
- `run build` 用于验证 Vue SFC 和生产构建路径仍然正常

## 已知事项

- 当前 smoke 测试刻意保持轻量，没有引入完整的组件测试栈
- 构建目前能通过，但仍存在 Vite 的大包 warning；这已经被记录为已知风险，而不是本阶段的性能专项
