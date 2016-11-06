import json
import os
import subprocess
import tempfile
import kata.config
import kata.router

def generate_config(assets):
    routes = kata.router.routes()
    entry = {}
    for route in routes.values():
        entry[route.js()] = './' + assets['src']['js'] + route.js() + '.js'

    return '''
module.exports = {
    entry: %s,
    output: {
        path: './%s',
        filename: '[name].min.js',
    },
    module: {
        loaders: [{
            test: /\.js/,
            exclude: /node_modules/,
            loader: 'babel-loader',
            query: {
                presets: ['es2015', 'react']
            }
        }, {
            test: /\.css/,
            exclude: /node_modules/,
            loader: 'style!css'
        }, {
            test: /\.less/,
            exclude: /node_modules/,
            loader: 'style!css!less'
        }]
    }
};
    ''' % (
        json.dumps(entry),
        assets['build']['js'],
    )

def initialize(assets):
    with open(os.getcwd() + '/webpack.config.js', 'w') as f:
        f.write(generate_config(assets))

def build(watch=False, production=False, wait=False):
    args = ['webpack']
    if watch:
        args.append('--watch')
    if production:
        args.append('-p')

    if not wait:
        subprocess.Popen(args)
    else:
        subprocess.call(args)
