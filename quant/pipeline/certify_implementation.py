"""Verify public unit CI on the exact clean local SHA, independently of live health."""
from datetime import datetime, timezone
import json
import subprocess
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import requests

from quant.config import REPO_ROOT
from quant.storage.research_store import git_commit, write_json


def local_checks():
    commands = {
        'dependency_check': [sys.executable, '-m', 'pip', 'check'],
        'compile_check': [sys.executable, '-m', 'compileall', '-q', 'quant'],
        'whitespace_check': ['git', 'diff', '--check'],
    }
    results = {}
    for key, command in commands.items():
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        results[key] = dict(status='PASS' if result.returncode == 0 else 'FAIL',
                            output=(result.stdout+result.stderr).strip())
    return results


def junit_summary(path):
    if path is None:
        return dict(status='UNASSESSED', tests=None, failures=[])
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    failed = [dict(test=c.get('classname', '')+'.'+c.get('name', ''),
                   message=' '.join((e.get('message') or e.text or '') for e in c if e.tag in ('failure', 'error')))
              for c in cases if any(e.tag in ('failure', 'error') for e in c)]
    return dict(status='FAIL' if failed else 'PASS' if cases else 'UNASSESSED',
                tests=len(cases), failures=failed,
                skipped=sum(any(e.tag == 'skipped' for e in c) for c in cases))


def certify_implementation(config, *, session=None, unit_results=None, live_results=None):
    commit = git_commit()
    dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--untracked-files=normal'],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip())
    client = session or requests.Session()
    checks = local_checks()
    unit = junit_summary(unit_results)
    live = junit_summary(live_results)
    exact, latest, passed, error = [], {}, False, None
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
    except (requests.RequestException, KeyError, ValueError) as exc:
        error = str(exc)
    finally:
        if session is None:
            client.close()
    certified = passed and not dirty and all(c['status'] == 'PASS' for c in checks.values()) and unit['status'] != 'FAIL'
    now = datetime.now(timezone.utc).isoformat()
    report = dict(status='CERTIFIED' if certified else 'NOT_CERTIFIED', git_commit=commit,
        sha=commit, working_tree_clean=not dirty, runs=exact, unit_ci_passed=passed,
        unit_ci_status='PASS' if passed else latest.get('conclusion') or latest.get('status') or 'UNASSESSED',
        unit_ci_run=latest.get('html_url'), unit_test_count=unit['tests'], local_unit_test_status=unit['status'],
        **checks, live_test_status=live['status'], live_test_failures=live['failures'],
        live_ci_required_for_historical_research=False,
        certified_at=now if certified else None, verified_at=now, remote_error=error)
    from quant.storage.research_store import digest_file
    report['local_test_evidence'] = {str(p): digest_file(p) for p in (unit_results, live_results) if p is not None}
    write_json(config.data_dir/'reports/implementation-certification.json', report)
    return report


def require_certified_implementation(config):
    report = certify_implementation(config)
    if report['status'] != 'CERTIFIED':
        raise ValueError('Real historical research requires public passing unit CI on the exact clean implementation SHA')
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--unit-results', type=Path)
    parser.add_argument('--live-results', type=Path)
    args = parser.parse_args()
    result = certify_implementation(args.config(config), unit_results=args.unit_results, live_results=args.live_results)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'CERTIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
