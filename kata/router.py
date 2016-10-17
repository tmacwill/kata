import kata.config

def add_route(path, resource_class, format=None):
    app = kata.config.app()
    resource = resource_class(format=format)
    app.add_route(path, resource)
