"""Resolve an incident without rewriting its opening evidence."""
import argparse
import json
from pathlib import Path
from quant.monitoring.incidents import IncidentLedger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--incident-id', required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(IncidentLedger(args.ledger).resolve(args.incident_id,
        **json.loads(args.record.read_text(encoding='utf-8'))), indent=2))


if __name__ == '__main__':
    main()
