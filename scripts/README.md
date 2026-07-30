# Scripts

| Script | Purpose |
|---|---|
| `smoke.sh` | Hermetic record→replay against an in-process fake upstream |
| `release_smoke.sh` | Clean venv install → help/doctor → offline fixture replay |
| `mutation_gate.sh` | Pytest coverage floor (>=95%) on critical modules |
| `repro_stress.sh` | Multi-tool / chain / N-fold replay reproducibility suite |

Prefer `bash scripts/<name>.sh` (works when `./` +x or shebang PATH differs).

See [docs/ci.md](../docs/ci.md) and the README **Testing & validation** section.
