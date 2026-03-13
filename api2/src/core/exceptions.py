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


class IndexPerformanceError(Exception):
    pass


class InvalidIndexCompositionError(IndexPerformanceError):
    pass


class InsufficientHistoricalDataError(IndexPerformanceError):
    pass
