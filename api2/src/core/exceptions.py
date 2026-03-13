class DomainValidationError(Exception):
    pass


class MarketDataError(Exception):
    pass


class UnsupportedSymbolError(MarketDataError):
    pass


class UpstreamMarketDataError(MarketDataError):
    pass


class UpstreamMarketDataTimeoutError(UpstreamMarketDataError):
    pass


class MalformedMarketDataResponseError(UpstreamMarketDataError):
    pass
