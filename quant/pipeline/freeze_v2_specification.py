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
    parser.add_argument('--governance-review', type=Path, required=True)
    parser.add_argument('--data-interval', type=Path, required=True)
    parser.add_argument('--joint-matrix-coverage', type=Path, help='Optional joint evidence bound by the human review')
    args=parser.parse_args()
    coverage_reports = {'filings': json.loads(args.coverage.read_text(encoding='utf-8')),
                        'shares': json.loads(args.share_coverage.read_text(encoding='utf-8'))}
    if args.joint_matrix_coverage:
        coverage_reports['matrix'] = json.loads(args.joint_matrix_coverage.read_text(encoding='utf-8'))
    freeze_specification(json.loads(args.spec.read_text(encoding='utf-8')),args.output,
        coverage_reports=coverage_reports,
        governance_review=json.loads(args.governance_review.read_text(encoding='utf-8')),
        data_interval=json.loads(args.data_interval.read_text(encoding='utf-8')))
    print(args.output)


if __name__=='__main__':
    main()
