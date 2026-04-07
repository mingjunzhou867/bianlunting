# 项目开发待办清单 (Todo List)

> 项目：基于 LLM Agent 与规则推理的政务数据决策系统
> 最近更新：2026-03-24（同步实际进度）
> 开发理念：**先让数据能查、再让 Agent 能说、最后让他们能吵**
> 执行原则：自底向上，逐层搭建，每一步都可独立验证

---

## ✅ 第零阶段：业务规则与数据准备（已完成）

> 已完成的地基工作，不再需要额外投入。

- [x] 业务规则梳理 → `规则.txt`（三大核心功能、排斥条件、合理推断、精算规则）
- [x] 数据库 Schema 设计 → `data/schema/mysql_ddl.sql`（9张表，含 Agent 辩论表）
- [x] 模拟数据设计 → `data/mock_data/personas_mock.sql`（9个 Persona，5家企业）
- [x] 项目约束边界文档 → `README.md`（62条边界约束）

---

## ✅ 第一阶段：项目基础配置（已完成）

> 目标：让项目能连数据库、能调 LLM、能跑起来。

### 1.1 环境与依赖

- [x] 创建 `config/.env.example`（配置模板，支持 Nova / OpenAI / DeepSeek / Claude）
- [x] 创建实际 `config/.env` 并加入 `.gitignore`
- [x] 编写 `requirements.txt`（pymysql / sqlalchemy / openai / pydantic / loguru / rich）
- [x] `pip install -r requirements.txt` 验证依赖安装

### 1.2 项目主入口与配置加载

- [x] 创建 `config/settings.py`（统一配置加载，读取 `.env`）
- [x] 创建 `config/database.py`（数据库连接池/会话管理）
- [x] 创建 `config/llm_client.py`（LLM 调用封装，多提供商路由）
- [x] 创建 `main.py`（冒烟测试骨架）

### 1.3 数据库初始化

- [x] 建库并执行 DDL / 模拟数据导入
- [x] 验证连接和数据完整性

**✅ 阶段验收通过：** `python main.py` 输出 数据库 ✅ + LLM ✅

---

## ✅ 第二阶段：证据对象 + Text-to-SQL 取证模块（已完成）

> 目标：Agent 的所有论点必须来自数据库事实。本阶段建立"事实获取基础设施"。

### 2.1 统一证据对象定义

- [x] 创建 `evidence/evidence_model.py`，定义 `EvidenceItem`（Pydantic Model）
- [x] 同步定义 `EvidenceBundle`（某人所有证据的集合，传给 Agent 的完整输入）

### 2.2 SQL 模板库

- [x] 创建 `text2sql/sql_templates.py`，为每条规则预定义 SQL 模板（共 20 条）
  - BASIC_001~005：基础条件检查（5条）
  - EXCL_001~009：排斥条件检查（9条，含股东新旧记录对比）
  - INFER_001~002：合理推断查询（2条，含单位性质识别）
  - CALC_001~005：精算数据查询（5条，含四种情况的计算依据）
  - PROACT_001~004：主动服务查询（4条，含增员扫描、疑似人员筛选）
- [x] 按场景分组的快捷规则列表（QUALIFICATION / CALCULATION / PROACTIVE）

### 2.3 取证执行器

- [x] 创建 `text2sql/evidence_collector.py`，实现 `EvidenceCollector` 类
- [x] 自动填充 `supports_conclusion`、异常处理标注 `exec_status`

### 2.4 取证模块验证

- [x] 编写 `tests/test_evidence_collector.py`，对 9 个 Persona 分别跑全量取证
- [x] 修复 BASIC_001 特化判断逻辑（life_status + system_status 双判断）
- [x] 修复 EXCL_009 特化逻辑（无数据→不通过，有数据→交 Agent 判断）

**✅ 阶段验收通过：** `python -m tests.test_evidence_collector` EXIT:0，全部检查项通过。

---

## ✅ 第三阶段：五个异质 Agent 开发（已完成）

> 目标：让每个 Agent 都能基于证据，独立给出判断。

### 3.1 Agent 基类

