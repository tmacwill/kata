import setuptools

setuptools.setup(
    name='kata',
    version='0.0.1',
    author='Tommy MacWilliam',
    packages=setuptools.find_packages(),
    install_requires=[
        'falcon',
        'gunicorn',
        'msgpack-python',
        'natsort',
        'psycopg2',
        'pymemcache',
        'pyyaml',
        'redis',
        'statsd',
    ]
)
