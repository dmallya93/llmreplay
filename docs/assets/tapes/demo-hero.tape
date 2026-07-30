# LLMReplay one-liner install + doctor (shortest hero loop)
Output docs/assets/demo-hero.gif

Require llmreplay

Set Shell "zsh"
Set FontSize 18
Set Width 900
Set Height 420
Set TypingSpeed 35ms
Set Theme "Catppuccin Mocha"
Set PlaybackSpeed 1.15
Set WindowBar Colorful

Hide
Type "cd /Users/dkasargod/workspace/llmreplay && source .venv/bin/activate && export LLMREPLAY_HMAC_KEY=dev-local-hmac && clear"
Enter
Sleep 500ms
Show

Type "echo 'pip install coding-agent-vcr  # CLI: llmreplay'"
Enter
Sleep 700ms
Type "export LLMREPLAY_HMAC_KEY=dev-local-hmac"
Enter
Sleep 400ms
Type "llmreplay doctor"
Enter
Sleep 3s
Type "./scripts/demo_record.sh"
Enter
Sleep 5s
Type "# offline. zero tokens."
Enter
Sleep 1.5s