- [x] 创建 `agents/base_agent.py`，封装 LLM 调用，定义统一输出结构 `AgentJudgment`
- [x] 实现 `judge(bundle)` 独立判断 + `debate_respond()` 辩论回应
- [x] 实现 `_extract_json()` 兼容畸形 JSON 降级提取
- [x] 创建 `agents/__init__.py`，提供 `create_all_agents()` 工厂函数

### 3.2 五个 Agent 的 System Prompt

- [x] `agents/agent_strict.py` — 严格合规 Agent（temperature=0.1）
- [x] `agents/agent_lenient.py` — 业务宽松 Agent（temperature=0.3）
- [x] `agents/agent_explorer.py` — 发散探索 Agent（temperature=0.5）
- [x] `agents/agent_empirical.py` — 经验归纳 Agent（temperature=0.3）
- [x] `agents/agent_auditor.py` — 审计反驳 Agent（temperature=0.2）

### 3.3 独立判断验证

- [x] 编写 `tests/test_agents.py`，对典型 Persona 让 5 个 Agent 各自独立出具判断
- [x] 非争议人物（A/B）→ 结论基本一致；争议人物（D/E）→ Agent 产生明显分歧

**✅ 阶段验收通过：** 共识度差异明显，多 Agent 分歧机制正常工作。

---

## ✅ 第四阶段：辩论编排与共识机制（已完成）

> 目标：让 Agent 们"吵起来"，并最终形成结论。

### 4.1 辩论编排器

- [x] 创建 `agents/debate_orchestrator.py`
  - Round 0 独立判断 → 检查共识（≥80% 提前结束）→ Round 1~2 交叉辩论 → 多数票决议
  - 实现平权投票（基线方案）+ 预留权重裁决接口
  - `DebateRecord` 记录每轮立场、多数派、共识率

### 4.2 辩论记录持久化（含 Schema 重构）

- [x] 重构 `data/schema/mysql_ddl.sql`：新增 `debate_session` 表（完整会话主表）
- [x] 重构 `agent_debate_log` 表（逐轮逐 Agent 结构化记录，含外键约束）
- [x] 创建 `agents/debate_persistence.py`：封装序列化、写库、读库全部逻辑
  - `persist_completed_session()` — 只保存成功完成的会话
  - `list_saved_sessions(id_card)` — 按身份证查历史摘要列表（newest-first）
  - `get_saved_session_detail(session_id)` — 按会话 ID 读完整快照（不存在抛 404 语义异常）
  - `DebatePersistenceError` — 写库失败显式抛出，不静默吞掉
- [x] `debate_orchestrator.py` 集成持久化，两个接口均已接入

### 4.3 辩论验证

- [x] 编写 `tests/test_debate.py`，用赵争议(D)跑完整辩论流程
- [x] 确认多轮辩论正常推进，数据库产生日志记录

### 4.4 持久化合约测试（计划外，已完成）

- [x] `tests/test_persistence_contract.py` — 序列化器与 DDL 字段一致性验证（mock DB，5个用例）
- [x] `tests/test_retrieval_api.py` — 读取接口路由级测试（TestClient + mock，5个用例）

**✅ 阶段验收通过：** `test_debate.py` 成功走完争议案例，数据库写入正常。

---

## ✅ 第五阶段：后端 API + Vue 前端演示系统（已完成）

> 目标：为导师和评委提供可视化演示界面，展现取证与多智能体辩论逻辑。

### 5.1 后端 API 接口

- [x] 创建 `api/main.py`（基于 FastAPI）
  - `POST /api/debate` — 同步接口，返回完整结构化 JSON
  - `POST /api/debate_stream` — SSE 流式接口，逐 Agent 实时输出
  - `GET /api/debates?id_card=...` — 按身份证查历史会话摘要列表
  - `GET /api/debates/{session_id}` — 按会话 ID 查完整历史详情（不存在返回 404）

### 5.2 Vue 项目与前端组件

