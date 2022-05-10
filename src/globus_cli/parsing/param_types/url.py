import urllib.parse

import click


class URLType(click.ParamType):
    """Click param type for a URL."""

    name = "url"

    def convert(self, value, param, ctx):
        if not isinstance(value, tuple):
            value = urllib.parse.urlparse(value)
            if not value.netloc:
                self.fail("incomplete URL")
            if value.scheme not in ("http", "https"):
                self.fail(
                    f"invalid URL scheme ({value.scheme}). Only HTTP URLs are allowed",
                    param,
                    ctx,
                )
        return value
