"""Register an immutable candidate card; code existence confers no validation."""
import argparse
import json
from pathlib import Path
from quant.models.registry import ModelRegistry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--card', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(ModelRegistry(args.registry).register(json.loads(args.card.read_text(encoding='utf-8'))), indent=2))


if __name__ == '__main__':
    main()
