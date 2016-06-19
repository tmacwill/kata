import raven

_sentry_client = None

def initialize(config):
    global _sentry_client

    if 'sentry' in config:
        kwargs = {'dsn': config['sentry']['dsn']}
        if 'git' in config['sentry']:
            kwargs['release'] = raven.fetch_git_sha(config['sentry']['git'])
        elif 'release' in config['sentry']:
            kwargs['release'] = config['sentry']['release']

        _sentry_client = raven.Client(**kwargs)

def handler(exception, request, response, parameters):
    if _sentry_client:
        _sentry_client.captureException()

    raise exception
