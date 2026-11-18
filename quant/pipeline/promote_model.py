"""Explicit evidence-gated lifecycle transition, including manual champion review."""
import argparse
import json
from pathlib import Path
from quant.models.registry import ModelRegistry, STATES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--model-id', required=True)
    parser.add_argument('--state', choices=sorted(STATES), required=True)
    parser.add_argument('--reason', required=True)
    parser.add_argument('--reviewer')
    for name in ('forward-root', 'monitoring-report', 'manual-record'):
        parser.add_argument('--'+name, type=Path)
    args = parser.parse_args()
    print(json.dumps(ModelRegistry(args.registry).transition(args.model_id, args.state, reason=args.reason,
        reviewer=args.reviewer, forward_root=args.forward_root, monitoring_report=args.monitoring_report,
        manual_record=args.manual_record), indent=2))


if __name__ == '__main__':
    main()
