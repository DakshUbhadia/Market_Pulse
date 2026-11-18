"""Context-aware XBRL facts. No dimensional aggregation or fuzzy tag matching."""
from decimal import Decimal, InvalidOperation

import pandas as pd
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException


def local(tag):
    return tag.rsplit('}', 1)[-1]


def parse_xbrl(content):
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, DefusedXmlException) as error:
        raise ValueError(f'Invalid or unsafe XBRL: {error}') from error
    if local(root.tag).lower() != 'xbrl':
        raise ValueError('Expected XBRL instance')
    contexts, units = {}, {}
    for element in root:
        name = local(element.tag)
        if name == 'context':
            values = {local(item.tag): item.text for item in element.iter()
                      if local(item.tag) in ('startDate', 'endDate', 'instant', 'identifier')}
            values['dimensions'] = {item.attrib.get('dimension', ''): item.text for item in element.iter()
                                    if local(item.tag) == 'explicitMember'}
            values['has_typed_dimensions'] = any(local(item.tag) == 'typedMember' for item in element.iter())
            contexts[element.attrib['id']] = values
        elif name == 'unit':
            units[element.attrib['id']] = ET.tostring(element, encoding='unicode')
    facts = []
    for element in root.iter():
        reference = element.attrib.get('contextRef')
        if reference is None:
            continue
        if reference not in contexts:
            raise ValueError('XBRL fact references unknown context')
        context = contexts[reference]
        nil = element.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}nil') == 'true'
        value = None
        if not nil and element.text:
            try:
                value = Decimal(element.text.strip()) * (Decimal(10) ** int(element.attrib.get('scale', 0)))
                if not value.is_finite():
                    raise ValueError('Nonfinite XBRL value')
            except InvalidOperation:
                pass  # Text facts stay in the raw instance, not a numeric financial observation.
        facts.append({'concept': local(element.tag), 'namespace': element.tag.split('}')[0].lstrip('{'),
                      'text_value': element.text.strip() if element.text else None,
                      'context_id': reference, 'period_start': context.get('startDate'),
                      'period_end': context.get('endDate') or context.get('instant'),
                      'entity': context.get('identifier'), 'dimensions': context['dimensions'],
                      'has_typed_dimensions': context['has_typed_dimensions'],
                      'unit': units.get(element.attrib.get('unitRef')), 'value': value})
    return facts


def extract_financials(content, period_end, *, consolidated=False, bank=False, period_start=None, entity_type=None):
    from quant.data.taxonomy_registry import concept_rules, TAXONOMY_VERSION
    from quant.data.xbrl_context import declarations, matches_context, conflicting_period_contexts
    facts = parse_xbrl(content)
    family = entity_type or ('IND_AS_BANK' if bank else 'IND_AS_INDUSTRIAL')
    rules = concept_rules(family)
    declared = declarations(facts, rules[0].namespaces)
    invalid_contexts = conflicting_period_contexts(facts, rules[0].namespaces)
    result = {}
    for rule in rules:
        candidates = []
        for fact in facts:
            if (fact['concept'] not in rule.concepts or fact['namespace'] not in rule.namespaces
                    or fact['value'] is None or not fact['unit'] or fact['context_id'] in invalid_contexts):
                continue
            if not matches_context(fact, rule, period_start=period_start, period_end=period_end,
                                   basis='CONSOLIDATED' if consolidated else 'STANDALONE', declared=declared):
                continue
            unit = ET.fromstring(fact['unit'])
            measures = [e.text.split(':')[-1] for e in unit.iter() if local(e.tag) == 'measure' and e.text]
            expected = {'INR': ['INR'], 'PURE': ['pure'], 'INR_PER_SHARE': ['INR', 'shares']}[rule.unit_kind]
            if measures != expected:
                continue
            candidates.append(fact)
        # Two durations (quarter/YTD), units, or values are ambiguous; never select an arbitrary fact.
        signatures = {(fact['period_start'], fact['period_end'], fact['unit'], fact['value']) for fact in candidates}
        result[rule.canonical_field] = float(candidates[0]['value']) if len(signatures) == 1 else None
    result['parser_status'] = 'PARSED' if any(value is not None for value in result.values()) else 'NEEDS_REVIEW'
    result['financial_schema'] = 'BANK' if family == 'IND_AS_BANK' else 'ORDINARY' if family == 'IND_AS_INDUSTRIAL' else family
    result.update(entity_type=family, parser_version='financial_xbrl_2.0.0', taxonomy_version=TAXONOMY_VERSION)
    return result
