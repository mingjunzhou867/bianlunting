"""
sql_templates.py — 规则 SQL 模板注册表

将 规则.txt 中的每一条规则映射为可执行的参数化 SQL。
Agent 通过 rule_id 请求取证，EvidenceCollector 查找此表执行对应 SQL。

规则 ID 命名约定：
  BASIC_XXX   → 基础条件（必须满足）
  EXCL_XXX    → 直接排斥条件
  INFER_XXX   → 合理推断条件
  CALC_XXX    → 功能二：额度精算
  PROACT_XXX  → 功能三：主动服务

SQL 占位符：
  :id_card       → 被查询人员身份证号
  :system_date   → 系统模拟当前日期（来自 settings.system_date）
"""

# 每条规则的结构：
# {
#   "target":      str,           取证目标描述（自然语言）
#   "category":    str,           所属功能类别
#   "sql":         str,           参数化 SQL 模板
#   "needs_id_card": bool,        是否需要 :id_card 参数
#   "auto_verdict": str | None,   'pass_if_data' | 'fail_if_data' | None
#       pass_if_data  → 查到数据说明支持通过（基础条件有记录=好）
#       fail_if_data  → 查到数据说明触发排斥（排斥条件有记录=坏）
#       None          → 需 Agent 自行判断
# }

