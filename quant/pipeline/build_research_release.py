"""Package or independently verify a historically validated research release."""
import argparse
import json
from pathlib import Path
from quant.research.release import build_research_release, verify_research_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--registry', type=Path)
    parser.add_argument('--model-id')
    parser.add_argument('--specification', type=Path)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--data-dir', type=Path, help='Also verify original data bytes against the release manifest')
    args = parser.parse_args()
    if not args.verify_only:
        if not args.registry or not args.model_id:
            parser.error('--registry and --model-id are required to build a release')
        build_research_release(args.registry, args.model_id, args.output, specification=args.specification)
    print(json.dumps(verify_research_release(args.output, data_dir=args.data_dir), indent=2))


if __name__ == '__main__':
    main()
