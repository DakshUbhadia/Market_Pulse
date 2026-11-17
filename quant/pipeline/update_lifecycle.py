"""Incremental lifecycle evidence import; existing event IDs cannot be overwritten."""
from quant.pipeline.backfill_lifecycle import main


def update_lifecycle(config,start,end):
    from quant.pipeline.backfill_lifecycle import refresh_inventories
    from quant.pipeline.audit_lifecycle import audit_lifecycle
    from quant.pipeline.state import PipelineState
    inventories = refresh_inventories(config) if config.fetch_lifecycle else []
    report = audit_lifecycle(config,as_of=end)
    report.update(inventories=inventories,inventory_refresh='ENABLED' if config.fetch_lifecycle else 'DISABLED')
    if any(row['status'] == 'BLOCKED' for row in inventories):
        report['status'] = 'BLOCKED'
    PipelineState(config).record('lifecycle',status=report['status'],day=end,
        inventory_checked_through=str(end) if inventories else None,
        coverage_status=report['coverage_status'])
    return report

if __name__ == '__main__':
    raise SystemExit(main())
