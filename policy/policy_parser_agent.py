"""
政策解析Agent - 将政策原文转换为结构化规则
触发时机: 管理员录入新政策时(一次性任务)
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from config.llm_client import llm_chat
from policy.policy_models import PolicyConfig, StructuredRules, PolicyRule
from loguru import logger


def _extract_json(text: str) -> str:
    """从LLM输出中提取JSON字符串(可能被markdown代码块包裹)"""
    # 尝试提取 ```json ... ``` 中的内容
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 尝试找到第一个 { 到最后一个 } 之间的内容
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text


class PolicyParserAgent:
    """
    政策解析Agent
    职责: 读取政策原文,提取结构化规则,生成JSON配置文件
    """
    
    def __init__(self):
        self.temperature = 0.1
    
    def _build_system_prompt(self) -> str:
        """构建System Prompt"""
        return """你是一个政策文本分析专家。你的任务是从政策原文中提取结构化规则。

# 你的任务

1. 识别政策的基本信息(policy_id, policy_name, policy_type等)
2. 提取关键词、别名、口语化表达
3. 提取结构化规则:
   - basic_conditions: 必须满足的基础条件
   - exclusion_conditions: 直接排除的条件
   - inference_rules: 需要推断的规则
   - calculation_rules: 计算规则
4. 生成意图匹配模式(正则表达式)

# 输出格式

你必须输出严格的JSON格式,符合以下结构:

{
  "policy_id": "从原文中提取的policy_id",
  "policy_name": "政策名称",
  "policy_type": "资格认定/金额计算/主动服务等",
  "effective_date": "生效日期(如果有)",
  "expiry_date": null,
  "description": "政策简要描述",
  
  "keywords": ["关键词1", "关键词2", ...],
  "aliases": ["别名1", "别名2", ...],
  "intent_patterns": ["正则模式1", "正则模式2", ...],
  
  "policy_source_files": ["原文件路径"],
  "policy_text": "政策原文全文",
  
  "structured_rules": {
    "basic_conditions": [
      {
        "rule_id": "BASIC_001",
        "description": "规则描述",
        "check_fields": ["字段1", "字段2"],
        "pass_condition": "通过条件描述",
        "sql_template_ref": "BASIC_001"
      }
    ],
    "exclusion_conditions": [
      {
        "rule_id": "EXCL_001",
        "description": "排除规则描述",
        "check_fields": ["字段"],
        "fail_condition": "失败条件描述",
        "sql_template_ref": "EXCL_001"
      }
    ],
    "inference_rules": [
      {
        "rule_id": "INFER_001",
        "description": "推断规则描述",
        "check_logic": "推断逻辑",
        "sql_template_ref": "INFER_001"
      }
    ],
    "calculation_rules": [
      {
        "rule_id": "CALC_001",
        "description": "计算规则描述",
        "formula": "计算公式",
        "sql_template_ref": "CALC_001"
      }
    ]
  },
  
  "evidence_plan_template": {
    "qualification_check": ["BASIC_001", "BASIC_002", ...],
    "amount_calculation": ["CALC_001", "CALC_002", ...]
  },
  
  "notes": ["备注1", "备注2", ...]
}

# 重要提示

1. rule_id命名规范:
   - 基础条件: BASIC_001, BASIC_002, ...
   - 排斥条件: EXCL_001, EXCL_002, ...
   - 推断规则: INFER_001, INFER_002, ...
   - 计算规则: CALC_001, CALC_002, ...

2. 关键词提取要全面:
   - 正式名称
   - 常见别名
   - 口语化表达
   - 行业黑话

3. 意图匹配模式使用正则表达式:
   - 例: "判断.*灵活就业.*补贴"
   - 例: ".*失业.*资格"

