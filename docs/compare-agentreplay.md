# LLMReplay vs AgentReplay

| | LLMReplay | AgentReplay |
|---|---|---|
| Primary job | Controllable **replay** (VCR / time-travel) | Local **observability** + evals |
| Question answered | “Can I re-run and assert this trajectory?” | “What did the agent do / cost / score?” |
| CI goldens | First-class strict cassettes | Traces/evals, not fixture re-execution |
| Free offline loop | CCR + Ollama via `--free` (C5) | Local traces; different product surface |
| Mutate run | `tweak` / `fork` / breakpoints | Inspect & evaluate |

Both can coexist: observe with AgentReplay; lock regressions with LLMReplay.
