"""
政策路由器 - 根据 policy_id 加载对应政策配置
数据源: policy_master 表（数据库）
"""
import json
from pathlib import Path
from typing import Dict, Optional, List
from loguru import logger
from sqlalchemy import text

from policy.policy_models import PolicyConfig
from config.database import get_session

_POLICIES_DIR = Path(__file__).resolve().parent.parent / "policies"

# 模块级缓存: 第一次调用时加载, 后续直接读取
_policy_cache: Dict[str, PolicyConfig] = {}
_loaded = False


def _load_all_policies():
    """从数据库 policy_master 表加载所有政策"""
    global _loaded
    if _loaded:
        return

    try:
        with get_session() as session:
            # 加载政策基础信息
            policy_query = text("""
                SELECT policy_id, policy_name, policy_type, policy_description
                FROM policy_master
                WHERE is_active = 1
                ORDER BY policy_id
            """)
            policy_rows = session.execute(policy_query).fetchall()

            for policy_row in policy_rows:
                # 加载该政策的规则
                rule_query = text("""
                    SELECT rule_id, rule_name, rule_description, rule_type, sql_template
                    FROM rule_definitions
                    WHERE policy_id = :policy_id AND is_enabled = '1'
                    ORDER BY priority ASC, rule_id ASC
                """)
                rule_rows = session.execute(rule_query, {"policy_id": policy_row.policy_id}).fetchall()

                # 按 rule_type 分类
                from policy.policy_models import PolicyRule, StructuredRules
                basic_conditions = []
                exclusion_conditions = []
                calculation_rules = []

                for rule_row in rule_rows:
                    policy_rule = PolicyRule(
                        rule_id=rule_row.rule_id,
                        description=f"{rule_row.rule_name}: {rule_row.rule_description or ''}",
                        sql_template_ref=rule_row.sql_template,
                    )
                    if rule_row.rule_type == "必须满足":
                        basic_conditions.append(policy_rule)
                    elif rule_row.rule_type == "必须排除":
                        exclusion_conditions.append(policy_rule)
                    elif rule_row.rule_type == "灵活评判":
                        calculation_rules.append(policy_rule)

                config = PolicyConfig(
                    policy_id=policy_row.policy_id,
                    policy_name=policy_row.policy_name,
                    policy_type=policy_row.policy_type,
                    description=policy_row.policy_description or "",
                    keywords=[],
                    aliases=[],
                    structured_rules=StructuredRules(
                        basic_conditions=basic_conditions,
                        exclusion_conditions=exclusion_conditions,
                        calculation_rules=calculation_rules,
                    ),
                )
                _policy_cache[config.policy_id] = config
                logger.debug(f"[PolicyRouter] 已加载: {config.policy_id} ({config.policy_name}), 规则数={len(rule_rows)}")

        logger.info(f"[PolicyRouter] 从数据库加载 {len(_policy_cache)} 个政策配置")
    except Exception as e:
        logger.error(f"[PolicyRouter] 数据库加载失败: {e}")

    _loaded = True


# 【暂时弃用，已改成数据库读取】
# def _load_all_policies():
#     """从 policies/ 目录扫描并缓存全部 JSON 文件"""
#     global _loaded
#     if _loaded:
#         return
#
#     if not _POLICIES_DIR.exists():
#         logger.warning(f"[PolicyRouter] policies 目录不存在: {_POLICIES_DIR}")
#         _loaded = True
#         return
#
#     for json_file in _POLICIES_DIR.glob("*.json"):
#         try:
#             with open(json_file, "r", encoding="utf-8") as f:
#                 raw = json.load(f)
#             config = PolicyConfig(**raw)
#             _policy_cache[config.policy_id] = config
#             logger.debug(f"[PolicyRouter] 已加载: {config.policy_id} ({config.policy_name}) <- {json_file.name}")
#         except Exception as e:
#             logger.error(f"[PolicyRouter] 加载失败 {json_file.name}: {e}")
#
#     logger.info(f"[PolicyRouter] 共加载 {len(_policy_cache)} 个政策配置")
#     _loaded = True


def reload_policies():
    """强制重新加载（管理员重新跑 parse_policies 后调用）"""
    global _loaded
    _policy_cache.clear()
    _loaded = False
    _load_all_policies()


def get_policy(policy_id: str) -> Optional[PolicyConfig]:
    """按 policy_id 获取政策配置"""
    _load_all_policies()
    return _policy_cache.get(policy_id)


def list_policies() -> List[Dict]:
    """返回所有已加载政策的摘要列表（供前端选择/IntentAgent参考）"""
    _load_all_policies()
    return [
        {
            "policy_id": cfg.policy_id,
            "policy_name": cfg.policy_name,
            "policy_type": cfg.policy_type,
            "description": cfg.description,
            "keywords": cfg.keywords,
            "aliases": cfg.aliases,
        }
        for cfg in _policy_cache.values()
    ]


def get_all_policy_configs() -> Dict[str, PolicyConfig]:
    """返回完整缓存（内部使用）"""
    _load_all_policies()
    return dict(_policy_cache)
