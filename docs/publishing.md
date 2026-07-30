# Publishing to PyPI

Package name on PyPI: **`coding-agent-vcr`**.

(`llmreplay` and `llm-replay` are unavailable — taken / rejected as too similar.)

CLI / import remain `llmreplay`.

> **Do not run Publish until Trusted Publisher is configured.** Unconfigured runs fail and show red on the Actions tab. CI already builds + `twine check` the package on every push.

## One-time Trusted Publisher setup

1. Create a PyPI account (if needed) and enable 2FA.
2. Open [PyPI publishing settings](https://pypi.org/manage/account/publishing/) → **Add a new pending publisher**:
   - **PyPI project name:** `coding-agent-vcr`
   - **Owner:** `dmallya93`
   - **Repository:** `llmreplay`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
3. Save. (Pending publisher becomes active on first successful upload.)

## Publish a release

```bash
gh workflow run publish.yml -f confirm=publish
gh run watch
```

Then verify:

```bash
pip install -U coding-agent-vcr
llmreplay version
```

## Social preview (GitHub)

Repo → **Settings** → **General** → **Social preview** → upload
[`docs/assets/social-preview.jpg`](assets/social-preview.jpg).