- [x] 在 `frontend/` 目录下用 Vite + Vue 3 初始化前端项目，采用 Element Plus 深色主题
- [x] `App.vue` — 主入口，包含：
  - 身份证号输入框（执行期间禁用）
  - 「开始实时分析」按钮（执行期间禁用，防重复触发）
  - 「停止」按钮（执行期间显示，点击断开 SSE，已渲染内容保留，后端照常跑完写库）
  - 快速测试案例按钮（只填充身份证号，不自动触发分析）
  - 左侧历史会话面板 + 右侧会话详情视图
- [x] `components/EvidenceBoard.vue` — 取证快照列表展示
- [x] `components/AgentCard.vue` — 单个 Agent 判断气泡卡片
- [x] `components/DebateSessionView.vue` — 完整辩论会话视图（实时流 + 历史回放共用同一组件）
- [x] `components/HistorySessionList.vue` — 左侧历史会话列表面板，支持按 id_card 查询

**✅ 阶段验收通过：** 浏览器可完整演示从取证→流式辩论→历史回放的全流程。

---

## 🔨 第五阶段（收尾）：测试与文档补全（进行中）

> 对应 `.planning/ROADMAP.md` Phase 3: Verification and Hardening

- [ ] 补充 save→read 全链路回归测试（覆盖 round-trip 完整性，schema drift 检测）
- [ ] 补充持久化模型说明文档、检索接口 response 示例、后续扩展点说明

---

## 🔨 第六阶段：规则推理校验层（未开始）

> 目标：在 Agent 结论产出后，用硬编码规则做最终兜底校验（业务保险栓）。

- [ ] 创建 `rules/rule_engine.py`，将 `规则.txt` 强制逻辑硬编码为静态 Python 函数
  - 输入：`EvidenceBundle`，输出：符合/不符合/无法判定
- [ ] 将静态规则结果与 Agent 辩论结果进行 Diff 对比
- [ ] 若冲突 → 系统层面抛出"须人工核查"预警标记

**✅ 阶段验收目标：** 全部 9 个 Persona 能跑出规则结果，有能力揭露大模型幻觉。

---

## 🔨 第七阶段：评测实验（未开始）

> 目标：产出论文/报告所需的量化数据。

### 7.1 测试案例集

- [ ] 基于 9 个核心 Persona 扩展至 50 个测试案例
- [ ] 每个案例标注金标准标签（符合/不符合/数据缺失）
- [ ] 存入 `data/test_cases/test_cases.json`

### 7.2 批量评测

- [ ] 编写 `evaluation/eval_runner.py`，批量跑 50 个案例
- [ ] 计算准确率、证据完整性得分
- [ ] 输出结果至 `evaluation/results/`

### 7.3 对比与消融实验

- [ ] 实验一：单 Agent vs 多 Agent（准确率 + 可解释性）
- [ ] 实验二：有/无审计反驳 Agent（消融）
- [ ] 实验三：辩论 vs 直接投票（机制对比）
- [ ] 可选：平权投票 vs 权重裁决

### 7.4 可解释性人工评价

- [ ] 设计 5 维度评分量表（结论明确性/证据可追溯/争议说明/缺失指出/表述可读性）
- [ ] 2 名评分者给分，取均值

**✅ 阶段验收目标：** 产出完整的实验数据表格，可直接写入论文。

---

## 🔨 扩展基础设施：码值字典与 MCP 工具层（待办，未开始）

> 这两项是新扩展架构的基础支撑，与主业务链并行推进，不阻塞其他阶段。

### 码值字典生成

- [ ] 编写字典生成脚本（`scripts/generate_dicts.py`）
  - 扫描数据库中各枚举/码值字段，自动提取值域及语义
  - 输出格式参考 `dicts/ADC310.json`（含字段名、描述、码值→中文映射）
  - 覆盖范围：`hardship_category`、`insurer_status`、`employment_form`、`company_type`、`business_role` 等所有有意义枚举字段
- [ ] 将生成的字典文件统一存放于 `dicts/` 目录

### MCP 工具服务

- [x] 设计 MCP Server 接口规范（工具列表、入参/出参结构）
  - `get_dict(field_name)` — 按字段名按需加载对应码值字典，注入 Agent Prompt
  - `text_to_sql(intent, table_hints, dict_refs, person_id)` — 接收查询意图，动态生成 SQL 并执行，返回 JSON 结果
  - `auto_debug_sql(sql_with_bug, error_msg, ...)` — 接收执行错误，自动修正 SQL 并重试
