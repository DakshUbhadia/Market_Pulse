"""Open a research incident from a reviewable JSON record."""
import argparse
import json
from pathlib import Path
from quant.monitoring.incidents import IncidentLedger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    record = json.loads(args.record.read_text(encoding='utf-8'))
    print(json.dumps(IncidentLedger(args.ledger).open(**record), indent=2))


if __name__ == '__main__':
    main()
