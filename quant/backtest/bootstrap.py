import numpy as np


def block_bootstrap(values, *, block_size=63, samples=1000, seed=7, confidence=.95):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if block_size < 1 or samples < 1 or not 0 < confidence < 1:
        raise ValueError('Invalid bootstrap configuration')
    if len(values) < 2*block_size:
        return dict(status='INSUFFICIENT_INDEPENDENT_BLOCKS', lower=None, upper=None, seed=seed, block_size=block_size)
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(samples):
        starts = rng.integers(0, len(values)-block_size+1, size=int(np.ceil(len(values)/block_size)))
        resample = np.concatenate([values[start:start+block_size] for start in starts])[:len(values)]
        means.append(resample.mean())
    alpha = (1-confidence)/2
    return dict(status='OK', lower=float(np.quantile(means, alpha)), upper=float(np.quantile(means, 1-alpha)),
                seed=seed, block_size=block_size, samples=samples, confidence=confidence)