- [x] 实现 MCP Server（基于官方 `mcp` 库与 `FastMCP` 架构，使用 `stdio` 传输机制）
- [ ] 与大模型直接集成：后续可让通用 Agent 直接通过 MCP 协议跨进程调用这些取证服务

---

## 持续跟踪项（贯穿全程）

- [ ] 每阶段完成后在本文件打勾，并更新 README.md 进度
- [ ] 关键设计决策记录在 `docs/design_decisions.md`
- [ ] 遇到政策规则歧义时记录在 `docs/policy/ambiguity_log.md`

---

## 🧭 v1.1 设计阶段边界（2026-03-24 已锁定）

> 说明：以下内容对应新的 `.planning` 设计里程碑 `v1.1`，不是立刻实现代码，而是先把扩展系统的正式边界讲清楚，避免后续开发时各人理解不一致。

### 当前设计里程碑的定位

- [x] 本轮先做设计，不做实现
- [x] 重点是定义模块边界、输入输出、上下游关系、非目标和后续开发顺序
- [x] 现有 `v1.0` 已跑通的静态取证 + 多 Agent 辩论链路继续作为基线参考，不在本轮直接重写

### 已锁定的 Phase 4 关键决策

- [x] 扩展系统的正式任务输入不再只是 `person_id`，而是：`person_id + policy_id + 可选资格范围`
- [x] 数据库认知层的第一版输出不是“全库灌输”，而是**任务裁剪语义包**
  - 该语义包最少包含：字段语义、相关码值片段、表关系提示、时间语义
- [x] MCP 不是“以后再说的可选项”，而是这套扩展架构的正式工具边界
- [x] 但 MCP 工具分阶段落地：第一优先是跑通 `text_to_sql`，其余 `get_dict`、`plan_evidence`、`auto_debug_sql` 先记入后续扩展
- [x] 目标架构中，动态 SQL 是主路径；现有静态 SQL 模板只保留为迁移期基线和回归对照，不是长期正式形态

### Phase 4 执行完成后，已经可以视为正式共识的系统边界

- [x] 系统不再被描述为“输入人 -> 5 个 Agent 分析投票 -> 规则校验”的单线结构
- [x] 系统的正式分层已经明确为：
  - 前置理解与取证准备层
  - 取证执行与证据构建层
  - 多 Agent 协商裁决层
  - 后置规则校验与人工复核层
  - 持续学习与评测支撑层
- [x] 各层职责边界已明确：前置层负责“知道该查什么”，取证层负责“把该查的东西查出来”，Agent 层负责“围绕证据做判断”，后置层负责“兜底与升级人工”，学习层负责“沉淀长期资产”
- [x] 当前 `v1.0` 的静态 SQL 模板链路仍然是**现实基线**，但不再是**目标架构**
- [x] 后续若实现 `text_to_sql` MCP，也不是让它单独决定资格结论，而是让它成为取证执行层中的正式工具

### 已明确的上下文加载原则

- [x] 默认只加载当前任务需要的最小语义上下文
- [x] 字典、关系提示、模板、历史修复样例都属于“按需加载”，不是默认全量注入
- [x] 默认禁止把整库 DDL、所有字典、所有历史 SQL 模板无脑塞进 Prompt

### 为了避免误解，特别说明

- [x] “任务裁剪语义包”不等于把整库 DDL、所有字典、所有历史 SQL 全塞进 Prompt
- [x] “直接按 MCP 定”不等于这轮就要把所有工具全部实现完
- [x] “动态替代静态”不等于立刻删除当前 `sql_templates.py`，而是后续架构目标明确转向动态生成

### 接下来 Phase 5/6/7 将继续细化的内容

- [ ] `dicts/` 目录下字典文件的统一格式、生成方式、索引方式
- [ ] `plan_evidence` 的正式输入输出结构
- [ ] `text_to_sql` MCP 的正式输入输出结构
- [ ] `auto_debug_sql` 的职责边界
- [ ] Evidence v2 的字段设计
- [ ] Debate Agent 从 MCP/规划层接收哪些上下文，哪些必须按需加载

