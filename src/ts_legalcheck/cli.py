import json
import click
import pathlib
import typing as t


from .engine import createEngineWithDefinitions, loadDefinitions
from .engine.context import Component, Module
from .utils import setup_logging

def _createEngine(paths: t.List[pathlib.Path]):
    defs = loadDefinitions(paths)
    return createEngineWithDefinitions(defs)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--defs', '-d', 'defs', type=click.Path(exists=True, path_type=pathlib.Path), default=[],
              multiple=True, required=False, help='File with constraints definitions')
@click.option('--verbose', 'verbose', default=False, is_flag=True, required=False, help='Enable verbose output')
@click.argument('path', type=click.Path(exists=True, path_type=pathlib.Path), required=True)
def check(defs, verbose, path):
    if verbose:
        setup_logging()

    if mod := Module.load(path):
        engine = _createEngine(list(defs))

        result = engine.checkModule(mod)
        result = json.dumps(result, indent=2)

        print(result)


@cli.command()
@click.option('--defs', '-d', 'defs', type=click.Path(exists=True, path_type=pathlib.Path), default=(),
              multiple=True, required=False, help='File with constraints definitions')
@click.option('-l', '--license', 'lic', type=str, required=True, help='License key to test the input against')
@click.option('--verbose', 'verbose', default=False, is_flag=True, required=False, help='Enable verbose output')
@click.argument('path', type=click.Path(exists=True, path_type=pathlib.Path), required=True)
def test(defs, lic, verbose, path):
    from .testing import test_license
    
    if verbose:
        setup_logging()
    
    engine = _createEngine(list(defs))

    if result := test_license(engine, lic, path):
        print(json.dumps(result.to_dict(), indent=2))



@cli.command()
@click.option('--port', '-p', 'port', type=int, default=5000, envvar='TS_LEGALCHECK_WEBUI_PORT', required=False, help='Port to run the web server on')
def start(port):
    from .ui import run
    run(port=port)


if __name__ == '__main__':
    cli()