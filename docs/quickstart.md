# Quickstart (full free-stack path lands in C5)

```bash
pip install -e ".[dev]"
llmreplay version
llmreplay doctor
llmreplay exit-codes
pytest -q
```

When C5 ships:

```bash
llmreplay test-stack up
llmreplay keys create --free
llmreplay record --free -- claude "..."
llmreplay replay cassette/ --profile local --free -- claude "..."
```