### Phase 5 已锁定的字典与语义包方向（2026-03-24）

- [x] 字典文件第一版采用 **“ADC310 增强版”** 思路
  - 保留现有这类结构：`name` / `description` / `total_count` / `common_values` / `values`
  - 在此基础上再补：`source_refs` / `aliases` / `notes`
- [x] 字典文件命名以**字典ID**为主，不以物理字段名命名
  - 例如继续保留 `ADC310.json` 这种命名
  - 具体服务哪些表字段，写在文件内部元数据里
- [x] 一份字典允许服务多个源字段，不要求“一字段一份字典”
- [x] 任务裁剪语义包第一版采用**任务级组合包 + 分区卡片式结构**
  - 推荐至少分成：`task` / `fields` / `relations` / `time_semantics` / `dict_excerpt`
- [x] 字典注入默认采用**摘录优先**
  - 平时只注入当前任务相关的关键码值片段
  - 只有字典很小或确实需要时才放全量
- [x] 时间语义在新架构里是**一等公民**
  - 不是字段备注
  - 应作为独立区块进入语义包

---

## v1.1 Phase 5 阶段总结声明 (仅设计)

> 说明：本区块作为清晰的交接说明有意保留。

- Phase 5 仅涉及文档工作，不改变运行时代码。
- 现有两份基线设计契约：
  - `.planning/phases/05-database-cognition-and-dictionary-memory/05-DICT-CONTRACT.md`
  - `.planning/phases/05-database-cognition-and-dictionary-memory/05-SEMANTIC-PACKET-CONTRACT.md`
- 字典产物应保持类似 `ADC310.json` 的高可读性风格。
- 字典文件命名基于语义字典 ID，而非物理字段名。
- 一份字典可以通过 `source_refs` 服务于多个字段。
- 首批获批的元数据扩展为 `source_refs`、`aliases` 和 `notes`。
- 数据库认知层应输出经过任务裁剪的语义包，而非全schema的 Prompt 倾印。
- 语义包的基准区块包括：
  - `task` (任务)
  - `fields` (字段)
  - `relations` (关系)
  - `time_semantics` (时间语义)
  - `dict_excerpt` (字典摘录)
- 字典加载默认优先采用摘录（excerpt-first）。全量字典注入仅作为例外。
- 时间语义是一等公民上下文，因为后续的规划和查询生成将依赖于有效期窗口、计数窗口、时间先后规则和粒度。
- Phase 5 尚未定义的内容：
  - 生成器的具体实现
  - `plan_evidence`（证据规划）的确切 schema
  - `text_to_sql` MCP 的确切 schema
  - 摘录与全量加载之间的确切运行时启发式规则
  - 针对特殊情况字典的字段级覆盖机制

当前的理解：

- Phase 5 已足以指导字典文件设计和认知层输出的实现。
- 它尚未成为整个扩展系统的完整实现指南，因为 Phase 6 和 Phase 7 还需要定义证据规划、动态查询契约机制以及 Agent 交接规则。

---

## v1.1 Phase 6 阶段总结声明 (仅设计)

> 说明：本区块作为清晰的交接说明有意保留。

- Phase 6 仅涉及文档工作，不改变运行时代码。
- 此阶段的核心是将 Phase 5 的语义包转化为实际的规划与查询契约。
- 当前的静态资产被视为迁移基线，而非最终架构：
  - `text2sql/sql_templates.py`
  - `text2sql/evidence_collector.py`
  - `evidence/evidence_model.py`
- 检查问题模板目前的定位是“以资格审查项优先”。
  - 资格审查项是核心锚点。
  - 政策条款与冲突模式是关联引用的元数据，而非主要组织键。
- 证据规划项目前的定位是“以问题为导向”。
  - 一个规划项 = 一个核查问题。
  - 一个规划项可指向多个取证目标、字段和时间约束条件。
