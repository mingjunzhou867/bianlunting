-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: localhost    Database: bysj
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `agent_debate_log`
--

DROP TABLE IF EXISTS `agent_debate_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `agent_debate_log` (
  `log_id` bigint NOT NULL AUTO_INCREMENT,
  `session_id` varchar(36) NOT NULL COMMENT '对应 debate_session.session_id',
  `id_card` varchar(18) NOT NULL COMMENT '被审查人员身份证号',
  `debate_round` int NOT NULL COMMENT '辩论轮次',
  `agent_id` varchar(50) NOT NULL COMMENT 'Agent唯一标识',
  `agent_role` varchar(100) NOT NULL COMMENT 'Agent展示名称',
  `conclusion` varchar(20) NOT NULL COMMENT '该Agent本轮结论',
  `stance` varchar(20) NOT NULL COMMENT '该Agent本轮立场',
  `confidence` decimal(5,4) NOT NULL COMMENT '该Agent本轮置信度',
  `evidence_refs` longtext NOT NULL COMMENT '引用证据ID列表(JSON字符串)',
  `reasoning` text NOT NULL COMMENT '该Agent本轮推理文本',
  `dissent_points` longtext NOT NULL COMMENT '该Agent本轮异议点列表(JSON字符串)',
  `key_finding` text COMMENT '该Agent本轮关键发现',
  `round_majority_stance` varchar(20) NOT NULL COMMENT '该轮多数派立场',
  `round_consensus_rate` decimal(5,4) NOT NULL COMMENT '该轮共识率',
  `round_is_consensus_reached` tinyint(1) NOT NULL DEFAULT '0' COMMENT '该轮是否达成共识',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '持久化时间',
  PRIMARY KEY (`log_id`),
  KEY `idx_agent_debate_session` (`session_id`),
  KEY `idx_agent_debate_idcard` (`id_card`),
  KEY `idx_agent_debate_round` (`session_id`,`debate_round`),
  CONSTRAINT `fk_agent_debate_session` FOREIGN KEY (`session_id`) REFERENCES `debate_session` (`session_id`)
) ENGINE=InnoDB AUTO_INCREMENT=68 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='逐轮逐Agent辩论记录表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `company_info`
--

DROP TABLE IF EXISTS `company_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `company_info` (
  `company_id` varchar(50) NOT NULL COMMENT '企业统一信用代码/机构代码',
  `company_name` varchar(200) NOT NULL COMMENT '单位名称',
  `legal_person_id_card` varchar(18) DEFAULT NULL COMMENT '法定代表人身份证号',
  `company_type` varchar(50) DEFAULT '企业' COMMENT '单位性质(企业/机关单位/事业单位/社会团体/个体工商户)',
  `is_valid` varchar(10) DEFAULT '1' COMMENT '有效标志(1/0)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`company_id`),
  KEY `idx_company_type` (`company_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='企业基础信息表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `company_shareholder`
--

DROP TABLE IF EXISTS `company_shareholder`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `company_shareholder` (
  `relation_id` bigint NOT NULL AUTO_INCREMENT,
  `company_id` varchar(50) NOT NULL COMMENT '企业代码',
  `id_card` varchar(18) NOT NULL COMMENT '股东身份证号',
  `share_ratio` decimal(5,2) DEFAULT NULL COMMENT '持股比例(%)',
  `is_valid` varchar(10) DEFAULT '1' COMMENT '有效标志(1/0)',
  PRIMARY KEY (`relation_id`),
  KEY `idx_company` (`company_id`),
  KEY `idx_shareholder` (`id_card`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='企业股东关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `debate_session`
--

DROP TABLE IF EXISTS `debate_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `debate_session` (
  `session_id` varchar(36) NOT NULL COMMENT '一次成功辩论的唯一会话ID',
  `id_card` varchar(18) NOT NULL COMMENT '被审查人员身份证号',
  `policy_id` varchar(50) DEFAULT 'POLICY_001' COMMENT '本次辩论对应的政策ID',
  `status` varchar(20) NOT NULL COMMENT '当前仅保存 completed',
  `source_endpoint` varchar(32) NOT NULL COMMENT '来源接口，如 /api/debate 或 /api/debate_stream',
  `final_conclusion` varchar(20) NOT NULL COMMENT '最终结论：符合/不符合/数据缺失',
  `final_stance` varchar(20) NOT NULL COMMENT '最终多数派立场：支持通过/反对通过/待定',
  `consensus_rate` decimal(5,4) NOT NULL COMMENT '最终轮次共识率',
  `is_consensus_reached` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否在轮次内自发达成共识',
  `rounds_taken` int NOT NULL COMMENT '最终采用的轮次编号',
  `evidence_count` int NOT NULL COMMENT '本次会话使用的证据条数',
  `agent_count` int NOT NULL COMMENT '参与辩论的Agent数量',
  `started_at` datetime NOT NULL COMMENT '会话开始时间',
  `completed_at` datetime NOT NULL COMMENT '会话完成时间',
  `snapshot_payload` longtext NOT NULL COMMENT '完整会话快照(JSON字符串)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '持久化时间',
  PRIMARY KEY (`session_id`),
  KEY `idx_debate_session_idcard` (`id_card`),
  KEY `idx_debate_session_completed` (`completed_at`),
  KEY `idx_debate_session_conclusion` (`final_conclusion`),
  KEY `idx_debate_session_policy` (`policy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='成功辩论会话总表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `employment_registration`
--

DROP TABLE IF EXISTS `employment_registration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employment_registration` (
  `record_id` bigint NOT NULL AUTO_INCREMENT,
  `id_card` varchar(18) NOT NULL COMMENT '身份证号',
  `company_id` varchar(50) DEFAULT NULL COMMENT '录用单位编号',
  `employment_form` varchar(50) DEFAULT NULL COMMENT '就业形式(如:灵活就业、全日制用工)',
  `employment_date` date DEFAULT NULL COMMENT '合同/协议约定的就业开始日期',
  `contract_start_date` date DEFAULT NULL COMMENT '合同起始日期',
  `contract_end_date` date DEFAULT NULL COMMENT '合同终止日期',
  `sync_date` date DEFAULT NULL COMMENT '增员数据同步入系统日期(企业报备时间)',
  `is_valid` varchar(10) DEFAULT '1' COMMENT '有效标志(1/0)',
  PRIMARY KEY (`record_id`),
  KEY `idx_emp_idcard` (`id_card`),
  KEY `idx_emp_sync` (`sync_date`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='就业登记表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `hardship_certification`
--

DROP TABLE IF EXISTS `hardship_certification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `hardship_certification` (
  `cert_id` bigint NOT NULL AUTO_INCREMENT,
  `id_card` varchar(18) NOT NULL COMMENT '身份证号',
  `hardship_category` varchar(100) DEFAULT NULL COMMENT '就业困难人员类别(如:大龄失业人员/残疾人员/离校2年内未就业的高校毕业生)',
  `apply_date` date DEFAULT NULL COMMENT '困难认定申请日期',
  `certify_org` varchar(100) DEFAULT NULL COMMENT '认定机构',
  `cancel_date` date DEFAULT NULL COMMENT '认定退出注销日期',
  `cancel_reason` varchar(255) DEFAULT NULL COMMENT '退出原因',
  `is_valid` varchar(10) DEFAULT '1' COMMENT '有效标志(1有效/0失效)',
  PRIMARY KEY (`cert_id`),
  KEY `idx_hardship_idcard` (`id_card`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='就业困难认定表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `insurance_change_log`
--

DROP TABLE IF EXISTS `insurance_change_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `insurance_change_log` (
  `change_id` bigint NOT NULL AUTO_INCREMENT,
  `id_card` varchar(18) NOT NULL COMMENT '发生变更的身份证号',
  `insurance_type` varchar(20) NOT NULL COMMENT '发生变更的险种类型(110/310)',
  `old_status` varchar(20) DEFAULT NULL COMMENT '变更前参保身份(如:102 个人)',
  `new_status` varchar(20) DEFAULT NULL COMMENT '变更后参保身份(如:101 单位)',
  `event_date` date NOT NULL COMMENT '系统变更发生日期(真实业务流转日期)',
  `related_company_id` varchar(50) DEFAULT NULL COMMENT '引发变更的单位编号(如有)',
  `is_valid` varchar(10) DEFAULT '1' COMMENT '数据是否有效(1/0)',
  PRIMARY KEY (`change_id`),
  KEY `idx_change_idcard` (`id_card`),
  KEY `idx_change_date` (`event_date`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='险种参保记录变更事件表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `person`
--

DROP TABLE IF EXISTS `person`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `person` (
  `id_card` varchar(18) NOT NULL COMMENT '身份证号(全局统一标识)',
  `name` varchar(50) NOT NULL COMMENT '姓名',
  `gender` varchar(10) DEFAULT NULL COMMENT '性别',
  `birth_date` date NOT NULL COMMENT '出生日期',
  `hukou_region` varchar(100) DEFAULT NULL COMMENT '户籍所在地编号/名称(如:孝感市市辖区)',
  `life_status` varchar(10) DEFAULT '生存' COMMENT '生存状态(生存/死亡)',
  `system_status` varchar(10) DEFAULT '1' COMMENT '数据标识(1有效/0无效)',
  `business_role` varchar(50) DEFAULT NULL COMMENT '工商注册身份(个体工商户/企业法人/NULL=普通居民)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '系统记录时间',
  PRIMARY KEY (`id_card`),
  KEY `idx_hukou` (`hukou_region`),
  KEY `idx_business_role` (`business_role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='人员主表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `policy_master`
--

DROP TABLE IF EXISTS `policy_master`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `policy_master` (
  `policy_id` varchar(50) NOT NULL COMMENT '政策唯一标识',
  `policy_name` varchar(200) NOT NULL COMMENT '政策名称',
  `policy_type` varchar(50) NOT NULL COMMENT '政策类型（资格认定/额度计算/主动服务）',
  `policy_description` text COMMENT '政策简介',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '是否启用',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`policy_id`),
  KEY `idx_policy_type` (`policy_type`),
  KEY `idx_policy_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='政策主表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rule_definitions`
--

DROP TABLE IF EXISTS `rule_definitions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rule_definitions` (
  `rule_id` varchar(50) NOT NULL COMMENT '规则主键(业务编号)',
  `policy_id` varchar(50) NOT NULL DEFAULT 'POLICY_001' COMMENT '规则所属政策ID',
  `rule_name` varchar(100) NOT NULL COMMENT '规则名称(中文业务语义)',
  `rule_description` text COMMENT '规则详细描述及判断逻辑',
  `rule_type` enum('必须满足','必须排除','灵活评判') NOT NULL DEFAULT '灵活评判' COMMENT '规则性质：必须满足=硬性通过条件，必须排除=硬性拒绝条件，灵活评判=Agent推理',
  `sql_template` text NOT NULL COMMENT '包含占位符(如 :id_card)的SQL查询模板',
  `scenario_category` varchar(50) DEFAULT NULL COMMENT '适用场景(基础资格/排斥条件/额度计算/主动服务)',
  `priority` int DEFAULT '100' COMMENT '规则执行优先级(数字越小越优先，排斥条件建议设1-10)',
  `is_enabled` varchar(10) DEFAULT '1' COMMENT '是否启用本条规则校验(1/0)',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`rule_id`),
  KEY `idx_rule_policy_type` (`policy_id`,`rule_type`,`priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='智能体驱动规则表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `social_insurance_payment`
--

DROP TABLE IF EXISTS `social_insurance_payment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `social_insurance_payment` (
  `payment_id` bigint NOT NULL AUTO_INCREMENT,
  `id_card` varchar(18) NOT NULL COMMENT '身份证号',
  `company_id` varchar(50) DEFAULT NULL COMMENT '代缴企业编号(灵活就业则为空)',
  `insurance_type` varchar(20) NOT NULL COMMENT '险种类型(110养老, 310医保)',
  `pay_month` varchar(6) NOT NULL COMMENT '费款所属期(YYYYMM)',
  `insurer_status` varchar(20) DEFAULT NULL COMMENT '参保身份(101单位缴费/102个人灵活就业)',
  `pay_base` decimal(10,2) DEFAULT NULL COMMENT '缴费基数',
  `is_valid` varchar(10) DEFAULT '1' COMMENT '有效标志(1/0)',
  PRIMARY KEY (`payment_id`),
  KEY `idx_payment_idcard_month` (`id_card`,`pay_month`),
  KEY `idx_payment_type` (`insurance_type`),
  KEY `idx_payment_status` (`insurer_status`)
) ENGINE=InnoDB AUTO_INCREMENT=63 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='社保缴费流水表(含养老/医保)';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `subsidy_payment_history`
--

DROP TABLE IF EXISTS `subsidy_payment_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subsidy_payment_history` (
  `payment_id` bigint NOT NULL AUTO_INCREMENT,
  `id_card` varchar(18) NOT NULL COMMENT '身份证号',
  `policy_code` varchar(50) NOT NULL COMMENT '发放依据的政策或补贴编号',
  `apply_start_month` varchar(6) DEFAULT NULL COMMENT '本次申领时段起始月(YYYYMM，功能二情况2计算起点)',
  `apply_end_month` varchar(6) DEFAULT NULL COMMENT '本次申领时段截止月(YYYYMM)',
  `first_enjoy_month` varchar(6) DEFAULT NULL COMMENT '初次享受补贴的年月(YYYYMM，功能二情况1/3计算起点)',
  `grant_months` int NOT NULL COMMENT '本次发放月数',
  `grant_amount` decimal(10,2) DEFAULT NULL COMMENT '本次发放金额',
  `grant_date` date DEFAULT NULL COMMENT '实际发放打款日期',
  `is_valid` varchar(10) DEFAULT '1' COMMENT '有效标志(1/0)',
  PRIMARY KEY (`payment_id`),
  KEY `idx_subsidy_idcard` (`id_card`),
  KEY `idx_subsidy_policy` (`policy_code`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='历史补贴发放明细表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `unemployment_registration`
--

DROP TABLE IF EXISTS `unemployment_registration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `unemployment_registration` (
  `record_id` bigint NOT NULL AUTO_INCREMENT,
  `id_card` varchar(18) NOT NULL COMMENT '身份证号',
  `unemployment_date` date DEFAULT NULL COMMENT '失业时间',
  `unemployment_reason` varchar(255) DEFAULT NULL COMMENT '失业原因',
  `register_date` date DEFAULT NULL COMMENT '失业登记日期',
  `cancel_date` date DEFAULT NULL COMMENT '失业注销日期(不失业了)',
  `is_valid` varchar(10) DEFAULT '1' COMMENT '有效标志(1/0:注销后变为0)',
  PRIMARY KEY (`record_id`),
  KEY `idx_unemp_idcard` (`id_card`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='失业登记表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-03-25 19:13:59
