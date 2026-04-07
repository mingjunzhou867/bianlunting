-- ==========================================================
-- 核心功能测试：九大典型验证人设（Persona A~I）模拟数据
-- 设定时间基准：本系统当前运转日期视为 2026年3月21日
--
-- A 张完美 — 完美过审型（正向基准）
-- B 李老板 — 隐蔽拒审型（明确欺诈）
-- C 王精算 — 精准算账型（功能二测试）
-- D 赵争议 — 薛定谔的困难人员（功能三辩论）
-- E 陈灰色 — 已注销个体户の身份困境（功能一排斥争议）
-- F 吴边界 — 退休年龄线上的女性（功能一+二交叉争议）
-- G 孙迷雾 — 事业单位临聘の财政供养之谜（功能一推断争议）
-- H 郑重叠 — 高校毕业生の算账噩梦（功能二精算+排斥交叉争议）
-- I 钱幽灵 — 死亡标记の幽灵人（基础条件vs数据可信度争议）
-- ==========================================================

-- --------------------------------------------------------
-- 清理旧数据（按外键依赖倒序）
-- --------------------------------------------------------
DELETE FROM agent_debate_log;
DELETE FROM debate_session;
DELETE FROM subsidy_payment_history;
DELETE FROM insurance_change_log;
DELETE FROM social_insurance_payment;
DELETE FROM employment_registration;
DELETE FROM hardship_certification;
DELETE FROM unemployment_registration;
DELETE FROM company_shareholder;
DELETE FROM person;
DELETE FROM company_info;

-- --------------------------------------------------------
-- 前置准备：模拟本市多家企业/单位
-- --------------------------------------------------------
INSERT INTO company_info (company_id, company_name, legal_person_id_card, company_type, is_valid) VALUES
('91420900000000001X', '湖北某科技有限公司',   '420902197001019999', '企业',       '1'),
('91420900000000002Y', '孝感某商贸有限公司',   '42090219850505000B', '企业',       '1'),
('91420900000000003Z', '陈灰色个体经营部',     '42090219780815000E', '个体工商户', '0'),
('91420900000000004W', '孝感市某中学',         NULL,                '事业单位',   '1'),
('91420900000000005V', '孝感某职业培训学校',   NULL,                '企业',       '1');


-- ========================================================
-- 🎭 Persona A：【完美过审型】—— 正向基准对照
-- 姓名：张完美  画像：各项登记无缝衔接，标准补贴候选人
-- ========================================================
INSERT INTO person (id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role) VALUES
('42090219800101000A', '张完美', '女', '1980-01-01', '孝感市市辖区', '生存', '1', NULL);

INSERT INTO unemployment_registration (id_card, unemployment_date, unemployment_reason, register_date, is_valid) VALUES
('42090219800101000A', '2025-01-01', '原单位倒闭', '2025-01-05', '1');

INSERT INTO hardship_certification (id_card, hardship_category, apply_date, certify_org, is_valid) VALUES
('42090219800101000A', '大龄失业人员', '2025-02-01', '孝感市就业局', '1');

INSERT INTO employment_registration (id_card, employment_form, employment_date, is_valid) VALUES
('42090219800101000A', '灵活就业', '2025-03-01', '1');

INSERT INTO social_insurance_payment (id_card, insurance_type, pay_month, insurer_status, pay_base, is_valid) VALUES
('42090219800101000A', '110', '202601', '102', 4000.00, '1'),
('42090219800101000A', '310', '202601', '102', 4000.00, '1'),
('42090219800101000A', '110', '202602', '102', 4000.00, '1'),
('42090219800101000A', '310', '202602', '102', 4000.00, '1');


-- ========================================================
-- 🎭 Persona B：【隐蔽拒审型】—— 多Agent交叉反欺诈
-- 姓名：李老板  画像：表面全达标，深层是某商贸公司股东
-- ========================================================
INSERT INTO person (id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role) VALUES
('42090219850505000B', '李老板', '男', '1985-05-05', '孝感市市辖区', '生存', '1', NULL);

INSERT INTO unemployment_registration (id_card, unemployment_date, register_date, is_valid) VALUES
('42090219850505000B', '2024-06-01', '2024-06-15', '1');

INSERT INTO hardship_certification (id_card, hardship_category, apply_date, is_valid) VALUES
('42090219850505000B', '家庭零就业人员', '2024-07-01', '1');

INSERT INTO social_insurance_payment (id_card, insurance_type, pay_month, insurer_status, is_valid) VALUES
('42090219850505000B', '110', '202602', '102', '1');

