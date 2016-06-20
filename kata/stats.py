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

def decrement(key):
    if not _client:
        return None

    _client.decr(key)

def increment(key):
    if not _client:
        return None

    _client.incr(key)

def start_timer(key):
    if not _client:
        return None

    timer = _client.timer(key)
    timer.start()
    return timer

def stop_timer(timer):
    if not timer:
        return

    timer.stop()

def timer(key):
    return _client.timer(key) if _client else _noop()
