import falcon.errors
import raven
import subprocess

_sentry_client = None
_ignored_exceptions = [
    falcon.errors.HTTPUnauthorized,
    falcon.errors.HTTPForbidden,
    falcon.errors.HTTPNotFound,
]

def initialize(config):
    global _sentry_client

    if 'sentry' in config:
        kwargs = {'dsn': config['sentry']['dsn']}
        if 'git' in config['sentry']:
            kwargs['release'] = _git_commit(config['sentry']['git'])
        elif 'release' in config['sentry']:
            kwargs['release'] = config['sentry']['release']

        _sentry_client = raven.Client(**kwargs)

def handler(exception, request, response, parameters):
    if _sentry_client:
        capture = True
        for ignored in _ignored_exceptions:
            if isinstance(exception, ignored):
                capture = False
                break

        if capture:
            _sentry_client.captureException()

    raise exception

def _git_commit(path):
    return subprocess.check_output(
        'cd %s ; git log --format="%%H" -1' % path,
        shell=True,
        universal_newlines=True
    )[:-1]
