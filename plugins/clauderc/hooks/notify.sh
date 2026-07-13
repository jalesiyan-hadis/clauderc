#!/usr/bin/env bash
# Claude Code notification hook.
# Usage: notify.sh <input|done>
# Detects the terminal that launched Claude and activates the right app on click.

mode="${1:-input}"

case "$mode" in
  done)
    subtitle="Done"
    message="Turn finished"
    sound="Pop"
    group="claude-code-done"
    ;;
  *)
    subtitle="Waiting for you"
    message="Claude needs your input"
    sound="Glass"
    group="claude-code-input"
    ;;
esac

# Pick the bundle id of the host terminal so clicking the notification
# focuses the correct window (VSCode, kitty, iTerm, Terminal, ...).
if [ -n "$KITTY_WINDOW_ID" ]; then
  activate="net.kovidgoyal.kitty"
else
  case "$TERM_PROGRAM" in
    vscode)         activate="com.microsoft.VSCode" ;;
    iTerm.app)      activate="com.googlecode.iterm2" ;;
    Apple_Terminal) activate="com.apple.Terminal" ;;
    WezTerm)        activate="com.github.wez.wezterm" ;;
    ghostty)        activate="com.mitchellh.ghostty" ;;
    *)              activate="" ;;
  esac
fi

if command -v terminal-notifier >/dev/null; then
  args=(-title 'Claude Code' -subtitle "$subtitle" -message "$message" -sound "$sound" -group "$group")
  [ -n "$activate" ] && args+=(-activate "$activate")
  terminal-notifier "${args[@]}"
else
  osascript -e "display notification \"$message\" with title \"Claude Code\" sound name \"$sound\""
fi