- 动态查询目前的定位是“有界限的调用链”：
  - 证据规划项 (evidence plan item)
  - 查询意图 (query intent)
  - text_to_sql 工具调用
  - 数据库执行
  - 可选的 auto_debug_sql（自动调试）
  - 明确的成功或明确的中止
- 本项目不希望出现永无止境的自我修复循环。
  - 重试行为应是有限的。
  - 语义不确定时允许以中止或上报（人工）作为最终结果。
- Evidence v2 目前的定位是“完整的、可审计的证据对象”。
  - 它最终应承载出处证明、字典引用、查询意图引用、时间范围、执行结果和修复历史。
- Debate Agent 不应将原生 SQL 作为主要上下文消费。
  - 默认的交接机制应该是“摘要优先”且可通过引用进行追溯。

Phase 6 尚未完全定义的内容：

- 问题模板的确切子字段 schema
- 规划项的确切子字段 schema
- 自动修复的确切数值化重试上限
- `query_intent`（查询意图）的确切最终形态
- Evidence v2 的确切逐字段 schema

当前的理解：

- Phase 6 的讨论已足以规划下一轮设计。
- 它尚未成为最终的实现蓝图，因为 Phase 6 的规划和执行仍需正式确立这些契约，且 Phase 7 仍需定义最终的 Agent/工具交接规则。

---

## v1.1 Phase 6 执行阶段总结 (仅设计)

> 说明：本区块作为清晰的交接说明有意保留。

- Phase 6 的执行仍然仅涉及文档工作，不改变运行时代码。
- Phase 6 在契约定义层面现已完成。
- 目前已产出三份正式资产：
  - `.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-QUESTION-AND-PLAN-CONTRACT.md`
  - `.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-DYNAMIC-QUERY-CONTRACT.md`
  - `.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-EVIDENCE-V2-CONTRACT.md`
- 规划侧（planning-side）契约已足够稳定，可指导以下内容的实现：
  - 可复用的核查问题模板
  - 以问题为导向的证据规划项
  - 从资格审查项到问题模板再到规划项的可追溯性
- 动态查询契约已足够稳定，可指导以下内容的实现：
  - `query_intent` (查询意图)
  - 运行时的 `text_to_sql`
  - 有界限的 `auto_debug_sql`
  - 明确的中止条件
  - 运行时可观测性（且无需将 SQL 视为长期记忆）
- Evidence v2 契约已足够稳定，可指导以下内容的实现：
  - 包含丰富出处证明的证据对象
  - 字典与查询的血缘关系 (lineage)
  - 修复历史保留机制
  - 摘要优先的下游消费机制
- 旧有的静态路径仍作为迁移基线：
  - `text2sql/sql_templates.py`
  - `text2sql/evidence_collector.py`
  - `evidence/evidence_model.py`
- 新设计应被解读为基于旧基线的向前映射，而不是全盘否定旧系统。

Phase 6 明确敲定的内容：

- 规划应是“问题优先”，而非“SQL优先”
- 数据检索必须通过 `query_intent` 进行传递
- 修复必须是有限的并且具备中止感知能力
- 证据应是一个可审计的产物，而不仅仅是查询结果的包装
- 辩论 Agent 在处理证据视图时，应默认使用“摘要优先”，而非直接查看底层 SQL

Phase 7 仍需完成的工作：

- 最终的 Agent/工具 交接契约
- Prompt 上下文加载规则
- 明确哪些是“常驻”，哪些是“按需提取”，哪些是“绝不盲目注入”
- 为后续编码阶段提供可落地的实施蓝图

当前的理解：

- Phase 6 现在已足以作为规划对象、动态查询边界和证据对象演进方向的开发指导。
- 该里程碑尚未完全结束，因为 Phase 7 还必须定义辩论 Agent 如何消费这些产物，以及后续实施工作该如何分阶段进行。

---

## v1.1 Phase 7 阶段总结声明 (仅设计)

> 说明：本区块作为清晰的交接说明有意保留。

- Phase 7 仍然仅涉及文档工作，不改变运行时代码。
- 本阶段的核心是确定已就绪的证据与辩论 Agent 之间的最终交接边界。
- 目前明确的默认流向为：
  - 上游工具负责准备
  - 下游 Agent 负责判定