4. 只输出JSON,不要有任何其他文字。"""
    
    def parse_policy_file(self, policy_file_path: str) -> PolicyConfig:
        """
        解析单个政策文件
        
        Args:
            policy_file_path: 政策文件路径
            
        Returns:
            PolicyConfig: 解析后的政策配置
        """
        try:
            logger.info(f"[PolicyParserAgent] 开始解析政策文件: {policy_file_path}")
            
            # 读取政策原文
            with open(policy_file_path, 'r', encoding='utf-8') as f:
                policy_text = f.read()
            
            logger.debug(f"[PolicyParserAgent] 政策原文长度: {len(policy_text)} 字符")
            
            # 调用LLM解析
            result_text = llm_chat(
                system_prompt=self._build_system_prompt(),
                user_message=f"请解析以下政策文本:\n\n{policy_text}",
                temperature=self.temperature,
            )
            logger.debug(f"[PolicyParserAgent] LLM解析结果长度: {len(result_text)} 字符")
            
            # 解析JSON
            result_dict = json.loads(_extract_json(result_text))
            
            # 补充policy_source_files
            result_dict['policy_source_files'] = [policy_file_path]
            result_dict['policy_text'] = policy_text
            
            # 转换为PolicyConfig对象
            policy_config = PolicyConfig(**result_dict)
            
            rule_count = (len(policy_config.structured_rules.basic_conditions)
                         + len(policy_config.structured_rules.exclusion_conditions)
                         + len(policy_config.structured_rules.inference_rules)
                         + len(policy_config.structured_rules.calculation_rules))
            logger.info(f"[PolicyParserAgent] 解析成功: policy_id={policy_config.policy_id}, 规则数={rule_count}")
            
            return policy_config
            
        except json.JSONDecodeError as e:
            logger.error(f"[PolicyParserAgent] JSON解析失败: {e}")
            logger.error(f"原始输出: {result_text[:500]}...")
            raise
        
        except Exception as e:
            logger.error(f"[PolicyParserAgent] 政策解析失败: {e}")
            raise
    
    def save_policy_config(self, policy_config: PolicyConfig, output_dir: str = "policies"):
        """
        保存政策配置到JSON文件
        
        Args:
            policy_config: 政策配置对象
            output_dir: 输出目录
        """
        try:
            # 确保输出目录存在
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            filename = f"{policy_config.policy_id}_{policy_config.policy_name}.json"
            file_path = output_path / filename
            
            # 保存JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(
                    policy_config.model_dump(),
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            
            logger.info(f"[PolicyParserAgent] 政策配置已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"[PolicyParserAgent] 保存政策配置失败: {e}")
            raise
    
    def batch_parse_policies(self, policy_dir: str = "docs/policy", output_dir: str = "policies"):
        """
        批量解析政策目录下的所有文件
        
        Args:
            policy_dir: 政策文件目录
            output_dir: 输出目录
        """
        policy_path = Path(policy_dir)
        
        if not policy_path.exists():
            logger.error(f"[PolicyParserAgent] 政策目录不存在: {policy_dir}")
            return
        
        # 获取所有.txt文件
        policy_files = list(policy_path.glob("*.txt"))
        logger.info(f"[PolicyParserAgent] 找到 {len(policy_files)} 个政策文件")
        
        results = []
        for policy_file in policy_files:
            try:
                logger.info(f"[PolicyParserAgent] 正在处理: {policy_file.name}")
                
                # 解析政策
                policy_config = self.parse_policy_file(str(policy_file))
                
                # 保存配置
                self.save_policy_config(policy_config, output_dir)
                
                results.append({
                    "file": policy_file.name,
                    "policy_id": policy_config.policy_id,
                    "status": "success"
                })
                
            except Exception as e:
                logger.error(f"[PolicyParserAgent] 处理失败: {policy_file.name}, error={e}")
                results.append({
                    "file": policy_file.name,
                    "policy_id": None,
                    "status": "failed",
                    "error": str(e)
                })
        
        # 输出汇总
        success_count = sum(1 for r in results if r['status'] == 'success')
        logger.info(f"[PolicyParserAgent] 批量解析完成: 成功 {success_count}/{len(results)}")
        
        return results
