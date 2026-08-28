# confargs examples

Self-contained, runnable examples. They are exercised by the test suite
(`tests/test_example.py`), so they always match the current API.

| File | Shows |
| --- | --- |
| [`demo.py`](demo.py) | A complete `greeter` CLI: value options, boolean flag with `--no-` negation, environment variables (`GREETER_*`), TOML discovery and an eager `--argumentfile`. |
| [`example.args`](example.args) | A sample argument file consumed by `demo.py -A`. |

Run them from the repository root without installing anything:

```bash
uv run python examples/demo.py --who Ada --repeat 3
uv run python examples/demo.py --no-color
GREETER_WHO=Ada uv run python examples/demo.py
uv run python examples/demo.py -A examples/example.args
uv run python examples/demo.py --help
```

For the installed console-script version of a demo tool, see
[`confargs.demo`](../src/confargs/demo.py) and run `uv run confargs-demo --help`.