- 辩论 Agent 应当接收“摘要优先”的证据投影，而非原生 SQL 或底层数据库状态。
- 该投影仍应比单行摘要更加丰富。
  - 它应包含任务头部、资格审查范围、证据摘要、不确定性标记及对底层证据工件的引用。
- 不应再期望辩论 Agent：
  - 自行推断代码字典
  - 从原始字段中自行重构时间语义
  - 在常规辩论回合中直接进行数据库探索
- 如果 Agent 认为证据存在缺失，首选行为不应是直接使用查询工具。
  - 它应当抛出结构化的缺失或质疑信号。
  - 任何二次检索动作都应由编排层 (orchestrator layer) 来中转调度。
- Prompt 加载现已划分为不同层级：
  - 常驻加载 (always-on)：角色设定、任务头、政策范围、辩论目标、当前的证据投影、前序回合判断记录
  - 按需加载 (on-demand)：深层溯源信息、额外的字典摘录、修复历史、特定的语义包含区块
  - 绝不盲目注入 (never blindly injected)：全库 schema 盲dump、默认情况下的完整字典、默认情况下的原生 SQL 追踪记录、完整未裁剪的 Evidence v2 对象
- 实施路径应分阶段推进，而非一次性推翻重写。
  - 第一步：在现有的证据对象和未来的 agent 投影之间，建立适配器边界。
  - 第二步：在该边界后方引入新的检索管线。
  - 第三步：将新的检索输出接入到辩论编排层中，同时避免让 Agent 退化为自由调用的工具机器。
  - 在整个迁移过程中，旧的静态路径都将作为基线、回退方案和回归测试的参考对照 (oracle)。

Phase 7 旨在完成的内容：

- 明确界定辩论 Agent 的接收内容
- 明确界定它们不再需要自行凭空推断的内容
- 明确界定哪些工具属于编排层，哪些属于辩论层
- 明确界定哪些上下文是“常驻”，哪些是“按需”，哪些是“绝不盲目注入”
- 明确后续落地实施的分段步骤

尚不属于此阶段的内容：

- 具体的 MCP 协议传输与部署结构
- 实时的人机/智能体多路检索循环
- 规则引擎的执行
- 大规模评测与自动化学习

---

## v1.1 Phase 7 执行阶段总结 (仅设计)

> 说明：本区块作为清晰的交接说明有意保留。

- Phase 7 的执行仍然仅涉及文档工作，不改变运行时代码。
- 目前已产出三份正式资产：
  - `.planning/phases/07-agent-tool-boundary-and-implementation-blueprint/07-AGENT-EVIDENCE-PROJECTION-CONTRACT.md`
  - `.planning/phases/07-agent-tool-boundary-and-implementation-blueprint/07-PROMPT-AND-TOOL-BOUNDARY-CONTRACT.md`
  - `.planning/phases/07-agent-tool-boundary-and-implementation-blueprint/07-IMPLEMENTATION-BLUEPRINT.md`
- 扩展架构现已确立了封闭的下游边界。
  - 上游工具负责准备语义和证据。
  - 编排器 (orchestrator) 负责路由和任何未来的缺失情报上报。
  - 辩论 Agent 仅就准备好的证据进行裁决，不再直接探索数据库。
- 此时已明确规定：默认的辩论输入就是 Evidence v2 的 Agent 面向投影 (agent-facing projection)。
  - 它以摘要为优先。
  - 结构化程度依然能够承载不确定性、矛盾点及可追踪的引用。
- Prompt 的加载规则现在已有了明确分层：
  - 常驻 (always-present)
  - 按需 (on-demand)
  - 绝对不可盲目注入 (never blindly injected)
- 工具归属同样进行了明确分层。
  - `text_to_sql`、`get_dict`、`auto_debug_sql` 以及其他检索侧的工作保留在上游。
  - 辩论 Agent 在常规的回合中并不直接拥有这些工具。
