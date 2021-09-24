import json
from typing import Dict, Iterator, Optional


def format_list_of_words(first: str, *rest: str):
    if not rest:
        return first
    if len(rest) == 1:
        return f"{first} and {rest[0]}"
    return ", ".join([first] + list(rest[:-1])) + f", and {rest[-1]}"


def format_plural_str(formatstr: str, pluralizable: Dict[str, str], use_plural: bool):
    """
    Format text with singular or plural forms of words. Use the singular forms as
    keys in the format string.

    Usage:

    >>> command_list = [...]
    >>> fmtstr = "you need to run {this} {command}:"
    >>> print(
    ...     format_plural_str(
    ...         fmtstr,
    ...         {"this": "these", "command": "commands"},
    ...         len(command_list) == 1
    ...     )
    ... )
    >>> print("  " + "\n  ".join(command_list))
    """
    argdict = {
        singular: plural if use_plural else singular
        for singular, plural in pluralizable.items()
    }
    return formatstr.format(**argdict)


def sorted_json_field(key):
    """Define sorted JSON output for text output containing complex types."""

    def field_func(data):
        return json.dumps(data[key], sort_keys=True)

    field_func._filter_key = key
    return field_func


class CLIStubResponse:
    """
    A stub response class to make arbitrary data accessible in a way similar to a
    GlobusHTTPResponse object.
    """

    def __init__(self, data):
        self.data = data

    def __getitem__(self, key):
        return self.data[key]


# wrap to add a `has_next()` method and `limit` param to a naive iterator
class PagingWrapper:
    def __init__(self, iterator: Iterator, limit: Optional[int] = None):
        self.iterator = iterator
        self.next = None
        self.limit = limit
        self._step()

    def _step(self):
        try:
            self.next = next(self.iterator)
        except StopIteration:
            self.next = None

    def has_next(self):
        return self.next is not None

    def __iter__(self):
        yielded = 0
        while self.has_next() and (self.limit is None or yielded < self.limit):
            cur = self.next
            self._step()
            yield cur
            yielded += 1
