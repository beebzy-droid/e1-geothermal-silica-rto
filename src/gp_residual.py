"""
gp_residual.py — E1 / ipis-thesis-geothermal-silica
P8b: Gaussian-process residual model — the comparator for the hybrid
sensor's learned correction inside the RTO loop.

WHY THIS EXISTS
    The closest prior art to "a learned mismatch model whose own
    uncertainty is consumed by the optimizer" is modifier adaptation with
    Gaussian processes (de Avila Ferreira et al., ECC 2018; del Rio
    Chanona et al., Comput. Chem. Eng. 2021). A fair paper compares
    against that idea rather than only citing it. This module supplies a
    GP regressor for the SAME residual target the hybrid sensor learns
    (log1p rate minus log1p physics core at the measured silica), so the
    closed-loop arms rto_gp / rto_gp_k0 differ from rto_hybrid /
    rto_hybrid_k0 in the regressor ONLY.

    Honest scope statement: this is a GP correction of the constraint
    with a posterior-sd back-off. It is NOT a full GP-MA implementation
    (no cost modifiers, no gradient matching, no trust region or
    acquisition function). It tests the regressor, not that literature's
    whole algorithm.

DESIGN (deterministic on purpose)
    Constant-mean GP (plug-in mean = sample mean of the targets; ordinary
    kriging), ARD squared-exponential kernel + iid noise. Hyperparameters
    are chosen by EXACT log marginal likelihood over a small fixed grid
    in physical units — no gradient optimizer, no restarts, no random
    state: the same data always give the same model on any machine,
    which the repository's regeneration rule requires.

    Inputs are (T_C, dose_ppm, s_mgkg). predict() returns the posterior
    mean and the PREDICTIVE sd (latent variance + noise variance), the
    like-for-like counterpart of the hybrid's leave-one-out error sd.
"""

from itertools import product
import math

import numpy as np

# hyperparameter grid, physical units (documented design constants)
GRID_L_T = (5.0, 15.0, 45.0)        # deg C
GRID_L_D = (0.5, 1.5, 4.5)          # ppm
GRID_L_S = (30.0, 90.0, 270.0)      # mg/kg supersaturation
GRID_SF = (0.3, 1.0)                # signal sd, log1p-rate units
GRID_SN = (0.03, 0.1, 0.3)          # noise sd, log1p-rate units
_JITTER = 1e-10


class GPResidual:
    def __init__(self):
        self.X = None
        self.alpha = None
        self.L = None
        self.mean = 0.0
        self.hyp = None          # (l_T, l_d, l_s, sf, sn)
        self.lml = -math.inf

    @staticmethod
    def _sqdist_parts(A: np.ndarray, B: np.ndarray):
        return [(A[:, [j]] - B[:, j][None, :]) ** 2 for j in range(3)]

    @staticmethod
    def _kernel(parts, hyp):
        lT, lD, lS, sf, _ = hyp
        q = parts[0] / lT ** 2 + parts[1] / lD ** 2 + parts[2] / lS ** 2
        return sf ** 2 * np.exp(-0.5 * q)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "GPResidual":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        n = len(y)
        self.X = X
        self.mean = float(np.mean(y))
        yc = y - self.mean
        parts = self._sqdist_parts(X, X)
        best = None
        for hyp in product(GRID_L_T, GRID_L_D, GRID_L_S, GRID_SF, GRID_SN):
            K = self._kernel(parts, hyp) \
                + (hyp[4] ** 2 + _JITTER) * np.eye(n)
            try:
                L = np.linalg.cholesky(K)
            except np.linalg.LinAlgError:
                continue
            a = np.linalg.solve(L.T, np.linalg.solve(L, yc))
            lml = (-0.5 * float(yc @ a) - float(np.log(np.diag(L)).sum())
                   - 0.5 * n * math.log(2.0 * math.pi))
            # strict '>' keeps the FIRST grid point on exact ties
            if best is None or lml > best[0] + 1e-12:
                best = (lml, hyp, L, a)
        if best is None:
            raise RuntimeError("GP fit failed on every grid point")
        self.lml, self.hyp, self.L, self.alpha = best
        return self

    def predict(self, Xs: np.ndarray):
        Xs = np.asarray(Xs, dtype=float)
        parts = self._sqdist_parts(Xs, self.X)
        Ks = self._kernel(parts, self.hyp)
        mu = self.mean + Ks @ self.alpha
        v = np.linalg.solve(self.L, Ks.T)
        var_f = np.maximum(self.hyp[3] ** 2 - np.sum(v * v, axis=0), 0.0)
        sd = np.sqrt(var_f + self.hyp[4] ** 2)
        return mu, sd


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------

