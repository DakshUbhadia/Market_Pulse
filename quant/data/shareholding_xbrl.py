"""Extract only explicitly labelled aggregate shareholding concepts."""
from quant.data.xbrl import parse_xbrl

CONCEPTS = {
    'promoter_pct': ('ShareholdingOfPromoterAndPromoterGroupAsPercentageOfTotalNumberOfShares',),
    'public_pct': ('ShareholdingOfPublicAsPercentageOfTotalNumberOfShares',),
    'FPI_pct': ('ShareholdingOfForeignPortfolioInvestorsAsPercentageOfTotalNumberOfShares',),
    'mutual_fund_pct': ('ShareholdingOfMutualFundsAsPercentageOfTotalNumberOfShares',),
    'institutional_pct': ('ShareholdingOfInstitutionsAsPercentageOfTotalNumberOfShares',),
    'promoter_pledged_pct': ('PercentageOfPledgedOrOtherwiseEncumberedSharesOfPromoterAndPromoterGroup',),
}

MEMBERS = {
    'promoter_pct': 'ShareholdingOfPromoterAndPromoterGroupMember',
    'public_pct': 'PublicShareholdingMember',
    'mutual_fund_pct': 'MutualFundsOrUTIMember',
    'promoter_pledged_pct': 'ShareholdingOfPromoterAndPromoterGroupMember',
}


def parse_shareholding_xbrl(content, as_on_date):
    import pandas as pd
    facts = parse_xbrl(content)
    category_values = {}
    for fact in facts:
        dims = {key.split(':')[-1]: value.split(':')[-1] for key, value in fact['dimensions'].items()}
        if (fact['concept'] == 'ShareholdingAsAPercentageOfTotalNumberOfShares' and fact['value'] is not None
                and fact['period_end'] and pd.Timestamp(fact['period_end']) == pd.Timestamp(as_on_date)
                and len(dims) == 1 and 'CategoryOfShareholdersAxis' in dims):
            category_values.setdefault(dims['CategoryOfShareholdersAxis'], set()).add(float(fact['value']) * 100)
    result = {}
    for name, concepts in CONCEPTS.items():
        values = {float(fact['value']) for fact in facts
                  if fact['concept'] in concepts and fact['value'] is not None
                  and fact['period_end'] and pd.Timestamp(fact['period_end']) == pd.Timestamp(as_on_date)
                  and not fact['dimensions'] and not fact['has_typed_dimensions']}
        # The current BSE/NSE taxonomy stores aggregate categories as dimensional
        # fractions (0.4171 = 41.71%). Only exact known category totals are accepted.
        if not values and name in MEMBERS:
            concept = ('EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares'
                       if name == 'promoter_pledged_pct' else 'ShareholdingAsAPercentageOfTotalNumberOfShares')
            for fact in facts:
                dims = {key.split(':')[-1]: value.split(':')[-1] for key, value in fact['dimensions'].items()}
                if (fact['concept'] == concept and fact['value'] is not None and fact['period_end']
                        and pd.Timestamp(fact['period_end']) == pd.Timestamp(as_on_date)
                        and dims == {'CategoryOfShareholdersAxis': MEMBERS[name]}):
                    values.add(100 * float(fact['value']))
        if any(not 0 <= value <= 100 for value in values):
            raise ValueError('Shareholding percentage outside [0, 100]')
        result[name] = values.pop() if len(values) == 1 else None
    for field, members in {
        'FPI_pct': ('InstitutionsForeignPortfolioInvestorCategoryOneMember', 'InstitutionsForeignPortfolioInvestorCategoryTwoMember'),
        'institutional_pct': ('InstitutionsDomesticMember', 'InstitutionsForeignMember'),
    }.items():
        if result[field] is None and all(len(category_values.get(member, set())) == 1 for member in members):
            result[field] = sum(next(iter(category_values[member])) for member in members)
    if any(value is not None and not 0 <= value <= 100 for value in result.values()):
        raise ValueError('Shareholding percentage outside [0, 100]')
    if result['promoter_pct'] is not None and result['public_pct'] is not None:
        if result['promoter_pct'] + result['public_pct'] > 100.01:
            raise ValueError('Shareholding percentages exceed 100')
    return result
