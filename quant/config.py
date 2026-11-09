"""Configuration independent of Next.js and production credentials."""
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv('QUANT_DATA_DIR', './data')))
    timeout: float = 45
    request_interval: float = 1.5
    retries: int = 3

    @property
    def prices_dir(self) -> Path:
        return self.data_dir / 'normalized' / 'prices'
