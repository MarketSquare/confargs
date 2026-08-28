"""Environment-variable configuration source.

Reading an option from the environment is **opt-in** per option via the
``env`` argument to :func:`~confargs.option`:

* ``@option(env=True)`` uses a name generated from the config class'
  ``env_var_template`` (by default ``"{name}_{option}"`` upper-cased, e.g.
  ``MYTOOL_LOG``), and
* ``@option(env="MY_TOOL_LOG")`` sets an explicit variable name verbatim.

Options left at the default ``env=False`` are never read from the environment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from confargs.options import Option

DEFAULT_ENV_VAR_TEMPLATE = "{name}_{option}"


def env_var_name(
    option: Option,
    tool_name: str,
    *,
    template: str = DEFAULT_ENV_VAR_TEMPLATE,
) -> str | None:
    """Return the environment variable name for ``option``, or ``None``.

    An explicit string ``env`` is used verbatim; ``env=True`` formats
    ``template`` with ``name`` (the tool name) and ``option`` (the attribute
    name) and upper-cases the result; ``env=False`` disables the source.
    """
    spec = option.env
    if spec is True:
        return template.format(name=tool_name, option=option.attr_name).upper()
    if isinstance(spec, str) and spec:
        return spec
    return None


def collect_env_values(
    options: Mapping[str, Option],
    tool_name: str,
    *,
    template: str = DEFAULT_ENV_VAR_TEMPLATE,
    environ: Mapping[str, str],
) -> dict[str, str]:
    """Collect raw option values present in ``environ``."""
    values: dict[str, str] = {}
    for attr, option in options.items():
        name = env_var_name(option, tool_name, template=template)
        if name is not None and name in environ:
            values[attr] = environ[name]
    return values
