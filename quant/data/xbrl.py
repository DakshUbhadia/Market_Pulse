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
                      'context_id': reference, 'period_start': context.get('startDate'),
                      'period_end': context.get('endDate') or context.get('instant'),
                      'entity': context.get('identifier'), 'dimensions': context['dimensions'],
                      'has_typed_dimensions': context['has_typed_dimensions'],
                      'unit': units.get(element.attrib.get('unitRef')), 'value': value})
    return facts


def extract_financials(content, period_end, *, consolidated=False, bank=False, period_start=None):
    from quant.data.financial_taxonomy import BANK, ORDINARY
    facts = parse_xbrl(content)
    target = pd.Timestamp(period_end).date()
    result = {}
    for field, concepts in (BANK if bank else ORDINARY).items():
        candidates = []
        for fact in facts:
            if fact['concept'] not in concepts or not fact['period_end'] or fact['value'] is None:
                continue
            if pd.Timestamp(fact['period_end']).date() != target or fact['has_typed_dimensions']:
                continue
            dims = fact['dimensions']
            # Only an explicit consolidation dimension is accepted; segments are not totals.
            consolidation = [value for dimension, value in dims.items()
                             if 'Consolidat' in dimension or 'Standalone' in dimension]
            if len(dims) != len(consolidation):
                continue
            if consolidation and not any(('Consolidated' if consolidated else 'Standalone') in v for v in consolidation):
                continue
            if consolidated and not consolidation:
                continue  # An unlabelled context cannot prove consolidation.
            if period_start is not None and fact['period_start'] and pd.Timestamp(fact['period_start']) != pd.Timestamp(period_start):
                continue
            candidates.append(fact)
        # Two durations (quarter/YTD), units, or values are ambiguous; never select an arbitrary fact.
        signatures = {(fact['period_start'], fact['period_end'], fact['unit'], fact['value']) for fact in candidates}
        result[field] = float(candidates[0]['value']) if len(signatures) == 1 else None
    result['parser_status'] = 'PARSED' if any(value is not None for value in result.values()) else 'NEEDS_REVIEW'
    result['financial_schema'] = 'BANK' if bank else 'ORDINARY'
    return result
