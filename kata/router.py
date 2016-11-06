import kata.config

_routes = {}

def add_route(path, resource_class, format=None):
    global _routes

    app = kata.config.app()
    resource = resource_class(format=format)
    app.add_route(path, resource)
    _routes[path] = resource

def routes():
    return _routes
