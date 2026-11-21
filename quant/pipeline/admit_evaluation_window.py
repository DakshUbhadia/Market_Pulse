"""Attach supplied human attestations to an unchanged evidence-only declaration."""
import argparse
import json
from pathlib import Path

from quant.research.evaluation_window import load_evaluation_window, freeze_evaluation_window


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', type=Path, required=True)
    parser.add_argument('--transition-review', type=Path, action='append', required=True)
    parser.add_argument('--window-review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = load_evaluation_window(args.declaration, require_admission=False)
    record = {k: v for k, v in record.items() if k not in ('sha256', 'governance')}
    transitions = [json.loads(p.read_text(encoding='utf-8')) for p in args.transition_review]
    if len({r['transition_id'] for r in transitions}) != len(transitions):
        raise ValueError('Duplicate transition reviews')
    governance = dict(transition_reviews={r['transition_id']: r for r in transitions},
        window_review=json.loads(args.window_review.read_text(encoding='utf-8')))
    freeze_evaluation_window(record, args.output, governance=governance)
    print(args.output)


if __name__ == '__main__':
    main()
