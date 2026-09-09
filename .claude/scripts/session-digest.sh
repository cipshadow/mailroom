#!/usr/bin/env bash
# Extract a token-lean audit digest from a Claude Code session transcript.
# Keeps: user prompts, assistant prose, a one-line summary per tool call.
# Drops: tool results, system reminders, thinking, file contents — the bulk.
#
# Usage: session-digest.sh [session-id-or-jsonl-path] > digest.txt
# With no argument, uses the newest transcript for the current project.

set -euo pipefail

CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
ARG="${1:-}"

if [[ -f "$ARG" ]]; then
  F="$ARG"
else
  SLUG="-$(pwd | sed 's|^/||; s|/|-|g')"
  DIR="$CFG/projects/$SLUG"
  [[ -d "$DIR" ]] || DIR="$(ls -dt "$CFG"/projects/*/ 2>/dev/null | head -1)"
  if [[ -n "$ARG" ]]; then
    F="$DIR/$ARG.jsonl"
  else
    F="$(ls -t "$DIR"/*.jsonl 2>/dev/null | head -1)"
  fi
fi

[[ -f "$F" ]] || { echo "no transcript found (looked for: ${F:-unset})" >&2; exit 1; }

echo "# Session digest: $(basename "$F" .jsonl)"
echo "# Raw transcript: $(wc -c < "$F" | tr -d ' ') bytes"
echo

jq -r '
  select(.type=="user" or .type=="assistant")
  | .message as $m
  | if (.type=="user") then
      (if ($m.content|type)=="string" then $m.content
       else ([$m.content[]? | select(.type=="text") | .text] | join("\n")) end)
      | select(length>0)
      | select(startswith("<system-reminder>")|not)
      | "\n=== USER ===\n" + .
    else
      ([ $m.content[]? |
         if .type=="text" then .text
         elif .type=="tool_use" then
           "  [tool] " + .name +
           (if .input.description then ": " + .input.description
            elif .input.file_path then ": " + .input.file_path
            elif .input.command then ": " + (.input.command|split("\n")[0]|.[0:100])
            else "" end)
         else empty end
       ] | join("\n"))
      | select(length>0)
      | "\n--- ASSISTANT ---\n" + .
    end
' "$F"