RULE_REGISTRY: dict[str, dict] = {

    # ----------------------------------------------------------
    # 基础条件（全部必须满足）
    # ----------------------------------------------------------

    "BASIC_001": {
        "target": "核查人员生存状态和系统数据有效性",
        "category": "基础条件",
        "sql": """
            SELECT id_card, name, gender, birth_date,
                   life_status, system_status, hukou_region
            FROM person
            WHERE id_card = :id_card
        """,
        "needs_id_card": True,
        "auto_verdict": None,  # 需检查 life_status='生存' AND system_status='1'
    },

    "BASIC_002": {
        "target": "核查户籍是否为孝感市市辖区（市直户籍）",
        "category": "基础条件",
        "sql": """
            SELECT id_card, hukou_region
            FROM person
            WHERE id_card = :id_card
              AND hukou_region = '孝感市市辖区'
        """,
        "needs_id_card": True,
        "auto_verdict": "pass_if_data",
    },

    "BASIC_003": {
        "target": "核查是否有有效的灵活就业登记记录",
        "category": "基础条件",
        "sql": """
            SELECT record_id, employment_form, employment_date,
                   contract_start_date, sync_date
            FROM employment_registration
            WHERE id_card = :id_card
              AND employment_form = '灵活就业'
              AND is_valid = '1'
            ORDER BY employment_date DESC
            LIMIT 1
        """,
        "needs_id_card": True,
        "auto_verdict": "pass_if_data",
    },

    "BASIC_004": {
        "target": "核查是否有有效的失业登记记录",
        "category": "基础条件",
        "sql": """
            SELECT record_id, unemployment_date, unemployment_reason,
                   register_date, cancel_date
            FROM unemployment_registration
            WHERE id_card = :id_card
              AND is_valid = '1'
            ORDER BY register_date DESC
            LIMIT 1
        """,
        "needs_id_card": True,
        "auto_verdict": "pass_if_data",
    },

    "BASIC_005": {
        "target": "核查是否有有效的就业困难人员认定记录及认定类别",
        "category": "基础条件",
        "sql": """
            SELECT cert_id, hardship_category, apply_date,
                   certify_org, cancel_date, cancel_reason
            FROM hardship_certification
            WHERE id_card = :id_card
              AND is_valid = '1'
            ORDER BY apply_date DESC
            LIMIT 1
        """,
        "needs_id_card": True,
        "auto_verdict": "pass_if_data",
    },

    # ----------------------------------------------------------
    # 直接排斥条件（查到即不通过）
    # ----------------------------------------------------------

    "EXCL_001": {
        "target": "排斥检查：person表工商身份是否为个体工商户",
        "category": "排斥条件",
        "sql": """
            SELECT id_card, name, business_role
            FROM person
            WHERE id_card = :id_card
              AND business_role = '个体工商户'
        """,
        "needs_id_card": True,
        "auto_verdict": "fail_if_data",
    },

    "EXCL_002": {
        "target": "排斥检查：工商库中是否登记为有效个体工商户法人",
        "category": "排斥条件",
        "sql": """
            SELECT company_id, company_name, company_type, is_valid
            FROM company_info
            WHERE legal_person_id_card = :id_card
              AND company_type = '个体工商户'
              AND is_valid = '1'
        """,
        "needs_id_card": True,
        "auto_verdict": "fail_if_data",
    },

    "EXCL_003": {
        "target": "排斥检查：person表工商身份是否为企业法人",
        "category": "排斥条件",
        "sql": """
            SELECT id_card, name, business_role
            FROM person
            WHERE id_card = :id_card
              AND business_role = '企业法人'
        """,
        "needs_id_card": True,
        "auto_verdict": "fail_if_data",
    },

    "EXCL_004": {
        "target": "排斥检查：工商库中是否登记为有效企业法定代表人",
        "category": "排斥条件",
        "sql": """
            SELECT company_id, company_name, company_type, is_valid
            FROM company_info
            WHERE legal_person_id_card = :id_card
              AND company_type = '企业'
              AND is_valid = '1'
        """,
        "needs_id_card": True,
        "auto_verdict": "fail_if_data",
    },

    "EXCL_005": {
        "target": "排斥检查：是否存在有效的企业股东记录",
        "category": "排斥条件",
        "sql": """
            SELECT cs.relation_id, cs.company_id, ci.company_name,
                   cs.share_ratio, cs.is_valid
            FROM company_shareholder cs
            LEFT JOIN company_info ci ON cs.company_id = ci.company_id
            WHERE cs.id_card = :id_card
              AND cs.is_valid = '1'
        """,
        "needs_id_card": True,
        "auto_verdict": "fail_if_data",
    },

    "EXCL_006": {
        "target": "排斥检查：股东记录全量查询（含已注销，用于辩论数据一致性）",
        "category": "排斥条件",
        "sql": """
            SELECT cs.relation_id, cs.company_id, ci.company_name,
                   cs.share_ratio, cs.is_valid AS shareholder_valid,
                   ci.is_valid AS company_valid
            FROM company_shareholder cs
            LEFT JOIN company_info ci ON cs.company_id = ci.company_id
            WHERE cs.id_card = :id_card
            ORDER BY cs.is_valid DESC
        """,
        "needs_id_card": True,
        "auto_verdict": None,  # 需 Agent 判断新旧记录并存时的结论
    },

    "EXCL_007": {
        "target": "排斥检查：退休年龄判断基础数据（出生日期、性别）",
        "category": "排斥条件",
        "sql": """
            SELECT id_card, name, gender, birth_date,
                CASE
                    WHEN gender = '男' THEN DATE_ADD(birth_date, INTERVAL 60 YEAR)
                    WHEN gender = '女' THEN DATE_ADD(birth_date, INTERVAL 55 YEAR)
                END AS retirement_date_55_60,
                CASE
                    WHEN gender = '女' THEN DATE_ADD(birth_date, INTERVAL 50 YEAR)
                    ELSE NULL
                END AS retirement_date_50_female,
                TIMESTAMPDIFF(YEAR, birth_date, :system_date) AS current_age
            FROM person
            WHERE id_card = :id_card
        """,
        "needs_id_card": True,
        "auto_verdict": None,  # 退休年龄取50/55/60需结合历史岗位，交给Agent判断
    },

    "EXCL_008": {
        "target": "排斥检查：申领期间医保是否存在单位缴纳记录（310类型，101状态）",
        "category": "排斥条件",
        "sql": """
            SELECT pay_month, insurance_type, insurer_status,
                   pay_base, company_id
            FROM social_insurance_payment
            WHERE id_card = :id_card
              AND insurance_type = '310'
              AND insurer_status = '101'
              AND is_valid = '1'
            ORDER BY pay_month DESC
        """,
        "needs_id_card": True,
        "auto_verdict": "fail_if_data",
    },

    "EXCL_009": {
        "target": "排斥检查：是否缺失灵活就业养老社保缴费记录（110类型，102状态）",
        "category": "排斥条件",
        "sql": """
            SELECT pay_month, insurance_type, insurer_status, pay_base
            FROM social_insurance_payment
            WHERE id_card = :id_card
              AND insurance_type = '110'
              AND insurer_status = '102'
              AND is_valid = '1'
            ORDER BY pay_month DESC
        """,
        "needs_id_card": True,
        "auto_verdict": None,  # no_data → 触发排斥；有数据 → 需看具体月份连续性
    },

    # ----------------------------------------------------------
    # 合理推断条件
    # ----------------------------------------------------------

    "INFER_001": {
        "target": "推断：企业职工社会保险全量记录（含单位性质，用于识别财政供养）",
        "category": "合理推断",
        "sql": """
            SELECT sip.pay_month, sip.insurance_type, sip.insurer_status,
                   sip.pay_base, sip.company_id,
                   ci.company_name, ci.company_type
            FROM social_insurance_payment sip
            LEFT JOIN company_info ci ON sip.company_id = ci.company_id
            WHERE sip.id_card = :id_card
              AND sip.is_valid = '1'
            ORDER BY sip.pay_month DESC, sip.insurance_type
        """,
        "needs_id_card": True,
        "auto_verdict": None,
    },

    "INFER_002": {
        "target": "推断：是否存在机关/事业单位缴费记录（财政供养/机关事业人员核查）",
        "category": "合理推断",
        "sql": """
            SELECT sip.pay_month, sip.insurance_type, sip.insurer_status,
                   ci.company_name, ci.company_type
            FROM social_insurance_payment sip
            JOIN company_info ci ON sip.company_id = ci.company_id
            WHERE sip.id_card = :id_card
              AND ci.company_type IN ('机关单位', '事业单位')
              AND sip.is_valid = '1'
            ORDER BY sip.pay_month DESC
        """,
        "needs_id_card": True,
        "auto_verdict": "fail_if_data",
    },

    # ----------------------------------------------------------
    # 功能二：额度精算
    # ----------------------------------------------------------

    "CALC_001": {
        "target": "精算：历史补贴发放明细（查询所有领取记录）",
        "category": "额度计算",
        "sql": """
            SELECT policy_code, first_enjoy_month,
                   apply_start_month, apply_end_month,
                   grant_months, grant_amount, grant_date
            FROM subsidy_payment_history
            WHERE id_card = :id_card
              AND is_valid = '1'
            ORDER BY first_enjoy_month ASC
        """,
        "needs_id_card": True,
        "auto_verdict": None,
    },

    "CALC_002": {
        "target": "精算：历史已领补贴总月数",
        "category": "额度计算",
        "sql": """
            SELECT COALESCE(SUM(grant_months), 0) AS total_received_months
            FROM subsidy_payment_history
            WHERE id_card = :id_card
              AND is_valid = '1'
        """,
        "needs_id_card": True,
        "auto_verdict": None,
    },

    "CALC_003": {
        "target": "精算：出生日期、性别及估算退休日期与剩余月数（功能二情况1/2依据）",
        "category": "额度计算",
        "sql": """
            SELECT id_card, name, gender, birth_date,
                CASE
                    WHEN gender = '男' THEN DATE_ADD(birth_date, INTERVAL 60 YEAR)
                    WHEN gender = '女' THEN DATE_ADD(birth_date, INTERVAL 55 YEAR)
                END AS estimated_retirement_date,
                TIMESTAMPDIFF(MONTH,
                    :system_date,
                    CASE
                        WHEN gender = '男' THEN DATE_ADD(birth_date, INTERVAL 60 YEAR)
                        WHEN gender = '女' THEN DATE_ADD(birth_date, INTERVAL 55 YEAR)
                    END
                ) AS months_to_retirement,
                TIMESTAMPDIFF(MONTH, birth_date, :system_date) AS age_in_months
            FROM person
            WHERE id_card = :id_card
        """,
        "needs_id_card": True,
        "auto_verdict": None,
    },

    "CALC_004": {
        "target": "精算：本人灵活就业养老社保缴费月数统计（功能二情况4依据）",
        "category": "额度计算",
        "sql": """
            SELECT COUNT(DISTINCT pay_month) AS flex_pay_months,
                   MIN(pay_month) AS first_pay_month,
                   MAX(pay_month) AS last_pay_month
            FROM social_insurance_payment
            WHERE id_card = :id_card
              AND insurance_type = '110'
              AND insurer_status = '102'
              AND is_valid = '1'
        """,
        "needs_id_card": True,
        "auto_verdict": None,
    },

    "CALC_005": {
        "target": "精算：困难认定类别（判断是否为高校毕业生，影响功能二情况3）",
        "category": "额度计算",
        "sql": """
            SELECT hardship_category, apply_date
            FROM hardship_certification
            WHERE id_card = :id_card
              AND is_valid = '1'
            ORDER BY apply_date DESC
            LIMIT 1
        """,
        "needs_id_card": True,
        "auto_verdict": None,
    },

    # ----------------------------------------------------------
    # 功能三：主动服务（部分不需要 id_card，扫描全库）
    # ----------------------------------------------------------

    "PROACT_001": {
        "target": "主动服务：查询本市近期企业增员名单（近30天入职的全日制人员）",
        "category": "主动服务",
        "sql": """
            SELECT er.id_card, p.name, p.gender, p.birth_date,
                   p.hukou_region, p.life_status,
                   er.employment_date, er.sync_date,
                   er.company_id, ci.company_name,
                   TIMESTAMPDIFF(YEAR, p.birth_date, :system_date) AS current_age
            FROM employment_registration er
            JOIN person p ON er.id_card = p.id_card
            JOIN company_info ci ON er.company_id = ci.company_id
            WHERE er.is_valid = '1'
              AND er.employment_form = '全日制用工'
              AND er.employment_date >= DATE_SUB(:system_date, INTERVAL 30 DAY)
              AND p.life_status = '生存'
              AND p.system_status = '1'
            ORDER BY er.employment_date DESC
        """,
        "needs_id_card": False,
        "auto_verdict": None,
    },

    "PROACT_002": {
        "target": "主动服务：识别增员名单中的疑似就业困难人员（无困难认定+年龄达到门槛）",
        "category": "主动服务",
        "sql": """
            SELECT p.id_card, p.name, p.gender, p.birth_date,
                   TIMESTAMPDIFF(YEAR, p.birth_date, :system_date) AS current_age,
                   er.employment_date, er.company_id, ci.company_name,
                   hc.cert_id AS existing_hardship_cert,
                   ur.record_id AS existing_unemployment_reg
            FROM employment_registration er
            JOIN person p ON er.id_card = p.id_card
            JOIN company_info ci ON er.company_id = ci.company_id
            LEFT JOIN hardship_certification hc
                ON p.id_card = hc.id_card AND hc.is_valid = '1'
            LEFT JOIN unemployment_registration ur
                ON p.id_card = ur.id_card AND ur.is_valid = '1'
            WHERE er.is_valid = '1'
              AND er.employment_form = '全日制用工'
              AND er.employment_date >= DATE_SUB(:system_date, INTERVAL 30 DAY)
              AND p.life_status = '生存'
              AND p.system_status = '1'
              AND p.hukou_region = '孝感市市辖区'
              AND (
                  (p.gender = '女' AND TIMESTAMPDIFF(YEAR, p.birth_date, :system_date) >= 40)
                  OR
                  (p.gender = '男' AND TIMESTAMPDIFF(YEAR, p.birth_date, :system_date) >= 50)
              )
            ORDER BY er.employment_date DESC
        """,
        "needs_id_card": False,
        "auto_verdict": None,
    },

    "PROACT_003": {
        "target": "主动服务：查询指定人员的险种变更记录（社保身份切换追踪）",
        "category": "主动服务",
        "sql": """
            SELECT change_id, insurance_type,
                   old_status, new_status, event_date,
                   related_company_id
            FROM insurance_change_log
            WHERE id_card = :id_card
              AND is_valid = '1'
            ORDER BY event_date DESC
        """,
        "needs_id_card": True,
        "auto_verdict": None,
    },

    "PROACT_004": {
        "target": "主动服务：指定人员所有社保缴费记录（全量，含历史单位缴费）",
        "category": "主动服务",
        "sql": """
            SELECT sip.pay_month, sip.insurance_type, sip.insurer_status,
                   sip.pay_base, sip.company_id,
                   ci.company_name, ci.company_type
            FROM social_insurance_payment sip
            LEFT JOIN company_info ci ON sip.company_id = ci.company_id
            WHERE sip.id_card = :id_card
              AND sip.is_valid = '1'
            ORDER BY sip.pay_month DESC, sip.insurance_type
        """,
        "needs_id_card": True,
        "auto_verdict": None,
    },
}

