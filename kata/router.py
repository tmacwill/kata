import kata.config

def add_route(path, resource_class):
    app = kata.config.app()
    resource = resource_class(format='msgpack')
    json_resource = resource_class(format='json')

    app.add_route(path, resource)
    app.add_route(path + '/json', json_resource)

def add_html_route(path, resource_class):
    app = kata.config.app()
    resource = resource_class(format='html')
    app.add_route(path, resource)
