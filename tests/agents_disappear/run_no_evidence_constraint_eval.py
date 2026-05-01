"""No-evidence-constraint ablation for the policy debate chain."""
from __future__ import annotations

from common_agent_ablation import EXPERIMENTS, parse_common_args, run_experiment


def main() -> int:
    args = parse_common_args("Run no-evidence-constraint policy-chain ablation.")
    return run_experiment(EXPERIMENTS["no_evidence"], args)


if __name__ == "__main__":
    raise SystemExit(main())
