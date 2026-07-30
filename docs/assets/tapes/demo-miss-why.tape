# LLMReplay miss → why demo
Output docs/assets/demo-miss-why.gif

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

Type "# When replay misses: llmreplay why"
Enter
Sleep 700ms
Type "clear"
Enter
Sleep 200ms
Type "./scripts/demo_miss_why.sh"
Enter
Sleep 6s
Type "# Static prompt drift → miss. Noise fields are ignored."
Enter
Sleep 2s
