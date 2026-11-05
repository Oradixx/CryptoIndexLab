"""Deterministic daily prices served to api2 instead of CoinGecko.

The expected index values used in the tests were computed by hand from these
series. An index is worth `100 * sum(w_i * P_i(t) / P_i(t0))`, where `w_i`
is the weight of asset i normalized to sum to 1 and `t0` is the first date
on which every asset of the index has a price.

Index BTC 60 / ETH 40 (t0 = D1, BTC0 = 100, ETH0 = 50):

    date  BTC/BTC0  ETH/ETH0  0.6*BTC + 0.4*ETH      value
    D1    1.000     1.00      0.6    + 0.4   = 1.0    100.00
    D2    1.100     0.90      0.66   + 0.36  = 1.02   102.00
    D3    1.210     1.20      0.726  + 0.48  = 1.206  120.60
    D4    1.331     1.08      0.7986 + 0.432 = 1.2306 123.06
    total return = 123.06 / 100 - 1 = +23.06 %

Index BTC 50 / SOL 50: SOL has no price on D1, so t0 = D2 (BTC0 = 110, SOL0 = 20):

    date  BTC/BTC0         SOL/SOL0       0.5*BTC + 0.5*SOL      value
    D2    1.00             1.00           0.5   + 0.5   = 1.0     100.0
    D3    121/110  = 1.10  25/20 = 1.25   0.55  + 0.625 = 1.175   117.5
    D4    133.1/110 = 1.21 30/20 = 1.50   0.605 + 0.75  = 1.355   135.5
    total return = +35.5 %

Index ETH 100: 100 * ETH / 50 = 100, 90, 120, 108; total return = +8 %.

Weights BTC 3 / ETH 1, stored without the API validation (normalized to 0.75 / 0.25):

    D1  100
    D2  100 * (0.75 * 1.1   + 0.25 * 0.9)  = 100 * (0.825   + 0.225) = 105.0
    D3  100 * (0.75 * 1.21  + 0.25 * 1.2)  = 100 * (0.9075  + 0.3)   = 120.75
    D4  100 * (0.75 * 1.331 + 0.25 * 1.08) = 100 * (0.99825 + 0.27)  = 126.825
"""

from datetime import date

D1 = date(2026, 1, 1)
D2 = date(2026, 1, 2)
D3 = date(2026, 1, 3)
D4 = date(2026, 1, 4)

MOCK_PRICES: dict[str, list[tuple[date, float]]] = {
    "BTC": [(D1, 100.0), (D2, 110.0), (D3, 121.0), (D4, 133.1)],
    "ETH": [(D1, 50.0), (D2, 45.0), (D3, 60.0), (D4, 54.0)],
    "SOL": [(D2, 20.0), (D3, 25.0), (D4, 30.0)],
}
