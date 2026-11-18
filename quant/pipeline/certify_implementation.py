"""Verify public unit CI on the exact clean local SHA, independently of live health."""
from datetime import datetime, timezone
import json
import subprocess
import requests

from quant.config import REPO_ROOT
from quant.storage.research_store import git_commit, write_json


def certify_implementation(config, *, session=None):
    commit = git_commit()
    dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--untracked-files=normal'],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip())
    client = session or requests.Session()
    try:
        response = client.get('https://api.github.com/repos/DakshUbhadia/Market_Pulse/actions/runs',
            params={'head_sha': commit, 'per_page': 100}, timeout=config.timeout)
        response.raise_for_status()
        runs = response.json()['workflow_runs']
        exact = [{k: r.get(k) for k in ('id', 'name', 'head_sha', 'status', 'conclusion', 'html_url', 'created_at')}
                 for r in runs if r.get('head_sha') == commit]
        units = [r for r in exact if r['name'] == 'Quant unit tests']
        latest = max(units, key=lambda r: r.get('created_at', ''), default={})
        passed = latest.get('status') == 'completed' and latest.get('conclusion') == 'success'
        report = dict(status='CERTIFIED' if passed and not dirty else 'NOT_CERTIFIED',
            sha=commit, working_tree_clean=not dirty, runs=exact,
            unit_ci_passed=passed, live_ci_required_for_historical_research=False,
            verified_at=datetime.now(timezone.utc).isoformat())
    finally:
        if session is None:
            client.close()
    write_json(config.data_dir/'reports/implementation-certification.json', report)
    return report


def require_certified_implementation(config):
    report = certify_implementation(config)
    if report['status'] != 'CERTIFIED':
        raise ValueError('Real V2 research requires public passing unit CI on the exact clean implementation SHA')
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    result = certify_implementation(args.config(config))
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'CERTIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
