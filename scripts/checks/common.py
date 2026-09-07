"""Safe parsing and validation primitives; errors never include configuration values."""
import base64
import binascii
import re

import yaml


class Invalid(Exception):
    pass


def require(condition, rule):
    if not condition:
        raise Invalid(rule)


def documents(text):
    try:
        result = [o for o in yaml.safe_load_all(text) if o is not None]
    except yaml.YAMLError:
        raise Invalid('YAML_PARSE_FAILED') from None
    require(all(isinstance(o, dict) for o in result), 'YAML_OBJECT_REQUIRED')
    return result


def read_yaml(path):
    return documents(path.read_text())


def secret_data(obj):
    values = {}
    try:
        for key, value in obj.get('data', {}).items():
            require(isinstance(value, str), 'SECRET_ENCODING_INVALID')
            values[key] = base64.b64decode(value.replace('\n', '').replace('\r', ''), validate=True).decode('utf-8')
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        raise Invalid('SECRET_ENCODING_INVALID') from None
    values.update(obj.get('stringData', {}))
    return values


def placeholder(value):
    value = str(value)
    return not value.strip() or 'CHANGE_ME' in value or bool(re.search(r'<[^>]+>', value))


def example_value(value):
    return bool(re.search(r'(?<![\w-])(?:[\w.-]+\.)?example\.(?:com|net|org)(?=[:/\s]|$)', str(value)))

