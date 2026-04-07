-- Canonical runtime schema contract for local setup and persistence tests.
-- This file intentionally uses a stable, human-readable format so tests can
-- verify the persisted debate contract without relying on dump output.

CREATE TABLE IF NOT EXISTS debate_session (
    session_id               VARCHAR(36)  PRIMARY KEY,
    id_card                  VARCHAR(18)  NOT NULL,
    policy_id                VARCHAR(50)  NOT NULL DEFAULT 'POLICY_001',
    status                   VARCHAR(20)  NOT NULL,
    source_endpoint          VARCHAR(32)  NOT NULL,
    final_conclusion         VARCHAR(20)  NOT NULL,
    final_stance             VARCHAR(20)  NOT NULL,
    consensus_rate           DECIMAL(5,4) NOT NULL,
    is_consensus_reached     TINYINT(1)   NOT NULL DEFAULT 0,
    rounds_taken             INT          NOT NULL,
    evidence_count           INT          NOT NULL,
    agent_count              INT          NOT NULL,
    started_at               DATETIME     NOT NULL,
    completed_at             DATETIME     NOT NULL,
    snapshot_payload         LONGTEXT     NOT NULL,
    created_at               TIMESTAMP    NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_debate_session_idcard (id_card),
    KEY idx_debate_session_completed (completed_at),
    KEY idx_debate_session_conclusion (final_conclusion),
    KEY idx_debate_session_policy (policy_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_debate_log (
    log_id                     BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    session_id                 VARCHAR(36)  NOT NULL,
    id_card                    VARCHAR(18)  NOT NULL,
    debate_round               INT          NOT NULL,
    agent_id                   VARCHAR(50)  NOT NULL,
    agent_role                 VARCHAR(100) NOT NULL,
    conclusion                 VARCHAR(20)  NOT NULL,
    stance                     VARCHAR(20)  NOT NULL,
    confidence                 DECIMAL(5,4) NOT NULL,
    evidence_refs              LONGTEXT     NOT NULL,
    reasoning                  TEXT         NOT NULL,
    dissent_points             LONGTEXT     NOT NULL,
    key_finding                TEXT         NULL,
    round_majority_stance      VARCHAR(20)  NOT NULL,
    round_consensus_rate       DECIMAL(5,4) NOT NULL,
    round_is_consensus_reached TINYINT(1)   NOT NULL DEFAULT 0,
    created_at                 TIMESTAMP    NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_agent_debate_session (session_id),
    KEY idx_agent_debate_idcard (id_card),
    KEY idx_agent_debate_round (session_id, debate_round),
    CONSTRAINT fk_agent_debate_session
        FOREIGN KEY (session_id) REFERENCES debate_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