INSERT INTO company_shareholder (company_id, id_card, share_ratio, is_valid) VALUES
('91420900000000002Y', '42090219850505000B', 30.00, '1');


-- ========================================================
-- 🎭 Persona C：【精准算账型】—— 功能二工具调用
-- 姓名：王精算  画像：历史已领12个月，距60岁退休剩25个月
-- ========================================================
INSERT INTO person (id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role) VALUES
('42090219680401000C', '王精算', '男', '1968-04-01', '孝感市市辖区', '生存', '1', NULL);

INSERT INTO unemployment_registration (id_card, unemployment_date, unemployment_reason, register_date, is_valid) VALUES
('42090219680401000C', '2022-11-01', '企业裁员', '2022-11-15', '1');

INSERT INTO hardship_certification (id_card, hardship_category, apply_date, certify_org, is_valid) VALUES
('42090219680401000C', '大龄失业人员', '2022-12-01', '孝感市就业局', '1');

INSERT INTO employment_registration (id_card, employment_form, employment_date, is_valid) VALUES
('42090219680401000C', '灵活就业', '2023-01-01', '1');

INSERT INTO social_insurance_payment (id_card, insurance_type, pay_month, insurer_status, pay_base, is_valid) VALUES
('42090219680401000C', '110', '202509', '102', 4000.00, '1'),
('42090219680401000C', '310', '202509', '102', 4000.00, '1'),
('42090219680401000C', '110', '202510', '102', 4000.00, '1'),
('42090219680401000C', '310', '202510', '102', 4000.00, '1'),
('42090219680401000C', '110', '202511', '102', 4000.00, '1'),
('42090219680401000C', '310', '202511', '102', 4000.00, '1'),
('42090219680401000C', '110', '202512', '102', 4000.00, '1'),
('42090219680401000C', '310', '202512', '102', 4000.00, '1'),
('42090219680401000C', '110', '202601', '102', 4000.00, '1'),
('42090219680401000C', '310', '202601', '102', 4000.00, '1'),
('42090219680401000C', '110', '202602', '102', 4000.00, '1'),
('42090219680401000C', '310', '202602', '102', 4000.00, '1');

INSERT INTO subsidy_payment_history (id_card, policy_code, first_enjoy_month, apply_start_month, apply_end_month, grant_months, grant_amount, is_valid) VALUES
('42090219680401000C', 'FLEX_SUB_2023', '202301', '202301', '202306', 6, 1800.00, '1'),
('42090219680401000C', 'FLEX_SUB_2023', '202307', '202307', '202312', 6, 1800.00, '1');


-- ========================================================
-- 🎭 Persona D：【薛定谔の困难人员】—— 功能三主动服务辩论
-- 姓名：赵争议  画像：3月1日入职但系统社保未切换，名义未就业
-- ========================================================
INSERT INTO person (id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role) VALUES
('42090219760310000D', '赵争议', '男', '1976-03-10', '孝感市市辖区', '生存', '1', NULL);

INSERT INTO employment_registration (id_card, company_id, employment_form, employment_date, contract_start_date, sync_date, is_valid) VALUES
('42090219760310000D', '91420900000000001X', '全日制用工', '2026-03-01', '2026-03-01', '2026-03-05', '1');

INSERT INTO social_insurance_payment (id_card, insurance_type, pay_month, insurer_status, pay_base, is_valid) VALUES
('42090219760310000D', '110', '202602', '102', 4000.00, '1');

INSERT INTO insurance_change_log (id_card, insurance_type, old_status, new_status, event_date, related_company_id, is_valid) VALUES
('42090219760310000D', '110', '102', '101', '2026-03-15', '91420900000000001X', '1');


-- ========================================================
-- 🎭 Persona E：【已注销个体户の身份困境】
-- 姓名：陈灰色
-- 争议维度：功能一排斥条件的边界
--
-- person.business_role = '个体工商户'（历史残留，系统未清洗）
-- company_info 中那家个体户 is_valid = '0'（已注销）
--
-- 🔥 排斥Agent："business_role写着个体工商户 → 直接排除！"
-- 🔥 资格Agent："工商库显示已注销，她现在是普通失业居民"
-- 🔥 政策Agent："规则说的是'是'个体工商户，注销了就'不是'了"
-- 🔥 裁判Agent：排斥条件看"当前状态"还是"历史记录"？
-- ========================================================
INSERT INTO person (id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role) VALUES
('42090219780815000E', '陈灰色', '女', '1978-08-15', '孝感市市辖区', '生存', '1', '个体工商户');

