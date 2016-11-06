import kata
import kata.assets
import kata.config
import os
import subprocess

def run():
    gunicorn_config = kata.config.data['gunicorn']['config']
    gunicorn_module = kata.config.data['gunicorn']['module']
    debug = kata.config.data.get('debug')

    gunicorn_args = ['gunicorn']
    reload = ''
    if debug:
        gunicorn_args += ['--reload']
    gunicorn_args += ['-c', gunicorn_config, '%s:app' % gunicorn_module]

    if kata.config.data.get('assets'):
        kata.assets.build(watch=debug, production=not debug)

    subprocess.call(gunicorn_args)
