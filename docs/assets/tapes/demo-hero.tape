# LLMReplay hero — one terminal start→end
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
Type "source .venv/bin/activate && clear"
Enter
Sleep 500ms
Show

Type "echo 'pip install coding-agent-vcr  # CLI: llmreplay'"
Enter
Sleep 700ms
Type "llmreplay demo"
Enter
Sleep 6s
Type "# one terminal. no keys. gateway included."
Enter
Sleep 1.5s
