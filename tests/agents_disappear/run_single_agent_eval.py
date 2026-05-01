"""Single-agent ablation for the policy debate chain."""
from __future__ import annotations

from common_agent_ablation import EXPERIMENTS, parse_common_args, run_experiment


def main() -> int:
    args = parse_common_args("Run single-agent policy-chain ablation.")
    return run_experiment(EXPERIMENTS["single"], args)


if __name__ == "__main__":
    raise SystemExit(main())