INSERT INTO unemployment_registration (id_card, unemployment_date, unemployment_reason, register_date, is_valid) VALUES
('42090219780815000E', '2025-01-05', '个体经营停业', '2025-01-10', '1');

INSERT INTO hardship_certification (id_card, hardship_category, apply_date, certify_org, is_valid) VALUES
('42090219780815000E', '大龄失业人员', '2025-02-15', '孝感市就业局', '1');

INSERT INTO employment_registration (id_card, employment_form, employment_date, is_valid) VALUES
('42090219780815000E', '灵活就业', '2025-03-01', '1');

INSERT INTO social_insurance_payment (id_card, insurance_type, pay_month, insurer_status, pay_base, is_valid) VALUES
('42090219780815000E', '110', '202601', '102', 3800.00, '1'),
('42090219780815000E', '310', '202601', '102', 3800.00, '1'),
('42090219780815000E', '110', '202602', '102', 3800.00, '1'),
('42090219780815000E', '310', '202602', '102', 3800.00, '1');


-- ========================================================
-- 🎭 Persona F：【退休年龄线上的女性】
-- 姓名：吴边界
-- 争议维度：功能一排斥 + 功能二精算 交叉争议
--
-- 女性1971-03-21生，今天(2026-03-21)正好55岁
-- 女性退休：50岁(工人岗) vs 55岁(管理/技术岗)
-- 职业历史模糊：先做操作工13年，后做行政管理4年
--
-- 🔥 排斥Agent："不管50或55，都到了或过了 → 已退休排除！"
-- 🔥 资格Agent："最后岗位是行政管理，按55岁，今天刚到线，
--    政策没说到线当天算退休"
-- 🔥 精算Agent："即使不算退休，情况2=退休日-申领开始≈0个月"
-- 🔥 裁判Agent：以什么标准认定退休？最后岗位？最长岗位？
-- ========================================================
INSERT INTO person (id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role) VALUES
('42090219710321000F', '吴边界', '女', '1971-03-21', '孝感市市辖区', '生存', '1', NULL);

INSERT INTO unemployment_registration (id_card, unemployment_date, unemployment_reason, register_date, is_valid) VALUES
('42090219710321000F', '2023-06-01', '合同期满未续签', '2023-06-10', '1');

INSERT INTO hardship_certification (id_card, hardship_category, apply_date, certify_org, is_valid) VALUES
('42090219710321000F', '大龄失业人员', '2023-07-01', '孝感市就业局', '1');

-- 历史就业1：2005-2018 某科技公司 车间操作工（已离职）
INSERT INTO employment_registration (id_card, company_id, employment_form, employment_date, contract_start_date, contract_end_date, is_valid) VALUES
('42090219710321000F', '91420900000000001X', '全日制用工', '2005-03-01', '2005-03-01', '2018-12-31', '0');

-- 历史就业2：2019-2023 某商贸公司 行政管理（已离职）
INSERT INTO employment_registration (id_card, company_id, employment_form, employment_date, contract_start_date, contract_end_date, is_valid) VALUES
('42090219710321000F', '91420900000000002Y', '全日制用工', '2019-01-15', '2019-01-15', '2023-05-31', '0');

-- 当前：2023年7月起灵活就业
INSERT INTO employment_registration (id_card, employment_form, employment_date, is_valid) VALUES
('42090219710321000F', '灵活就业', '2023-07-15', '1');

INSERT INTO social_insurance_payment (id_card, insurance_type, pay_month, insurer_status, pay_base, is_valid) VALUES
('42090219710321000F', '110', '202601', '102', 3500.00, '1'),
('42090219710321000F', '310', '202601', '102', 3500.00, '1'),
('42090219710321000F', '110', '202602', '102', 3500.00, '1'),
('42090219710321000F', '310', '202602', '102', 3500.00, '1');

-- 历史已领18个月补贴
INSERT INTO subsidy_payment_history (id_card, policy_code, first_enjoy_month, apply_start_month, apply_end_month, grant_months, grant_amount, is_valid) VALUES
('42090219710321000F', 'FLEX_SUB_2024', '202401', '202401', '202406', 6, 1800.00, '1'),
('42090219710321000F', 'FLEX_SUB_2024', '202407', '202407', '202412', 6, 1800.00, '1'),
('42090219710321000F', 'FLEX_SUB_2025', '202501', '202501', '202506', 6, 1800.00, '1');


