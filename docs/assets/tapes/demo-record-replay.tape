# LLMReplay hero demo — hermetic record → replay
Output docs/assets/demo-record-replay.gif

Require llmreplay

Set Shell "zsh"
Set FontSize 16
Set Width 980
Set Height 520
Set TypingSpeed 40ms
Set Theme "Catppuccin Mocha"
Set PlaybackSpeed 1.1
Set WindowBar Colorful

Hide
Type "cd /Users/dkasargod/workspace/llmreplay && source .venv/bin/activate && export LLMREPLAY_HMAC_KEY=dev-local-hmac && clear"
Enter
Sleep 500ms
Show

Type "# LLMReplay — VCR for coding agents"
Enter
Sleep 800ms
Type "clear"
Enter
Sleep 200ms
Type "./scripts/demo_record.sh"
Enter
Sleep 5s
Type "# pip install coding-agent-vcr   # CLI: llmreplay"
Enter
Sleep 2s
