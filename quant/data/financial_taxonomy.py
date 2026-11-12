"""Explicit XBRL concepts; unknown concepts are preserved in raw documents."""
ORDINARY = {
    'revenue': ('RevenueFromOperations', 'RevenueFromOperationsNet'),
    'other_income': ('OtherIncome',), 'operating_profit': ('ProfitFromOperations',),
    'ebitda': ('EarningsBeforeInterestTaxDepreciationAndAmortisation',),
    'ebit': ('EarningsBeforeInterestAndTax',), 'finance_cost': ('FinanceCosts',),
    'pbt': ('ProfitBeforeTax',), 'tax': ('TaxExpense', 'TotalTaxExpense'),
    'pat': ('ProfitLossForPeriod', 'ProfitLoss'), 'eps_basic': ('BasicEarningsLossPerShare',),
    'eps_diluted': ('DilutedEarningsLossPerShare',), 'assets': ('Assets',), 'equity': ('Equity',),
    'cash': ('CashAndCashEquivalents',), 'borrowings': ('Borrowings',),
    'operating_cash_flow': ('CashFlowsFromUsedInOperatingActivities',),
    'capex': ('PurchaseOfPropertyPlantAndEquipment',),
}
BANK = {
    'interest_income': ('InterestEarned', 'InterestIncome'), 'interest_expense': ('InterestExpended', 'InterestExpense'),
    'net_interest_income': ('NetInterestIncome',), 'deposits': ('Deposits',), 'advances': ('Advances',),
    'GNPA': ('GrossNonPerformingAssets',), 'NNPA': ('NetNonPerformingAssets',),
    'provisions': ('ProvisionsAndContingencies',), 'capital_adequacy': ('CapitalAdequacyRatio',),
    'CET1': ('CommonEquityTier1CapitalRatio',), 'ROA': ('ReturnOnAssets',), 'ROE': ('ReturnOnEquity',),
}
