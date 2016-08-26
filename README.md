# kata: a simple and flexible web framework

## Creating a Project

Kata requires Python 3. If you want Python 2 support, sorry.

We're going to create a project called myproject. First, create a directory where the project will live:

    mkdir /srv/www/myproject
    cd /srv/www/myproject

You probably want to create a virtualenv. To do so:

    sudo pip install virtualenv
    virtualenv -p python3 venv
    source venv/bin/activate

Now, let's create a configuration file to that will specify how to connect to the database, cache, etc. Kata supports PosgreSQL for a relational database, and Redis/memcached for caching. There's an example in kata/config.yaml.example. You might want to create several different configuration files (e.g., one for dev, one for staging, and one for production) so I'd recommend creating a `config` directory inside of `myproject` and putting your config files in there. You might also want a `bin` directory for various scripts your app might need, or a `static` directory for static files.

Next, create a new directory where all the application source will live. Inside of `myproject`, create another directory called `myproject`, so your Python source can live as a standalone package:

    cd myproject
    mkdir myproject

Now, let's create the root `__init__.py` file. In `myproject/myproject/__init__.py`, paste:

    import kata
    import os

    config = os.environ.get('CONFIG', os.path.dirname(os.path.realpath(__file__)) + '/../config/dev.yaml')
    kata.initialize(config)
    app = kata.config.app()

Here, we're initializing our kata application, using the config file we just created. This `__init__.py` also lets us specify the path to a config file via an environment variable, and defaults to a file called `config/dev.yaml`. It also exposes a module-level `app` variable, which you'll need to run WSGI servers like gunicorn.

## Resources

Now that our app is set up, let's define URLs it can respond to. First, create a new file called `myproject/myproject/resource/foo.py`:

    import kata.resource

    class Bar(kata.resource.Resource):
        def get(self, request, response, baz):
            ...
            return self.success({
                'baz': baz,
                'something': 'else'
            })

        def post(self, request, response, baz):
            ...

We just created a new resource called `Bar` that can respond to both `get` and `post` requests. The first two arguments are objects where you can get more information about the request and set various response properties. They both take a third argument called `baz`, which represents some input from the user. At the end of the `get` method, we call `self.success`, which will take care of returning an appropriate HTTP response code and serializing data.

Next, we'll map that handler to a URL. Create a new file called `myproject/myproject/routes.py`, where you'll add routes to the app:

    import kata.router
    import myproject.resource.foo

    kata.router.add_route('/foo/bar/{baz}', myproject.resource.foo.Bar)

In order for these routes to be registered when your app starts, change `myproject/myproject/__init__.py` to look like this:

    import kata
    import os

    config = os.environ.get('CONFIG', os.path.dirname(os.path.realpath(__file__)) + '/../config/dev.yaml')
    kata.initialize(config)
    app = kata.config.app()

    import myproject.routes

You can split up these routes into as many different files and directories as you want, just be sure to import them all in your `__init__.py` file (or via modules imported by that file), or they won't be registered.

Now, when `/foo/bar/123` is accessed, the `Bar` resource you created above will call either its `get` or `post` method, depending on the type of request, passing along the value `123` to the `baz` parameter. For POST requests, you can call `self.body(request)` from within the `post` method to get a dictionary of data passed as POST data. The `Content-Type` request header will be used to decode data passed as JSON or msgpack appropriately.

By default, resources will return JSON. You can change the encoding via the `format` parameter in `kata.router.add_route`. To return msgpack instead, pass `format='msgpack'`, or if you want to return an HTML string, pass `format='html'`.

## Running the Server

kata works with any WSGI server. We'll use gunicorn as an example. After you've installed gunicorn, you can run the below from the root `myproject` directory to start your app server:

    gunicorn --bind 127.0.0.1:8000 myproject:app

In a production environment, we recommend putting gunicorn behind nginx. Here's an example nginx config file for `myproject`, running at `myproject.com`:

    upstream myproject {
        server 127.0.0.1:8000 fail_timeout=0;
    }

    server {
        listen 80;
        client_max_body_size 1m;
        server_name myproject.com www.myproject.com;
        keepalive_timeout 5;

        location /static/ {
            alias /srv/www/myproject/static/;
            autoindex off;
        }

        location / {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_pass http://myproject;
        }
    }

## Database

Chances are, your app uses a database. You can specify your database configuration info in your configuration YAML, like this:

    database:
      name: YOUR_DATABASE_NAME
      host: localhost
      password: YOUR_DATABASE_PASSWORD
      pool_size: 10
      port: 5432
      user: YOUR_DATABASE_USER

To manage the database schema, you can specify tables in YAML files. It's recommended to create a top-level directory called `schema`, then to create a separate YAML file for each of your tables. Here's an example for a table called `foo`:

    foo:
      columns:
        id:
          type: 'bigserial'
          nullable: false
          primary_key: true
        bar:
          type: 'integer'
          nullable: false
        baz:
          type: 'character varying'
          length: 255
      indexes:
        qux:
          columns: ['bar', 'baz']
          unique: true

