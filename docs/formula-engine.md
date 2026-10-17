# Formula Engine

Formula definitions are metadata. Calculation is performed by a controlled map of stable formula IDs to trusted Python implementations. Imported content cannot execute arbitrary code.

The engine distinguishes decimal returns from percentage returns, yield decimals from basis points, signed long/short position values, and positive loss measures used by VaR. It validates correlation bounds and vector/matrix dimensions.

The runtime API returns the inputs, progressive calculation steps, result values, assumptions, limitations, and whether values came from a formula example or a case learning assumption. Reset is a frontend state operation that restores either immutable case values or the formula example defaults.

The first registry covers 21 formulas: simple returns, bond duration/DV01/convexity, basis-point conversion, FX and credit sensitivities, variance/standard deviation/covariance/correlation, two- and N-asset portfolio variance, portfolio volatility, parametric and historical VaR, historical Expected Shortfall, and sensitivity stress P&L.
