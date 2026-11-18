"""Versioned, exact concept rules. New namespaces require an explicit review."""
from dataclasses import dataclass

from quant.data.financial_taxonomy import ORDINARY, BANK

TAXONOMY_VERSION = 'financial_taxonomy_2.0.0'
FAMILIES = ('IND_AS_INDUSTRIAL', 'IND_AS_BANK', 'IND_AS_NBFC',
            'IND_AS_INSURANCE', 'IND_AS_OTHER_FINANCIAL')
NAMESPACES = ('http://www.bseindia.com/xbrl/fin/2020-03-31/in-bse-fin',
              'urn:finance')  # Existing isolated synthetic fixtures.
BANK_NAMESPACE = 'http://www.bseindia.com/xbrl/fin/2019-09-30/in-bse-fin'


@dataclass(frozen=True)
class ConceptRule:
    canonical_field: str
    namespaces: tuple
    concepts: tuple
    entity_type: str
    statement_type: str
    period_type: str
    allowed_dimensions: tuple = ()
    unit_kind: str = 'INR'


def concept_rules(family):
    if family not in FAMILIES:
        raise ValueError('Unsupported financial taxonomy family')
    # Financial families share accounting totals, never industrial leverage ratios.
    mapping = dict(ORDINARY)
    mapping.update(eps_basic=('BasicEarningsLossPerShare',
        'BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations'),
        eps_diluted=('DilutedEarningsLossPerShare',
        'DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations'),
        paid_up_capital=('PaidUpValueOfEquityShareCapital',),
        face_value=('FaceValueOfEquityShareCapital',))
    if family != 'IND_AS_INDUSTRIAL':
        for field in ('ebitda', 'ebit', 'borrowings'):
            mapping.pop(field, None)
    if family == 'IND_AS_BANK':
        mapping.update(BANK, nim=('NetInterestMargin',), provision_coverage=('ProvisionCoverageRatio',))
        mapping.update(pat=('ProfitLossForPeriod','ProfitLossForThePeriod'),
                       pbt=('ProfitBeforeTax','ProfitLossFromOrdinaryActivitiesBeforeTax'),
                       operating_profit=('OperatingProfitBeforeProvisionAndContingencies',),
                       NNPA=('NetNonPerformingAssets','NonPerformingAssets'),
                       CET1=('CommonEquityTier1CapitalRatio','CET1Ratio'))
    stocks = {'assets', 'equity', 'cash', 'borrowings', 'paid_up_capital', 'face_value',
              'deposits', 'advances', 'GNPA', 'NNPA', 'capital_adequacy', 'CET1', 'provision_coverage'}
    ratios = {'ROA', 'ROE', 'nim', 'capital_adequacy', 'CET1', 'provision_coverage'}
    return tuple(ConceptRule(field, NAMESPACES+((BANK_NAMESPACE,) if family=='IND_AS_BANK' else ()), concepts, family,
                 'BALANCE_SHEET' if field in stocks else 'CASH_FLOW' if field in ('operating_cash_flow', 'capex') else 'INCOME',
                 'INSTANT_OR_DURATION' if family=='IND_AS_BANK' and field in stocks else 'INSTANT' if field in stocks else 'DURATION',
                 unit_kind='PURE' if field in ratios else 'INR_PER_SHARE' if field in ('eps_basic','eps_diluted','face_value') else 'INR')
                 for field, concepts in mapping.items())


def filing_family(row):
    """Use declared entity type or an exact exchange document taxonomy prefix."""
    declared = row.get('entity_type')
    if declared in FAMILIES:
        return declared
    from urllib.parse import urlsplit
    name = urlsplit(str(row.get('source_document', ''))).path.rsplit('/', 1)[-1]
    for prefix, family in (('NBFC_INDAS_', 'IND_AS_NBFC'), ('BANKING_', 'IND_AS_BANK'), ('INSURANCE_', 'IND_AS_INSURANCE')):
        if name.startswith(prefix):
            return family
    bank = row.get('bank')
    if bank is True or str(bank) == 'True':
        return 'IND_AS_BANK'
    if bank is False or str(bank) == 'False':
        return 'IND_AS_INDUSTRIAL'
    raise ValueError('Unknown financial institution type')