- 确认了 v1.1 版本后的后续实施顺序是分段开展的，而非模糊不清：
  - 首先，稳定适配器边界
  - 然后，在边界后方引入新的检索管线
  - 最后，将新引入的检索输出挂载至动态的辩论编排中
- 旧有的静态检索链条明确得以保留并被用作：
  - 基准线 (baseline)
  - 兜底方案 (fallback)
  - 自动化回归预期对照 (regression oracle)

更通俗的解释：

- v1.1 现在已经足够完善，可直接指导真实的研发落地工作。
- 它不再是空中楼阁的宏大愿景，主要的契约条款和迁移步骤都已形成文字。

Phase 7 之后剩下的工作：

- 里程碑级别的审计与归档
- 后续的具体实施开发阶段
- 未来待推进的延后内容，如规则引擎、MCP 的部署拓扑以及大规模评测等

## 🔨 v1.2 第一阶段：Adapter Boundary（Slice 1）

> 目标：在不改动现有取证链路职责的前提下，给 debate agent 建立稳定的投影适配边界。

- [x] 新增 `EvidenceProjection` / `EvidenceSummaryCard` 数据模型
- [x] 实现 `project_evidence()`，将 `EvidenceBundle` 转为 agent-facing projection
- [x] 让 `BaseAgent` / `DebateOrchestrator` 改为消费 projection 格式
- [x] 补充 Slice 1 回归测试，并更新 `tests/test_debate.py`

## ✅ v1.2 第二阶段：前置理解与取证准备层（Slice 2a）

> 目标：先完成 cognition 第一层的内部接口和种子资产，不影响现有前端和 `/api/debate` / `/api/debate_stream` 主链路。

- [x] 实现 `scripts/generate_dicts.py` 和第一批 enhanced dictionary seed assets
- [x] 实现 `cognition/semantic_packet.py` 五段式 typed packet builder
- [x] 实现 `cognition/question_templates.py` 的 question-type registry
- [x] 实现 `cognition/evidence_planner.py` 的 question-driven plan interface

## ✅ v1.2 第三阶段：动态取证与组装引擎（进行中，Slice 2b）

> 目标：衔接前置规划层，落实动态 SQL 的撰写、自愈执行与 JSON 到自然语言的装配转译。

- [x] 实现 `text2sql/dynamic/prompt_builder.py` 动态构建过滤与 DDL 注入。
- [x] 实现 `text2sql/dynamic/text2sql_agent.py` 生成带安全占位符的精准 SQL。
- [x] 实现 `text2sql/dynamic/auto_debugger.py` 实现抗压执行与带异常反馈自愈 (Auto Correction)。
- [x] 实现 `text2sql/dynamic/evidence_assembler.py` 翻译冰冷数据库 JSON 为带有 `supports_conclusion` 的大白话论据。
- [x] 缝合上述组件产生核心大满贯类 `DynamicEvidenceCollector`。
- [x] 编写测试脚本验证其执行稳定性，并在后端的 `debate_orchestrator.py` 中彻底完成对静态 `EvidenceCollector` 的“换脑接管机制”。

## ✅ v1.3 前端重构：“三视窗”全景看板演示系统（进行中）

> 目标：为了极其直观且震撼地展示系统能力，打破长页面流水账布局，使用 Element Plus `Tabs` 实施解耦大屏策略。

- [x] **重构路由与状态**：调整 `App.vue` 引入 Tabs 层级，优化不同界面的数据流转感知。
- [x] **视图一：取证规划中心 (Cognition Terminal)** 
      核心打磨：专享黑客感知体验，展示 `Evidence Planner` 的意图拆解过程，结合已接入后端的 SSE `system_trace` 事件，动态演绎 `Text2SQL`生成、压测查库、自动排错的一站式流水线。
- [x] **视图二：多智能体辩论庭 (Multi-Agent Tribunal)**
      核心打磨：承接视图一的可用 `EvidenceBundle`，以沉浸视角专注展示 5 位异质 Agent 的唇枪舌剑与共识收敛。
- [x] **视图三：决策审计看板 (Global History Audit)**
      核心打磨：剥离原左侧边栏，转换为数据报表面板形式，显示通过率、共识率及所有审计历史记录清单。
