"""Apply the recomputed AHE-MRTA communication footprint to a loaded frame.

The 300-run campaign logged a constant 84 bytes for every AHE-MRTA allocation
event: another variant's 3-robot weight-vector size, frozen into the class.  It
described neither AHE's queue-broadcast protocol nor the fleet size, while every
baseline logged a size-dependent estimate of its own protocol -- so the published
cross-method comparison was not like-for-like.

``scripts/recompute_comm_footprint.py`` rebuilds the AHE column on the baselines'
terms (transmitted fields x field size) from the logged task-event stream, and
``ahe_variants.AHEMRTAv3Allocator._comm_footprint`` now computes the same
quantity at run time, so future campaigns log it directly.

Exactly one column is superseded: ``footprint_bytes`` for ``ahe_mrta_v3``.  Every
baseline value still comes from the campaign.  This must be applied wherever the
communication numbers are reported, or the figure will contradict the text.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OVERRIDE_NAME = 'ahe_comm_footprint.csv'
KEY = ['experiment_id', 'alloc_num']
PROPOSED = 'ahe_mrta_v3'


def apply_comm_override(df: pd.DataFrame, processed_dir: Path,
                        verbose: bool = True) -> pd.DataFrame:
    """Return ``df`` with AHE-MRTA's per-event payload replaced."""
    path = Path(processed_dir) / OVERRIDE_NAME
    if not path.exists() or df is None or df.empty:
        return df
    if not set(KEY).issubset(df.columns) or 'footprint_bytes' not in df.columns:
        return df

    new = pd.read_csv(path)
    mapped = (new.set_index(KEY)['footprint_bytes']
                 .reindex(df.set_index(KEY).index)
                 .to_numpy())
    is_proposed = (df['strategy'] == PROPOSED).to_numpy()
    df = df.copy()
    df['footprint_bytes'] = np.where(is_proposed, mapped, df['footprint_bytes'])
    if verbose:
        print(f'[comm] recomputed payload applied to '
              f'{int(pd.notna(mapped[is_proposed]).sum())} of '
              f'{int(is_proposed.sum())} AHE-MRTA allocation events')
    return df
