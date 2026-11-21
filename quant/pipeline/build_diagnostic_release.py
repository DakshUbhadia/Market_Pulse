"""Package/verify diagnostic research without registration or a historical seal."""
import argparse
import json
from pathlib import Path

from quant.research.release import build_diagnostic_release, verify_diagnostic_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if not args.verify_only:
        if args.source is None:
            parser.error('--source is required when packaging')
        build_diagnostic_release(args.source, args.output)
    print(json.dumps(verify_diagnostic_release(args.output), indent=2))


if __name__ == '__main__':
    main()
