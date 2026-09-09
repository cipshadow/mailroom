#!/usr/bin/env bash
# Measure real time spent in a Claude Code session from transcript timestamps.
# Usage: session-time.sh [session-id-or-jsonl-path]
set -euo pipefail

CFG="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
ARG="${1:-}"
IDLE_GAP="${IDLE_GAP:-900}"   # gaps longer than this (sec) count as away, not work

if [[ -f "$ARG" ]]; then F="$ARG"; else
  SLUG="-$(pwd | sed 's|^/||; s|/|-|g')"
  DIR="$CFG/projects/$SLUG"
  [[ -d "$DIR" ]] || DIR="$(ls -dt "$CFG"/projects/*/ 2>/dev/null | head -1)"
  if [[ -n "$ARG" ]]; then F="$DIR/$ARG.jsonl"; else F="$(ls -t "$DIR"/*.jsonl 2>/dev/null | head -1)"; fi
fi
[[ -f "$F" ]] || { echo "no transcript found" >&2; exit 1; }

jq -sr --argjson gap "$IDLE_GAP" '
  [ .[] | select(.timestamp) | {t: (.timestamp | sub("\\.[0-9]+Z$";"Z") | fromdateiso8601), type} ] | sort_by(.t) as $ev
  | ($ev | map(.t)) as $ts
  | ($ts | first) as $start | ($ts | last) as $end
  | [ range(1; ($ts|length)) | ($ts[.] - $ts[.-1]) ] as $deltas
  | ($deltas | map(select(. <= $gap)) | add // 0) as $active
  | ($deltas | map(select(. >  $gap))) as $breaks
  | "start          \($start | strftime("%Y-%m-%d %H:%M"))
end            \($end   | strftime("%Y-%m-%d %H:%M"))
wall clock     \(((($end-$start)/60)|round)) min
active         \((($active/60)|round)) min   (gaps >\($gap/60|round)min excluded)
breaks         \($breaks|length) totalling \((($breaks|add // 0)/60|round)) min"
' "$F"

# what Cip actually contributed
jq -sr '
  [ .[] | select(.type=="user") | .message.content
    | if type=="string" then . else ([.[]? | select(.type=="text") | .text] | join(" ")) end
    | select(type=="string") | select(startswith("<system-reminder>")|not) | select(length>0) ]
  as $u
  | [ .[] | select(.type=="assistant") | .message.content
      | [.[]? | select(.type=="text") | .text] | join(" ") | select(length>0) ] as $a
  | "
your turns     \($u|length)  (\($u | map(length) | add // 0) chars typed)
replies        \($a|length)  (\($a | map(length) | add // 0) chars to read)
reading est    \(((($a | map(length) | add // 0) / 5 / 250) | round)) min at 250 wpm"
' "$F"
