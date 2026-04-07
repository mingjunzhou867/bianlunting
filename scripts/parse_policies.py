"""
政策解析脚本 - 一次性执行,生成所有政策JSON配置文件
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from policy.policy_parser_agent import PolicyParserAgent
from loguru import logger


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始解析政策文件")
    logger.info("=" * 60)
    
    # 创建PolicyParserAgent
    parser = PolicyParserAgent()
    
    # 批量解析docs/policy目录下的所有政策文件
    results = parser.batch_parse_policies(
        policy_dir="docs/policy",
        output_dir="policies"
    )
    
    # 输出结果
    logger.info("=" * 60)
    logger.info("解析结果汇总:")
    for result in results:
        status_icon = "✓" if result['status'] == 'success' else "✗"
        logger.info(f"{status_icon} {result['file']} -> {result.get('policy_id', 'N/A')}")
    
    logger.info("=" * 60)
    logger.info("政策解析完成!")
    logger.info("生成的JSON文件位于: policies/ 目录")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