# 按类别分组的快捷索引（Agent 可按场景批量请求）
RULES_BY_CATEGORY: dict[str, list[str]] = {}
for _rule_id, _rule in RULE_REGISTRY.items():
    _cat = _rule["category"]
    RULES_BY_CATEGORY.setdefault(_cat, []).append(_rule_id)

# 功能一资格判定所需的全量规则（按执行优先级排列：排斥 > 基础 > 推断）
QUALIFICATION_RULE_IDS: list[str] = [
    # 先跑排斥条件（命中即停）
    "EXCL_001", "EXCL_002", "EXCL_003", "EXCL_004",
    "EXCL_005", "EXCL_006", "EXCL_007", "EXCL_008", "EXCL_009",
    # 再跑基础条件
    "BASIC_001", "BASIC_002", "BASIC_003", "BASIC_004", "BASIC_005",
    # 最后跑推断
    "INFER_001", "INFER_002",
]

# 功能二精算所需规则
CALCULATION_RULE_IDS: list[str] = [
    "CALC_001", "CALC_002", "CALC_003", "CALC_004", "CALC_005",
]

# 功能三主动服务所需规则
PROACTIVE_RULE_IDS: list[str] = [
    "PROACT_001", "PROACT_002", "PROACT_003", "PROACT_004",
]
