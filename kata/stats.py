import contextlib
import statsd

_client = None
_noop = contextlib.contextmanager(lambda: (yield))

def initialize(config):
    global _client

    _client = statsd.StatsClient(
        config.get('host', 'localhost'),
        config.get('port', 8125),
        prefix=config.get('prefix', '')
    )

def timer(key):
    return _client.timer(key) if _client else _noop()