-- ========================================================
-- 🎭 Persona G：【事业单位临聘の财政供养之谜】
-- 姓名：孙迷雾
-- 争议维度：功能一"合理推断"规则
--
-- 曾在某中学(事业单位)做临聘后勤3年，那段社保是单位缴(101)
-- 2025年6月合同到期后转灵活就业(102)
--
-- 🔥 排斥Agent："事业单位缴过社保 → 财政供养人员 → 不通过！"
-- 🔥 资格Agent："她是临聘不是编制，现在医保已转102个人缴"
-- 🔥 政策Agent："'期间医保单位缴纳'指当前申领期间，不是历史"
-- 🔥 裁判Agent：临聘算财政供养？"期间"怎么定义？
-- ========================================================
INSERT INTO person (id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role) VALUES
('42090219820620000G', '孙迷雾', '女', '1982-06-20', '孝感市市辖区', '生存', '1', NULL);

INSERT INTO unemployment_registration (id_card, unemployment_date, unemployment_reason, register_date, is_valid) VALUES
('42090219820620000G', '2025-06-15', '聘用合同到期', '2025-06-20', '1');

INSERT INTO hardship_certification (id_card, hardship_category, apply_date, certify_org, is_valid) VALUES
('42090219820620000G', '大龄失业人员', '2025-08-01', '孝感市就业局', '1');

INSERT INTO employment_registration (id_card, employment_form, employment_date, is_valid) VALUES
('42090219820620000G', '灵活就业', '2025-08-15', '1');

-- 历史：事业单位期间的社保记录(101单位缴费) ← Agent会查到这些！
INSERT INTO social_insurance_payment (id_card, company_id, insurance_type, pay_month, insurer_status, pay_base, is_valid) VALUES
('42090219820620000G', '91420900000000004W', '110', '202501', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '310', '202501', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '110', '202502', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '310', '202502', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '110', '202503', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '310', '202503', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '110', '202504', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '310', '202504', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '110', '202505', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '310', '202505', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '110', '202506', '101', 4500.00, '1'),
('42090219820620000G', '91420900000000004W', '310', '202506', '101', 4500.00, '1');

-- 当前：灵活就业个人缴费(102)
INSERT INTO social_insurance_payment (id_card, insurance_type, pay_month, insurer_status, pay_base, is_valid) VALUES
('42090219820620000G', '110', '202509', '102', 3800.00, '1'),
('42090219820620000G', '310', '202509', '102', 3800.00, '1'),
('42090219820620000G', '110', '202510', '102', 3800.00, '1'),
('42090219820620000G', '310', '202510', '102', 3800.00, '1'),
('42090219820620000G', '110', '202511', '102', 3800.00, '1'),
('42090219820620000G', '310', '202511', '102', 3800.00, '1'),
('42090219820620000G', '110', '202512', '102', 3800.00, '1'),
('42090219820620000G', '310', '202512', '102', 3800.00, '1'),
('42090219820620000G', '110', '202601', '102', 3800.00, '1'),
('42090219820620000G', '310', '202601', '102', 3800.00, '1'),
('42090219820620000G', '110', '202602', '102', 3800.00, '1'),
('42090219820620000G', '310', '202602', '102', 3800.00, '1');

-- 险种变更记录：从101→102
INSERT INTO insurance_change_log (id_card, insurance_type, old_status, new_status, event_date, related_company_id, is_valid) VALUES
('42090219820620000G', '110', '101', '102', '2025-07-01', '91420900000000004W', '1'),
('42090219820620000G', '310', '101', '102', '2025-07-01', '91420900000000004W', '1');


-- ========================================================
-- 🎭 Persona H：【高校毕业生の算账噩梦】
-- 姓名：郑重叠
-- 争议维度：功能二精算 + 功能一排斥 双重交叉
--
-- 2024年6月毕业，困难类=高校毕业生，已领6个月补贴
-- 缴了4个月灵活就业社保，但其中1个月(2025.12)的医保(310)
-- 竟然是某培训机构代缴的101！
--
-- 🔥 精算Agent四路：min(30, ∞, 18, 3or4) → 结果是3还是4？
-- 🔥 排斥Agent："12月医保101=单位缴纳 → 直接排除！"
-- 🔥 资格Agent："那只是培训机构代缴，不是正式用工"
-- 🔥 裁判Agent：代缴算"单位缴纳"吗？情况4取几？
-- ========================================================
INSERT INTO person (id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role) VALUES
('42090220010901000H', '郑重叠', '女', '2001-09-01', '孝感市市辖区', '生存', '1', NULL);

