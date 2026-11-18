"""Exact statement-basis and period resolution; segments never become totals."""
import pandas as pd

from quant.features.fundamental_snapshot import period_semantics

BASIS_VALUES = {'Consolidated': 'CONSOLIDATED', 'Standalone': 'STANDALONE',
                'Non-Consolidated': 'STANDALONE'}
CONSOLIDATION_AXES = {'ConsolidatedAndStandaloneAxis', 'ConsolidationAxis',
                      'ConsolidatedAndStandaloneFinancialStatementsAxis'}
MEMBERS = {'ConsolidatedMember': 'CONSOLIDATED', 'StandaloneMember': 'STANDALONE'}


def declarations(facts, namespaces):
    contexts = {}
    for fact in facts:
        if (fact['namespace'] in namespaces and fact['concept'] == 'NatureOfReportStandaloneConsolidated'
                and not fact['dimensions'] and not fact['has_typed_dimensions']):
            contexts.setdefault(fact['context_id'], set()).add(BASIS_VALUES.get(fact['text_value'], 'UNKNOWN'))
    return contexts


def conflicting_period_contexts(facts, namespaces):
    """Reject contexts whose explicit reporting dates contradict XML periods.

    Some exchange instances repeat the quarter's XML dates on a YTD context.
    Its larger value must never compete with the actual quarter total.
    """
    invalid = set()
    for fact in facts:
        if fact['namespace'] not in namespaces:
            continue
        column = {'DateOfStartOfReportingPeriod': 'period_start',
                  'DateOfEndOfReportingPeriod': 'period_end'}.get(fact['concept'])
        if column and fact['text_value']:
            try:
                if pd.Timestamp(fact['text_value']) != pd.Timestamp(fact[column]):
                    invalid.add(fact['context_id'])
            except (ValueError, TypeError):
                invalid.add(fact['context_id'])
    return invalid


def classify_context(fact, declared):
    if fact['has_typed_dimensions']:
        return 'OTHER_DIMENSIONAL', 'UNKNOWN'
    basis = set(declared.get(fact['context_id'], ()))
    for axis, member in fact['dimensions'].items():
        if axis.split(':')[-1] not in CONSOLIDATION_AXES:
            return 'SEGMENT', 'UNKNOWN'
        basis.add(MEMBERS.get(member.split(':')[-1], 'UNKNOWN'))
    if not basis:
        # A uniform declaration applies to undimensioned instant balance facts.
        basis = set().union(*declared.values()) if declared else set()
    resolved = next(iter(basis)) if len(basis) == 1 else 'UNKNOWN'
    if fact['period_start'] is None:
        return 'INSTANT', resolved
    semantics = period_semantics(fact['period_start'], fact['period_end'])
    return {'QUARTER_ONLY': 'CURRENT_QUARTER', 'YTD': 'YTD', 'ANNUAL': 'ANNUAL'}.get(semantics, 'UNKNOWN'), resolved


def matches_context(fact, rule, *, period_start, period_end, basis, declared):
    kind, resolved = classify_context(fact, declared)
    if kind in ('SEGMENT', 'OTHER_DIMENSIONAL', 'UNKNOWN'):
        return False
    if not fact['period_end'] or pd.Timestamp(fact['period_end']) != pd.Timestamp(period_end):
        return False
    # Retain legacy standalone metadata convention for undimensioned contexts.
    if resolved == 'UNKNOWN' and not declared and not fact['dimensions'] and basis == 'STANDALONE':
        resolved = basis
    if resolved != basis:
        return False
    if rule.period_type == 'INSTANT':
        return kind == 'INSTANT'
    if rule.period_type == 'INSTANT_OR_DURATION' and kind=='INSTANT':
        return True
    return kind != 'INSTANT' and (period_start is None or pd.Timestamp(fact['period_start']) == pd.Timestamp(period_start))