You can use `kata.schema.apply` to generate SQL statements to migrate the current state of the database to the format specified in your schema files. By default, kata will simply print SQL statements without running anything, but if you pass `execute=True` as a kwarg, then kata will run the statements as well. You can also use `kata.schema.reset` to blow away your existing database and re-create the schema from scratch.

Kata also comes with a lightweight ORM. Each table should have a corresponding `kata.db.Object` class. We recommend putting them in a directory called `model`, but you can do whatever you want. The class for a table called `foo` would look like this:

    class Foo(kata.db.Object):
        __table__ = 'foo'

Suppose the `foo` table has columns calld `bar` (a `varchar`) and `qux` (an `int`). With that class, you can do things like:

    Foo.create([{'bar': 'baz', 'qux': 3}, {'bar': 'corge', 'qux': 5}])
    Foo.get({'bar': 'baz'}, order_by='qux', limit=5)
    Foo.get(where_in=('bar', ['qux', 'quux']))
    Foo.update({'bar': 'baz'}, where={'qux': 3})

Getter functions return instances of the `Foo` class. Values for the `bar` and `qux` columns can be accessed via properties on those objects. You can serialize data returned from getters with:

    kata.db.serialize(data, format='json')
    kata.db.serialize(data, format='msgpack')

## Cache

Kata also has support for caching data via three different mechanisms: memory, redis, and memcached. Cache instances are specified in the configuration YAML file, like this:

    cache:
      memcached:
        type: memcached
        prefix: YOUR_KEY_PREFIX
        hosts:
          - 'localhost:11211'
          - 'localhost:11212'
      memory:
        type: memory
      redis:
        type: redis
        db: 0
        host: 'localhost:6379'
        prefix: YOUR_KEY_PREFIX

Here, we've created 3 different cache instances, one called `memcached`, one called `memory`, and one called `redis`. You can call them whatever you want. All caches expose the same interface:

    def delete(self, key)
    def delete_multi(self, keys)
    def get(self, key)
    def get_multi(self, keys)
    def set(self, key, value, expire=None)
    def set_multi(self, value_map, expire=None)

Now, in your app, the instance called `memcached` can be accessed via `kata.cache.memcached`, so you can do things like:

    kata.cache.memcached.set('foo', 'bar')
    kata.cache.memcached.get('foo') == 'bar'

## Containers

Containers are an abstraction for caching data. A container handles caching some value and querying when there's a cache miss. Here's an example of a `Simple` container:

    class Foo(kata.container.Simple):
        def init(self, foo):
            self.foo = foo

        def cache(self):
            return kata.cache.memcached

        def dependencies(self):
            return (Bar, self.foo)

        def expire(self):
            return 3600

        def key(self):
            return 'foo:%s' % self.foo

        def pull(self):
            return some_expensive_thing(self.foo)

Here, `pull` will only be executed if the value isn't in the cache, and then the value will be stored in the cache. `key` specifies a unique key for the container, so it must be unique across everything you're caching, or containers will conflict with each other. The `expire` method specifies how long the value will remain in the cache, in seconds. `init` should used as a constructor, so always override `init` instead of `__init__`. With the `dependencies` method, you can specify which containers should be dirtied when the container is dirtied. In this example, every time `Foo` is dirtied, `Bar` will also be dirtied as well.

To use the `Simple` cache, just do this:

    Foo(5).get()

To remove a value from the cache before it expires:

    Foo(5).dirty()

A common use case in a web app is looking up a bunch of values in a database based on some column value. For example, `SomeModel` might have a `bigint` column called `id`, and you might want to look up all the rows where the `id` is in some list of values. With a `Simple` container, you'd need _n_ cache lookups to get _n_ rows, which would be slow. The `Attribute` container solves this by doing a bulk cache get for efficiency. Here's an example of an `Attribute` container:

    class Bar(kata.container.Attribute):
        def cache(self):
            return kata.cache.memcached

        def key(self, item):
            return 'bar:%s' % item

        def attribute(self):
            return SomeModel, 'id'

Notice how this time the `key` method takes an `item` argument, since the container will be given multiple different values. To use the `Attribute` cache, you can now do this:

    Bar([1, 2, 3, 4, 5]).get()

And again, to remove values:

    Bar([1, 2, 3, 4, 5]).dirty()

If some of those values are in the cache and some aren't, then only the values with misses will be queried.

If you need to do something more complex then a simple `where in` query, then you can just override the `pull` method, like we did before. Since `pull` will be called on a list of items this time, `items` will be given as a parameter to the method. This time, `pull` must return a dictionary indexed by each item. Here's an example:

    class Bar(kata.container.Attribute):
        def cache(self):
            return kata.cache.memcached

        def key(self, item):
            return 'bar:%s' % item

        def pull(self, items):
            result = {}
            for item in items:
                result[item] = some_expensive_thing(item)

            return result