INSERT INTO unemployment_registration (id_card, unemployment_date, unemployment_reason, register_date, is_valid) VALUES
('42090220010901000H', '2024-07-01', '高校毕业未就业', '2024-07-15', '1');

INSERT INTO hardship_certification (id_card, hardship_category, apply_date, certify_org, is_valid) VALUES
('42090220010901000H', '离校2年内未就业的高校毕业生', '2024-08-01', '孝感市就业局', '1');

INSERT INTO employment_registration (id_card, employment_form, employment_date, is_valid) VALUES
('42090220010901000H', '灵活就业', '2024-09-01', '1');

-- 社保缴费（关键争议：2025.12的医保310是101单位代缴⚠️）
INSERT INTO social_insurance_payment (id_card, insurance_type, pay_month, insurer_status, pay_base, is_valid) VALUES
('42090220010901000H', '110', '202511', '102', 3500.00, '1'),
('42090220010901000H', '310', '202511', '102', 3500.00, '1'),
('42090220010901000H', '110', '202512', '102', 3500.00, '1'),
('42090220010901000H', '310', '202512', '101', 3500.00, '1'),  -- ⚠️培训机构代缴！
('42090220010901000H', '110', '202601', '102', 3500.00, '1'),
('42090220010901000H', '310', '202601', '102', 3500.00, '1'),
('42090220010901000H', '110', '202602', '102', 3500.00, '1'),
('42090220010901000H', '310', '202602', '102', 3500.00, '1');

INSERT INTO subsidy_payment_history (id_card, policy_code, first_enjoy_month, apply_start_month, apply_end_month, grant_months, grant_amount, is_valid) VALUES
('42090220010901000H', 'FLEX_GRAD_2024', '202409', '202409', '202502', 6, 1200.00, '1');


-- ========================================================
-- 🎭 Persona I：【死亡标记の幽灵人】
-- 姓名：钱幽灵
-- 争议维度：基础条件 vs 数据可信度の终极拷问
--
-- 55岁男性，距退休还有5年。person表 life_status='死亡'
-- 但社保2026年1-2月仍正常扣缴！系统还打过补贴款！
--
-- 🔥 排斥Agent："死亡→基础条件不满足→不通过"
-- 🔥 取证Agent："社保还在扣，银行卡正常运作，可能是误录"
-- 🔥 反欺诈Agent："如果真死了，谁在冒用身份缴费领补贴？欺诈！"
-- 🔥 裁判Agent："无法自动判定→暂停审批→移交人工核实"
-- ========================================================
INSERT INTO person (id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role) VALUES
('42090219700505000I', '钱幽灵', '男', '1970-05-05', '孝感市市辖区', '死亡', '1', NULL);

INSERT INTO unemployment_registration (id_card, unemployment_date, unemployment_reason, register_date, is_valid) VALUES
('42090219700505000I', '2024-03-01', '企业搬迁', '2024-03-10', '1');

INSERT INTO hardship_certification (id_card, hardship_category, apply_date, certify_org, is_valid) VALUES
('42090219700505000I', '大龄失业人员', '2024-04-01', '孝感市就业局', '1');

INSERT INTO employment_registration (id_card, employment_form, employment_date, is_valid) VALUES
('42090219700505000I', '灵活就业', '2024-05-01', '1');

-- 诡异：人"死了"但社保还在正常扣缴
INSERT INTO social_insurance_payment (id_card, insurance_type, pay_month, insurer_status, pay_base, is_valid) VALUES
('42090219700505000I', '110', '202601', '102', 4000.00, '1'),
('42090219700505000I', '310', '202601', '102', 4000.00, '1'),
('42090219700505000I', '110', '202602', '102', 4000.00, '1'),
('42090219700505000I', '310', '202602', '102', 4000.00, '1');

-- 更诡异：系统还给他发过补贴！
INSERT INTO subsidy_payment_history (id_card, policy_code, first_enjoy_month, apply_start_month, apply_end_month, grant_months, grant_amount, grant_date, is_valid) VALUES
('42090219700505000I', 'FLEX_SUB_2025', '202507', '202507', '202512', 6, 1800.00, '2025-12-20', '1');


