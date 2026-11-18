"""Preserve document revisions even when an exchange reuses filing metadata/URLs."""
import pandas as pd

from quant.data.normalization import record_id, write_observation
from quant.storage.parquet_store import read_parquet_file


class FinancialVersionStore:
    def __init__(self, config):
        self.root = config.data_dir/'normalized/financials'
        self.lock_path = config.data_dir/'state/financial-versions.lock'
        self.documents, self.revoked = {}, {}
        self.known_paths = set()
        self._refresh()

    def _refresh(self):
        for path in self.root.rglob('*.parquet'):
            if path in self.known_paths:
                continue
            rows = read_parquet_file(path)
            for row in rows.to_dict('records'):
                key = row.get('metadata_filing_id') or row['filing_id']
                digest = row.get('document_sha256')
                if isinstance(digest, str):
                    self.documents.setdefault(key, set()).add(digest)
                detected = row.get('document_revision_detected_at')
                if pd.notna(detected):
                    timestamp = pd.Timestamp(detected)
                    self.revoked[key] = min(self.revoked.get(key, timestamp), timestamp)
            self.known_paths.add(path)

    def publish(self, frame, raw):
        if frame.empty:
            return None
        from quant.pipeline.state import state_lock
        with state_lock(self.lock_path):
            self._refresh()  # incorporate versions acquired by another daily/backfill writer
            return self._publish(frame, raw)

    def _publish(self, frame, raw):
        frame = frame.copy()
        for i, row in frame.iterrows():
            key, digest = row.filing_id, row.get('document_sha256')
            frame.loc[i, 'metadata_filing_id'] = key
            if isinstance(digest, str):
                previous = self.documents.setdefault(key, set())
                if previous and digest not in previous:
                    # Same dissemination record now serves different bytes.
                    # Observation proves a change, never its historical release time.
                    self.revoked.setdefault(key, pd.Timestamp(raw.fetched_at))
                previous.add(digest)
                if key in self.revoked:
                    frame.loc[i, 'timing_status'] = 'UNCERTAIN_DOCUMENT_REVISION'
                    frame.loc[i, 'document_revision_detected_at'] = self.revoked[key].isoformat()
            frame.loc[i, 'filing_id'] = record_id(dict(metadata_filing_id=key,
                document_sha256=digest if isinstance(digest, str) else None,
                attachment_sha256=row.get('attachment_sha256') if isinstance(row.get('attachment_sha256'), str) else None))
        # A changed document cannot overwrite the normalized original version.
        digest = record_id(dict(metadata_sha256=raw.sha256, versions=sorted(frame.filing_id),
            revocations={key:value.isoformat() for key,value in self.revoked.items() if key in set(frame.metadata_filing_id)}))
        path = write_observation(frame, self.root, digest, raw.fetched_at)
        self.known_paths.add(path)
        return path
