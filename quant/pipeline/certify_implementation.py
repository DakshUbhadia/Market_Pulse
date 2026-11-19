"""Verify public unit CI on the exact clean local SHA, independently of live health."""
from datetime import datetime, timezone
import json
import re
import subprocess
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import requests

from quant.config import REPO_ROOT
from quant.storage.research_store import git_commit, write_json


def verify_public_run_page(client, url, commit, *, timeout):
    """Verify GitHub's public run summary when REST quota is unavailable.

    Bind the full commit link, workflow file, completed status and run URL.
    An unrelated green icon, job name or abbreviated SHA is insufficient.
    """
    if not re.fullmatch(r'https://github\.com/DakshUbhadia/Market_Pulse/actions/runs/[0-9]+', url):
        raise ValueError('Unit CI URL must identify a public repository Actions run')
    response = client.get(url, timeout=timeout)
    response.raise_for_status()
    body = response.text
    if (getattr(response, 'url', url) != url
            or f'href="/DakshUbhadia/Market_Pulse/commit/{commit}"' not in body
            or 'href="/DakshUbhadia/Market_Pulse/actions/workflows/quant-tests.yml"' not in body
            or not re.search(r'class="PageHeader-parentLink-label">\s*Quant unit tests\s*</span>', body)
            or not re.search(r'>Status</span>\s*<span class="h4 color-fg-default">Success</span>', body)):
        raise ValueError('Public run page does not prove completed unit CI on the exact SHA')
    return dict(name='Quant unit tests', head_sha=commit, status='completed', conclusion='success', html_url=url), body


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


def certify_implementation(config, *, session=None, unit_results=None, live_results=None, unit_ci_run_url=None):
    commit = git_commit()
    branch = subprocess.run(['git', 'branch', '--show-current'], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(['git', 'status', '--porcelain', '--untracked-files=normal'],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip())
    client = session or requests.Session()
    checks = local_checks()
    unit = junit_summary(unit_results)
    live = junit_summary(live_results)
    exact, latest, passed, error, main_sha, main_error = [], {}, False, None, None, None
    verification_source, page_sha256 = 'GITHUB_REST_API', None
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
        try:
            response = client.get('https://api.github.com/repos/DakshUbhadia/Market_Pulse/commits/main', timeout=config.timeout)
            response.raise_for_status()
            main_sha = response.json().get('sha')
        except (requests.RequestException, KeyError, ValueError) as exc:
            main_error = str(exc)
    except (requests.RequestException, KeyError, ValueError) as exc:
        error = str(exc)
        if unit_ci_run_url:
            try:
                latest, body = verify_public_run_page(client, unit_ci_run_url, commit, timeout=config.timeout)
                from quant.data.http import atomic_write
                from quant.storage.research_store import digest_file
                path = config.data_dir/'reports/implementation-unit-ci.html'
                atomic_write(path, body.encode('utf-8'))
                page_sha256 = digest_file(path)
                verification_source, passed, exact = 'PUBLIC_GITHUB_RUN_PAGE', True, [latest]
            except (requests.RequestException, ValueError) as page_error:
                error += '; public run verification: '+str(page_error)
    finally:
        if session is None:
            client.close()
    if not main_sha:
        try:
            remote = subprocess.run(['git', 'ls-remote', 'https://github.com/DakshUbhadia/Market_Pulse.git', 'refs/heads/main'],
                cwd=REPO_ROOT, capture_output=True, text=True, check=False, timeout=config.timeout)
            match = re.fullmatch(r'([0-9a-f]{40})\s+refs/heads/main\s*', remote.stdout)
            if match:
                main_sha, main_error = match[1], None
            else:
                main_error = 'Public main ref could not be verified'
        except (OSError, subprocess.SubprocessError) as exc:
            main_error = str(exc)
    certified = passed and not dirty and all(c['status'] == 'PASS' for c in checks.values()) and unit['status'] != 'FAIL'
    now = datetime.now(timezone.utc).isoformat()
    def failure_class(failure):
        message = failure['message'].upper()
        for token, name in (('403', 'HTTP_403_ACCESS_DENIED'), ('429', 'HTTP_429_RATE_LIMITED'),
                            ('TIMEOUT', 'TIMEOUT'), ('CONNECTION', 'CONNECTION_ERROR')):
            if token in message:
                return name
        return 'OTHER_LIVE_FAILURE'

    report = dict(status='CERTIFIED' if certified else 'NOT_CERTIFIED', git_commit=commit, branch=branch,
        PUBLIC_MAIN_SHA=main_sha, LOCAL_IMPLEMENTATION_SHA=commit,
        RESEARCH_CERTIFIED_SHA=commit if certified else None, public_main_error=main_error,
        unit_ci_verification_source=verification_source, unit_ci_page_sha256=page_sha256,
        sha=commit, working_tree_clean=not dirty, runs=exact, unit_ci_passed=passed,
        unit_ci_status='PASS' if passed else latest.get('conclusion') or latest.get('status') or 'UNASSESSED',
        unit_ci_run=latest.get('html_url'), unit_ci_run_url=latest.get('html_url'),
        unit_test_count=unit['tests'], local_unit_test_status=unit['status'],
        **checks, live_test_status=live['status'], live_test_failures=live['failures'],
        live_passed=live['tests']-len(live['failures'])-live.get('skipped', 0) if live['tests'] is not None else None,
        live_failed=len(live['failures']) if live['tests'] is not None else None,
        live_failure_classes=sorted(set(failure_class(f) for f in live['failures'])),
        live_ci_required_for_historical_research=False,
        certified_at=now if certified else None, verified_at=now, remote_error=error)
    from quant.storage.research_store import digest_file
    report['local_test_evidence'] = {str(p): digest_file(p) for p in (unit_results, live_results) if p is not None}
    write_json(config.data_dir/'reports/implementation-certification.json', report)
    return report


def require_certified_implementation(config):
    prior_path = config.data_dir/'reports/implementation-certification.json'
    prior = json.loads(prior_path.read_text(encoding='utf-8')) if prior_path.exists() else {}
    report = certify_implementation(config, unit_ci_run_url=prior.get('unit_ci_run_url') if prior.get('git_commit') == git_commit() else None)
    if report['status'] != 'CERTIFIED':
        raise ValueError('Real historical research requires public passing unit CI on the exact clean implementation SHA')
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--unit-results', type=Path)
    parser.add_argument('--live-results', type=Path)
    parser.add_argument('--unit-ci-run-url', help='Exact-SHA public unit run; verified from GitHub if REST quota is exhausted')
    args = parser.parse_args()
    result = certify_implementation(args.config(config), unit_results=args.unit_results, live_results=args.live_results,
        unit_ci_run_url=args.unit_ci_run_url)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'CERTIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
