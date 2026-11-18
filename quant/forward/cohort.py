"""Explicit cohort namespaces; a policy change never reuses an existing store."""
import re


def cohort_root(config, cohort=None):
    root = config.data_dir/'forward/factor_v1'
    if cohort is None:
        return root  # preserve the existing unnamed cohort
    if not isinstance(cohort, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', cohort):
        raise ValueError('Cohort must be a simple name of at most 64 characters')
    target = root/'cohorts'/cohort
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Cohort path escaped its paper store')
    return target


def cohort_report(config, cohort, name):
    return (cohort_root(config,cohort)/'reports'/name if cohort is not None
            else config.data_dir/'reports'/name)
