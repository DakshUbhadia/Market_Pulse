"""Archive official TIDEWATER evidence without inventing historical availability."""
import json
from quant.data.http import Downloader
from quant.storage.research_store import write_json, digest_file

SOURCES = {
    'original-listing.html': 'https://nsearchives.nseindia.com/content/press/12012007.htm',
    'postal-ballot.pdf': 'https://www.veedolindia.com/sites/default/files/assets/pdf/pr-disclouser/PostalBallotNotice-Form28thJan2016.pdf',
    'record-date.pdf': 'https://www.veedolindia.com/sites/default/files/assets/pdf/pr-disclouser/NoticeRecordSplit-Bonus.pdf',
}


def review_security_transition(config):
    evidence, failures = [], []
    downloader = Downloader(config)
    try:
        for name, url in SOURCES.items():
            path = config.data_dir/'raw/security-transitions/tidewater-2016'/name
            try:
                if name.endswith('.html'):
                    from quant.data.http import atomic_write
                    response = downloader.session.get(url,timeout=config.timeout)
                    response.raise_for_status()
                    if b'INE484C01014' not in response.content:
                        raise ValueError('Original listing security absent from response')
                    atomic_write(path,response.content)
                else:
                    downloader.fetch(url,path)
                evidence.append(dict(source_url=url,raw_path=str(path.relative_to(config.data_dir)),
                    source_sha256=digest_file(path)))
            except (OSError,ValueError,RuntimeError) as error:
                failures.append(dict(source_url=url,error=str(error)))
    finally:
        downloader.close()
    prior_path = config.data_dir/'reports/tidewater-2016-held-blocker-review.json'
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else {}
    report = dict(status='UNRESOLVED',verification_status='PARTIALLY_VERIFIED',evidence=evidence,
        acquisition_failures=failures,predecessor_isin='INE484C01014',
        observed_successor_isin='INE484C01022', observations=prior.get('observed_prices',[]),
        answers=dict(predecessor='NSE original listing identifies INE484C01014',
            entitlement='Issuer ballot proposes two Rs5 shares per Rs10 share, then 1:1 bonus on subdivided shares',
            economic_multiplier_candidate=4,price_adjustment_multiplier_candidate=.25,
            immediately_tradable_units=None,successor_valid_from=None,credit_date=None,
            first_tradable_date=None,announced_at=None,can_value_march_17_without_future_information=False),
        missing_evidence=['Exact exchange dissemination timestamp',
            'Dated old/new ISIN conversion and ex-date entitlement basis',
            'Actual credit, listing and first tradable dates of each entitlement leg',
            'Reconcile ex-date old-ISIN quotation before successor first observation'],
        automatic_bridge_enabled=False,baseline_seal_created=False,
        note='Proposal and observed quotations do not prove completed mandatory conversion timing.')
    write_json(config.data_dir/'reports/security-transitions/tidewater-2016.json',report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    print(json.dumps(review_security_transition(args.config(config)),indent=2))
    return 1  # review intentionally cannot certify an unproven bridge


if __name__ == '__main__':
    raise SystemExit(main())
