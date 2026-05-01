"""Strict-vs-lenient pro-con debate ablation for the policy debate chain."""
from __future__ import annotations

from common_agent_ablation import EXPERIMENTS, parse_common_args, run_experiment


def main() -> int:
    args = parse_common_args("Run pro-con debate policy-chain ablation.")
    return run_experiment(EXPERIMENTS["pro_con"], args)


if __name__ == "__main__":
    raise SystemExit(main())