-- ========================================================
-- 已保存辩论会话 Mock 数据（对接 Phase 1 / Phase 2 新结构）
-- 用于历史列表与详情接口联调
-- ========================================================
INSERT INTO debate_session (
    session_id, id_card, status, source_endpoint, final_conclusion, final_stance,
    consensus_rate, is_consensus_reached, rounds_taken, evidence_count, agent_count,
    started_at, completed_at, snapshot_payload
) VALUES
(
    'sess-A-20260321-001',
    '42090219800101000A',
    'completed',
    '/api/debate',
    '符合',
    '支持通过',
    1.0000,
    1,
    0,
    4,
    3,
    '2026-03-21 09:00:00',
    '2026-03-21 09:00:20',
    '{"session_id":"sess-A-20260321-001","id_card":"42090219800101000A","evidence_count":4,"rounds_taken":0,"final_conclusion":"符合","final_stance":"支持通过","consensus_rate":1.0,"is_consensus_reached":true,"history":[{"round_num":0,"judgments":[{"agent_id":"agent_strict","agent_role":"严格合规Agent","debate_round":0,"conclusion":"符合","stance":"支持通过","confidence":0.9,"evidence_refs":["BASIC_001","BASIC_002"],"reasoning":"基础资格与灵活就业缴费记录一致。","dissent_points":[],"key_finding":"基础条件齐全"},{"agent_id":"agent_lenient","agent_role":"宽松业务Agent","debate_round":0,"conclusion":"符合","stance":"支持通过","confidence":0.88,"evidence_refs":["BASIC_001","PAY_102"],"reasoning":"当前画像符合稳定灵活就业状态。","dissent_points":[],"key_finding":"无明显排斥信号"},{"agent_id":"agent_auditor","agent_role":"审计挑战Agent","debate_round":0,"conclusion":"符合","stance":"支持通过","confidence":0.76,"evidence_refs":["BASIC_001"],"reasoning":"虽需持续关注，但当前证据未见异常。","dissent_points":[],"key_finding":"证据链完整"}],"total":3,"majority_stance":"支持通过","majority_count":3,"consensus_rate":1.0,"is_consensus_reached":true}],"status":"completed","source_endpoint":"/api/debate","started_at":"2026-03-21T09:00:00","completed_at":"2026-03-21T09:00:20","summary":{"status":"completed","source_endpoint":"/api/debate","final_conclusion":"符合","final_stance":"支持通过","consensus_rate":1.0,"is_consensus_reached":true,"rounds_taken":0,"evidence_count":4,"agent_count":3},"evidence":[{"rule_id":"BASIC_001","target":"person","category":"基础资格","exec_status":"success","supports_conclusion":true,"result_summary":"人员基础身份有效"},{"rule_id":"PAY_102","target":"social_insurance_payment","category":"缴费状态","exec_status":"success","supports_conclusion":true,"result_summary":"近月均为灵活就业个人缴费"}]}'
),
(
    'sess-D-20260321-001',
    '42090219760310000D',
    'completed',
    '/api/debate_stream',
    '不符合',
    '反对通过',
    0.6667,
    0,
    1,
    3,
    3,
    '2026-03-21 10:00:00',
    '2026-03-21 10:00:42',
    '{"session_id":"sess-D-20260321-001","id_card":"42090219760310000D","evidence_count":3,"rounds_taken":1,"final_conclusion":"不符合","final_stance":"反对通过","consensus_rate":0.6667,"is_consensus_reached":false,"history":[{"round_num":0,"judgments":[{"agent_id":"agent_strict","agent_role":"严格合规Agent","debate_round":0,"conclusion":"不符合","stance":"反对通过","confidence":0.91,"evidence_refs":["EMP_SYNC"],"reasoning":"就业登记与单位缴费尚未完全衔接。","dissent_points":[],"key_finding":"存在就业状态争议"},{"agent_id":"agent_explorer","agent_role":"探索分析Agent","debate_round":0,"conclusion":"数据缺失","stance":"待定","confidence":0.55,"evidence_refs":["CHANGE_LOG"],"reasoning":"需要结合变更日志观察身份切换时间。","dissent_points":["需要更多连续月份证据"],"key_finding":"切换窗口存在灰区"},{"agent_id":"agent_auditor","agent_role":"审计挑战Agent","debate_round":0,"conclusion":"不符合","stance":"反对通过","confidence":0.82,"evidence_refs":["EMP_SYNC","CHANGE_LOG"],"reasoning":"当前证据不足以直接认定稳定困难状态。","dissent_points":[],"key_finding":"系统切换滞后带来风险"}],"total":3,"majority_stance":"反对通过","majority_count":2,"consensus_rate":0.6667,"is_consensus_reached":false},{"round_num":1,"judgments":[{"agent_id":"agent_strict","agent_role":"严格合规Agent","debate_round":1,"conclusion":"不符合","stance":"反对通过","confidence":0.93,"evidence_refs":["EMP_SYNC","CHANGE_LOG"],"reasoning":"多数证据仍指向已进入单位就业轨道。","dissent_points":[],"key_finding":"单位就业迹象增强"},{"agent_id":"agent_explorer","agent_role":"探索分析Agent","debate_round":1,"conclusion":"符合","stance":"支持通过","confidence":0.61,"evidence_refs":["CHANGE_LOG"],"reasoning":"若按变更生效前窗口理解，仍可短期视作困难状态。","dissent_points":["解释口径存在弹性"],"key_finding":"窗口期解释空间"},{"agent_id":"agent_auditor","agent_role":"审计挑战Agent","debate_round":1,"conclusion":"不符合","stance":"反对通过","confidence":0.84,"evidence_refs":["EMP_SYNC","CHANGE_LOG"],"reasoning":"保存谨慎口径更稳妥。","dissent_points":[],"key_finding":"多数意见倾向不通过"}],"total":3,"majority_stance":"反对通过","majority_count":2,"consensus_rate":0.6667,"is_consensus_reached":false}],"status":"completed","source_endpoint":"/api/debate_stream","started_at":"2026-03-21T10:00:00","completed_at":"2026-03-21T10:00:42","summary":{"status":"completed","source_endpoint":"/api/debate_stream","final_conclusion":"不符合","final_stance":"反对通过","consensus_rate":0.6667,"is_consensus_reached":false,"rounds_taken":1,"evidence_count":3,"agent_count":3},"evidence":[{"rule_id":"EMP_SYNC","target":"employment_registration","category":"主动服务","exec_status":"success","supports_conclusion":false,"result_summary":"已存在3月入职登记"},{"rule_id":"CHANGE_LOG","target":"insurance_change_log","category":"主动服务","exec_status":"success","supports_conclusion":null,"result_summary":"3月15日发生101切换"},{"rule_id":"PAY_102","target":"social_insurance_payment","category":"缴费状态","exec_status":"success","supports_conclusion":true,"result_summary":"切换前仍有102个人缴费记录"}]}'
),
(
    'sess-I-20260321-001',
    '42090219700505000I',
    'completed',
    '/api/debate',
    '数据缺失',
    '待定',
    0.6667,
    0,
    0,
    3,
    3,
    '2026-03-21 11:30:00',
    '2026-03-21 11:30:18',
    '{"session_id":"sess-I-20260321-001","id_card":"42090219700505000I","evidence_count":3,"rounds_taken":0,"final_conclusion":"数据缺失","final_stance":"待定","consensus_rate":0.6667,"is_consensus_reached":false,"history":[{"round_num":0,"judgments":[{"agent_id":"agent_strict","agent_role":"严格合规Agent","debate_round":0,"conclusion":"不符合","stance":"反对通过","confidence":0.95,"evidence_refs":["BASIC_LIFE"],"reasoning":"死亡标记直接冲击基础资格。","dissent_points":[],"key_finding":"生命状态异常"},{"agent_id":"agent_explorer","agent_role":"探索分析Agent","debate_round":0,"conclusion":"数据缺失","stance":"待定","confidence":0.58,"evidence_refs":["BASIC_LIFE","PAY_102"],"reasoning":"死亡标记与后续缴费记录明显冲突。","dissent_points":["需要人工核验身份状态"],"key_finding":"数据自相矛盾"},{"agent_id":"agent_auditor","agent_role":"审计挑战Agent","debate_round":0,"conclusion":"数据缺失","stance":"待定","confidence":0.72,"evidence_refs":["BASIC_LIFE","SUBSIDY_LOG"],"reasoning":"继续自动审批风险过高，应转人工。","dissent_points":[],"key_finding":"疑似异常领补"}],"total":3,"majority_stance":"待定","majority_count":2,"consensus_rate":0.6667,"is_consensus_reached":false}],"status":"completed","source_endpoint":"/api/debate","started_at":"2026-03-21T11:30:00","completed_at":"2026-03-21T11:30:18","summary":{"status":"completed","source_endpoint":"/api/debate","final_conclusion":"数据缺失","final_stance":"待定","consensus_rate":0.6667,"is_consensus_reached":false,"rounds_taken":0,"evidence_count":3,"agent_count":3},"evidence":[{"rule_id":"BASIC_LIFE","target":"person","category":"基础资格","exec_status":"success","supports_conclusion":false,"result_summary":"人员生命状态显示死亡"},{"rule_id":"PAY_102","target":"social_insurance_payment","category":"缴费状态","exec_status":"success","supports_conclusion":null,"result_summary":"死亡后仍存在个人缴费记录"},{"rule_id":"SUBSIDY_LOG","target":"subsidy_payment_history","category":"补贴记录","exec_status":"success","supports_conclusion":null,"result_summary":"历史补贴发放与死亡标记冲突"}]}'
);