def _self_check() -> None:
    checks = []
    rng = np.random.default_rng(0)

    # 1. Recovers a smooth function of the three inputs from 30 noisy
    #    points; test RMSE well below the signal sd
    def f(X):
        return (0.6 * np.tanh((X[:, 0] - 135.0) / 12.0)
                - 0.25 * X[:, 1] + 0.004 * (X[:, 2] - 200.0))
    Xtr = np.column_stack([rng.uniform(120, 150, 30),
                           rng.uniform(0, 2, 30),
                           rng.uniform(100, 300, 30)])
    ytr = f(Xtr) + rng.normal(0, 0.03, 30)
    Xte = np.column_stack([rng.uniform(122, 148, 200),
                           rng.uniform(0.1, 1.9, 200),
                           rng.uniform(110, 290, 200)])
    gp = GPResidual().fit(Xtr, ytr)
    mu, sd = gp.predict(Xte)
    rmse = float(np.sqrt(np.mean((mu - f(Xte)) ** 2)))
    checks.append(("Recovers a smooth 3-input function (test RMSE < 0.08; "
                   "signal sd ~0.45)",
                   rmse < 0.08, f"rmse={rmse:.3f}, hyp={gp.hyp}"))

    # 2. Calibration: |error| <= 2 sd on >= 90% of test points
    cover = float(np.mean(np.abs(mu - f(Xte)) <= 2.0 * sd))
    checks.append(("Predictive sd calibrated (2-sd coverage >= 90%)",
                   cover >= 0.90, f"coverage={100*cover:.0f}%"))

    # 3. Uncertainty structure: sd near the data < sd far from the data,
    #    and the far-field mean reverts to the constant mean
    mu_near, sd_near = gp.predict(Xtr[:5])
    far = np.array([[400.0, 20.0, 5000.0]])
    mu_far, sd_far = gp.predict(far)
    prior_sd = math.sqrt(gp.hyp[3] ** 2 + gp.hyp[4] ** 2)
    checks.append(("sd small at data, prior sd far away; far mean = "
                   "constant mean",
                   float(sd_near.max()) < float(sd_far[0])
                   and abs(float(sd_far[0]) - prior_sd) < 1e-6
                   and abs(float(mu_far[0]) - gp.mean) < 1e-6,
                   f"sd near={sd_near.max():.3f}, far={sd_far[0]:.3f}"))

    # 4. Determinism: refit gives bit-identical hyperparameters and mean
    gp2 = GPResidual().fit(Xtr, ytr)
    mu2, _ = gp2.predict(Xte)        # same call shape as the first fit
    checks.append(("Deterministic (grid LML, no optimizer): identical "
                   "refit",
                   gp2.hyp == gp.hyp
                   and float(np.max(np.abs(mu2 - mu))) == 0.0,
                   f"lml={gp.lml:.2f}"))

    # 5. Pure level offset (the x6-stress shape): constant targets give a
    #    flat prediction equal to that constant everywhere
    yc = np.full(12, 0.33)
    gp3 = GPResidual().fit(Xtr[:12], yc)
    m3, _ = gp3.predict(np.vstack([Xte[:5], far]))
    checks.append(("Constant offset learned as a level, also far from "
                   "the data",
                   float(np.max(np.abs(m3 - 0.33))) < 1e-6,
                   f"max dev={np.max(np.abs(m3 - 0.33)):.1e}"))

    width = max(len(c[0]) for c in checks)
    print("P8b self-check — gp_residual.py")
    print("-" * (width + 50))
    failed = 0
    for name, ok, extra in checks:
        failed += (not ok)
        print(f"{name:<{width}}  {'PASS' if ok else 'FAIL'}  {extra}")
    print("-" * (width + 50))
    print(f"{len(checks) - failed}/{len(checks)} passed."
          + ("" if not failed else "  GATE BLOCKED."))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_check()
