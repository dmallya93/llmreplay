# Launch / visibility copy

Paste-ready posts. Do **not** spam the same text everywhere — tweak per channel.

---

## Show HN (Hacker News)

**Title:** Show HN: LLMReplay – VCR / time-travel for Claude Code and Codex

**Body:**

```
I built LLMReplay because agent tests either burn tokens in CI or rely on
hand-written mocks that drift from real SDK payloads.

Record one Claude Code / Codex turn through a local proxy, commit the
scrubbed cassette, then replay offline with a SHA-256 match key (tool order
normalized, secrets HMAC-scrubbed). Misses get a why diff.

pip install coding-agent-vcr   # CLI: llmreplay
https://github.com/dmallya93/llmreplay

One terminal, no API key: llmreplay demo
```

---

## Reddit / Discord one-liner + short post

**Title options:**
- Offline CI for Claude Code / Codex without API keys
- VCR for coding agents — record once, replay forever

**Body:**

```
If your agent CI is either (a) flaky live API calls or (b) a mock farm,
try LLMReplay: VCR-style cassettes for Anthropic Messages + OpenAI Chat/Responses.

pip install coding-agent-vcr
llmreplay demo          # one terminal, no keys

# then with a real agent:
export LLMREPLAY_HMAC_KEY=dev-local-hmac
llmreplay run --mode record --cassette .llmreplay/demo \
  --upstream https://api.anthropic.com -- claude --print "hi"
llmreplay run --mode replay --cassette .llmreplay/demo -- claude --print "hi"

Repo + GIFs: https://github.com/dmallya93/llmreplay
```

Channels worth posting (once each, engage replies):
- r/ClaudeAI, r/LocalLLaMA, r/Python, r/devops
- Anthropic Discord, Cursor Discord, OpenAI / Codex communities
- Twitter/X + LinkedIn with the social preview image

---

## Awesome-list PR blurb

Target: https://github.com/hesreallyhim/awesome-claude-code  
(also consider webfuse-com/awesome-claude, testing/awesome-python lists)

```markdown
- [LLMReplay](https://github.com/dmallya93/llmreplay) - VCR / time-travel replay for Claude Code and Codex: record once, replay offline, hermetic CI goldens (`pip install coding-agent-vcr`).
```

---

## GitHub checklist (repo owner)

- [x] Discussions enabled
- [x] GitHub Release `v0.2.0` published
- [ ] **Settings → General → Social preview** → upload `docs/assets/social-preview.jpg`
- [ ] Pin `llmreplay` on your GitHub profile
- [ ] Star your own repo (signals “active”)
- [ ] Open 1–2 “good first issue” / “help wanted” issues (empty issues look abandoned)
- [ ] Cross-link from personal site / Morph / LinkedIn featured

---

## What actually moves the needle

1. **One Show HN** on a weekday morning US time  
2. **One Awesome-list PR** merged  
3. **One thread** in a Claude Code Discord with the hero GIF  
4. **Ask 3 teammates / friends** to star + try `smoke.sh` (seed social proof)

Docs/GIFs help *conversion* after someone lands. Distribution gets them to land.
