"""Configuration loading utilities."""

import ast
import json
from pathlib import Path
from typing import Dict


def load_api_config() -> Dict[str, str]:
    """
    Load API configuration from data_config.py.
    
    Returns:
        Dict mapping filename to security name
    """
    config_path = Path(__file__).parent / "data_config.py"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        
        result = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'DATA_SOURCES':
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Call):
                                    symbol = name = None
                                    for kw in elt.keywords:
                                        if kw.arg == 'symbol' and isinstance(kw.value, ast.Constant):
                                            symbol = kw.value.value
                                        if kw.arg == 'name' and isinstance(kw.value, ast.Constant):
                                            name = kw.value.value
                                    if symbol:
                                        filename = symbol.replace('.', '_') + '.xlsx'
                                        result[filename] = name or symbol
        return result
    except Exception:
        return {}


def load_security_cache() -> Dict[str, str]:
    """
    Load security names from cache file.
    
    Returns:
        Dict mapping symbol to security name
    """
    cache_file = Path("data") / "security_names.json"
    if not cache_file.exists():
        return {}
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}
