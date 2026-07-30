# Examples

| Example | Purpose |
|---|---|
| `hello-fake-upstream/` | Hermetic record→replay (`./scripts/smoke.sh`) |
| `claude-code-hello/` | Claude Code wiring + hooks |
| `codex-hello/` | Codex / Responses wiring |
| `llmreplay.yaml` | Sample profiles |

```bash
pip install -e ".[dev]"
llmreplay doctor
./scripts/smoke.sh
pytest -q
```
