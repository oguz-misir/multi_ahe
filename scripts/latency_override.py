"""Apply the warm-up latency re-measurement to a loaded all_summary frame.

AHE-MRTA's decision latency was re-measured after the geodesic distance oracle
moved out of the first timed decision and into a start-up warm-up.  The change
leaves allocation decisions bit-identical, so exactly one column is superseded:
``mean_decision_latency_ms`` for ``ahe_mrta_v3``.  Every other quantity, and
every baseline quantity, still comes from the 300-run campaign.

Both the table generator and the figure generator must apply this, or the paper
ships figures that contradict its own text.  Hence one shared helper.

AHE runs that were *not* re-measured are set to NaN rather than left at their
old value: averaging warm and cold configurations together would produce a
number describing neither.  Callers aggregate with mean(), which skips NaN.

Regenerate the override CSV from ``results/raw/gazebo_warmup_campaign``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OVERRIDE_NAME = 'ahe_latency_warmup.csv'
KEY = ['scenario', 'strategy', 'robot_count', 'target_count', 'seed']


def apply_latency_override(df: pd.DataFrame, processed_dir: Path,
                           verbose: bool = True) -> pd.DataFrame:
    """Return ``df`` with AHE-MRTA latency replaced by the re-measurement."""
    path = Path(processed_dir) / OVERRIDE_NAME
    if not path.exists() or df is None or df.empty:
        return df
    if not set(KEY).issubset(df.columns):
        return df

    new = pd.read_csv(path)
    mapped = (new.set_index(KEY)['mean_decision_latency_ms']
                 .reindex(df.set_index(KEY).index)
                 .to_numpy())
    is_ahe = (df['strategy'] == 'ahe_mrta_v3').to_numpy()
    df = df.copy()
    df['mean_decision_latency_ms'] = np.where(
        is_ahe, mapped, df['mean_decision_latency_ms'])
    if verbose:
        print(f'[latency] warm-up re-measurement applied to '
              f'{int(pd.notna(mapped).sum())} of {int(is_ahe.sum())} '
              f'AHE-MRTA runs; the rest are excluded from the aggregate')
    return df
