# Publishing to PyPI

Package name on PyPI: **`llm-replay`** (the name `llmreplay` is taken by an unrelated project).
CLI / import remain `llmreplay`.

## One-time Trusted Publisher setup

1. Create a PyPI account (if needed) and enable 2FA.
2. Open [PyPI publishing settings](https://pypi.org/manage/account/publishing/) → **Add a new pending publisher**:
   - **PyPI project name:** `llm-replay`
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
pip install -U llm-replay
llmreplay version
```

## Social preview (GitHub)

Repo → **Settings** → **General** → **Social preview** → upload
[`docs/assets/social-preview.jpg`](assets/social-preview.jpg).
