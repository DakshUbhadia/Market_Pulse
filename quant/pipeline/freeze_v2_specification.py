"""Freeze an explicitly reviewed research specification and its implementation."""
import argparse
import json
from pathlib import Path
from quant.research.specification import freeze_specification


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--coverage', type=Path, required=True)
    parser.add_argument('--share-coverage', type=Path, required=True)
    args=parser.parse_args()
    freeze_specification(json.loads(args.spec.read_text(encoding='utf-8')),args.output,
        coverage_reports={'filings':json.loads(args.coverage.read_text(encoding='utf-8')),
                          'shares':json.loads(args.share_coverage.read_text(encoding='utf-8'))})
    print(args.output)


if __name__=='__main__':
    main()
