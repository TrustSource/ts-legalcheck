import time
import logging
import typing as t

import json
import toml
import yaml

from pathlib import Path

logger = logging.getLogger('ts_legalcheck.engine')


def time_it(f, *args, **kwargs):
    t = time.time()
    res = f(*args, **kwargs)
    return res, time.time() - t


def get_args(args):
    if len(args) == 1 and isinstance(args[0], list):
        return args[0]
    else:
        return list(args)


def setup_logging():
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(levelname)s] %(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')


def load_file(path: Path) -> t.Optional[dict]:        
    with path.open('r') as fp:
        if path.suffix == '.json':            
            try:
                return json.load(fp)
            except json.JSONDecodeError as err:
                logger.error(f'Cannot decode {str(path)}: {err}')
                return None
            
        elif path.suffix == '.toml':
            try:
                return toml.load(fp)
            except toml.TomlDecodeError as err:
                logger.error(f'Cannot decode {str(path)}: {err}')
                return None
        
        elif path.suffix in ('.yaml', '.yml'):
            try:
                return yaml.safe_load(fp)
            except yaml.YAMLError as err:
                logger.error(f'Cannot decode {str(path)}: {err}')
                return None
            
        else:
            logger.error(f'Unsupported file format: {path.suffix}')
            return None