INSERT INTO agent_debate_log (
    session_id, id_card, debate_round, agent_id, agent_role, conclusion, stance,
    confidence, evidence_refs, reasoning, dissent_points, key_finding,
    round_majority_stance, round_consensus_rate, round_is_consensus_reached
) VALUES
('sess-A-20260321-001', '42090219800101000A', 0, 'agent_strict', '严格合规Agent', '符合', '支持通过', 0.9000, '["BASIC_001","BASIC_002"]', '基础资格与灵活就业缴费记录一致。', '[]', '基础条件齐全', '支持通过', 1.0000, 1),
('sess-A-20260321-001', '42090219800101000A', 0, 'agent_lenient', '宽松业务Agent', '符合', '支持通过', 0.8800, '["BASIC_001","PAY_102"]', '当前画像符合稳定灵活就业状态。', '[]', '无明显排斥信号', '支持通过', 1.0000, 1),
('sess-A-20260321-001', '42090219800101000A', 0, 'agent_auditor', '审计挑战Agent', '符合', '支持通过', 0.7600, '["BASIC_001"]', '虽需持续关注，但当前证据未见异常。', '[]', '证据链完整', '支持通过', 1.0000, 1),
('sess-D-20260321-001', '42090219760310000D', 0, 'agent_strict', '严格合规Agent', '不符合', '反对通过', 0.9100, '["EMP_SYNC"]', '就业登记与单位缴费尚未完全衔接。', '[]', '存在就业状态争议', '反对通过', 0.6667, 0),
('sess-D-20260321-001', '42090219760310000D', 0, 'agent_explorer', '探索分析Agent', '数据缺失', '待定', 0.5500, '["CHANGE_LOG"]', '需要结合变更日志观察身份切换时间。', '["需要更多连续月份证据"]', '切换窗口存在灰区', '反对通过', 0.6667, 0),
('sess-D-20260321-001', '42090219760310000D', 0, 'agent_auditor', '审计挑战Agent', '不符合', '反对通过', 0.8200, '["EMP_SYNC","CHANGE_LOG"]', '当前证据不足以直接认定稳定困难状态。', '[]', '系统切换滞后带来风险', '反对通过', 0.6667, 0),
('sess-D-20260321-001', '42090219760310000D', 1, 'agent_strict', '严格合规Agent', '不符合', '反对通过', 0.9300, '["EMP_SYNC","CHANGE_LOG"]', '多数证据仍指向已进入单位就业轨道。', '[]', '单位就业迹象增强', '反对通过', 0.6667, 0),
('sess-D-20260321-001', '42090219760310000D', 1, 'agent_explorer', '探索分析Agent', '符合', '支持通过', 0.6100, '["CHANGE_LOG"]', '若按变更生效前窗口理解，仍可短期视作困难状态。', '["解释口径存在弹性"]', '窗口期解释空间', '反对通过', 0.6667, 0),
('sess-D-20260321-001', '42090219760310000D', 1, 'agent_auditor', '审计挑战Agent', '不符合', '反对通过', 0.8400, '["EMP_SYNC","CHANGE_LOG"]', '保存谨慎口径更稳妥。', '[]', '多数意见倾向不通过', '反对通过', 0.6667, 0),
('sess-I-20260321-001', '42090219700505000I', 0, 'agent_strict', '严格合规Agent', '不符合', '反对通过', 0.9500, '["BASIC_LIFE"]', '死亡标记直接冲击基础资格。', '[]', '生命状态异常', '待定', 0.6667, 0),
('sess-I-20260321-001', '42090219700505000I', 0, 'agent_explorer', '探索分析Agent', '数据缺失', '待定', 0.5800, '["BASIC_LIFE","PAY_102"]', '死亡标记与后续缴费记录明显冲突。', '["需要人工核验身份状态"]', '数据自相矛盾', '待定', 0.6667, 0),
('sess-I-20260321-001', '42090219700505000I', 0, 'agent_auditor', '审计挑战Agent', '数据缺失', '待定', 0.7200, '["BASIC_LIFE","SUBSIDY_LOG"]', '继续自动审批风险过高，应转人工。', '[]', '疑似异常领补', '待定', 0.6667, 0);


-- 数据捏造完毕 🎭 共 9 个 Persona，5 家企业/单位
