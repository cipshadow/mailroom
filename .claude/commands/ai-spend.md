---
name: ai-spend
description: Audit Claude Code token efficiency — MCP overhead, session patterns, skill cost, cache hit rate. Add --full for Hubble dollar data.
model: sonnet
user-invocable: true
---

Audit Claude Code token spend and surface efficiency wins. Quantify everything in dollars.

**Argument:** `$ARGUMENTS`
- No argument → local-only audit (instant, no Hubble query)
- `--full` → include Layer 1: actual dollar spend from Hubble

---

## Data gathering

Run ALL of the following bash commands **in parallel**. Collect the outputs before synthesizing anything.

### Bash 1: Stats-cache — model usage and daily activity
```bash
python3 - << 'EOF'
import json, os
from datetime import datetime, timedelta

with open(os.path.expanduser('~/.claude/stats-cache.json')) as f:
    d = json.load(f)

# Model usage (lifetime totals)
print("=== MODEL_USAGE ===")
pricing = {
    'claude-opus-4-6':       {'in': 15, 'out': 75, 'cr': 1.875, 'cc': 18.75},
    'claude-sonnet-4-6':     {'in': 3,  'out': 15, 'cr': 0.375, 'cc': 3.75},
    'claude-haiku-4-5-20251001': {'in': 0.80, 'out': 4, 'cr': 0.08, 'cc': 1.0},
    'claude-opus-4-5-20251101':  {'in': 15, 'out': 75, 'cr': 1.875, 'cc': 18.75},
    'claude-sonnet-4-5-20250929':{'in': 3,  'out': 15, 'cr': 0.375, 'cc': 3.75},
}
for model, stats in d.get('modelUsage', {}).items():
    p = pricing.get(model, {'in': 3, 'out': 15, 'cr': 0.375, 'cc': 3.75})
    i  = stats.get('inputTokens', 0)
    o  = stats.get('outputTokens', 0)
    cr = stats.get('cacheReadInputTokens', 0)
    cc = stats.get('cacheCreationInputTokens', 0)
    cost = (i * p['in'] + o * p['out'] + cr * p['cr'] + cc * p['cc']) / 1e6
    total = i + o + cr + cc
    hit_rate = round(cr / max(cr + cc + i, 1) * 100, 1)
    print(f"  {model}: input={i:,} output={o:,} cache_read={cr:,} cache_create={cc:,} est_cost=${cost:.2f} cache_hit={hit_rate}%")

# Daily activity — last 14 days
print("\n=== DAILY_ACTIVITY (last 14 days) ===")
da = d.get('dailyActivity', [])
cutoff = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
recent = [x for x in da if x.get('date','') >= cutoff]
for r in recent[-14:]:
    print(f"  {r['date']}: sessions={r.get('sessionCount',0)} msgs={r.get('messageCount',0)} tools={r.get('toolCallCount',0)}")

# Daily model tokens — last 14 days
print("\n=== DAILY_MODEL_TOKENS (last 14 days) ===")
dmt = d.get('dailyModelTokens', [])
recent_t = [x for x in dmt if x.get('date','') >= cutoff]
for r in recent_t[-14:]:
    print(f"  {r['date']}: {r.get('tokensByModel',{})}")

print(f"\n=== TOTALS ===")
print(f"  totalSessions={d.get('totalSessions',0)} totalMessages={d.get('totalMessages',0)}")
longest = d.get('longestSession', {})
print(f"  longestSession: {longest.get('messageCount',0)} messages")
EOF
```

### Bash 2: Setup overhead — MCP servers, context files, skill files
```bash
python3 - << 'EOF'
import json, os, glob

# MCP server counts
print("=== MCP_SERVERS ===")
# User-level (claude.json)
try:
    with open(os.path.expanduser('~/.claude.json')) as f:
        cj = json.load(f)
    user_servers = list(cj.get('mcpServers', {}).keys())
    print(f"  user-level (~/.claude.json): {len(user_servers)} servers: {user_servers}")
except: print("  user-level: error reading")

# Project-level (settings.local.json)
try:
    with open(os.path.expanduser('~/.claude/settings.local.json')) as f:
        sl = json.load(f)
    mcp_json = sl.get('enabledMcpjsonServers', [])
    all_proj = sl.get('enableAllProjectMcpServers', False)
    print(f"  enabledMcpjsonServers: {len(mcp_json)} servers: {mcp_json}")
    print(f"  enableAllProjectMcpServers: {all_proj}")
except: print("  settings.local.json: error reading")

# Estimate tool count per MCP server — adapt these to your own servers
# Format: 'server_name': estimated_tool_count
server_tool_estimates = {
    # Add your MCP servers here, e.g.:
    # 'my_google_drive': 40, 'my_slack': 8, 'my_calendar': 9,
}
all_servers = set(user_servers) | set(mcp_json)
est_tools = sum(server_tool_estimates.get(s, 12) for s in all_servers)
est_tokens = round(est_tools * 55 / 4)
print(f"\n  Estimated total tools: ~{est_tools}")
print(f"  Estimated deferred list tokens: ~{est_tokens:,} tokens/turn")
# Cost estimate at Opus cache read price (most turns are cache reads)
monthly_turns = 60 * 20  # 60 sessions × 20 turns avg
monthly_cost = monthly_turns * est_tokens * 1.875 / 1e6
print(f"  Estimated MCP overhead cost: ~${monthly_cost:.1f}/month (Opus cache read, 60 sessions × 20 turns)")

# Global context files
print("\n=== CONTEXT_FILES ===")
context_files = [
    '~/.claude/CLAUDE.md',
    '~/.claude/rules/discipline.md',
    '~/.claude/rules/hubble-queries.md',
    '~/.claude/rules/terminology.md',
    '~/.claude/rules/writing-style.md',
    # Add your own memory file if you use one, e.g.:
    # '~/.claude/memory/MEMORY.md',
]
total_bytes = 0
for f in context_files:
    path = os.path.expanduser(f)
    try:
        size = os.path.getsize(path)
        total_bytes += size
        print(f"  {os.path.basename(f)}: {size:,} bytes (~{round(size/4):,} tokens)")
    except: print(f"  {os.path.basename(f)}: not found")
print(f"  TOTAL context overhead: {total_bytes:,} bytes (~{round(total_bytes/4):,} tokens/turn)")
ctx_cost = 60 * 20 * (total_bytes/4) * 1.875 / 1e6
print(f"  Estimated cost: ~${ctx_cost:.1f}/month")

# Skill files
print("\n=== SKILL_FILES ===")
skills = sorted(glob.glob(os.path.expanduser('~/.claude/commands/*.md')), key=os.path.getsize, reverse=True)
for s in skills:
    size = os.path.getsize(s)
    name = os.path.basename(s).replace('.md','')
    flag = ' ← HEAVY' if size > 20000 else (' ← large' if size > 10000 else '')
    print(f"  /{name}: {size:,} bytes ({round(size/1024,1)}KB){flag}")
EOF
```

### Bash 3: Recent skill invocations and session patterns
```bash
python3 - << 'EOF'
import json, os
from datetime import datetime, timedelta
from collections import Counter

cutoff_ms = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)

# Skill invocation frequency (last 30 days)
print("=== SKILL_INVOCATIONS (last 30 days) ===")
skills = Counter()
total_prompts = 0
try:
    with open(os.path.expanduser('~/.claude/history.jsonl')) as f:
        for line in f:
            try:
                e = json.loads(line)
                if e.get('timestamp', 0) >= cutoff_ms:
                    total_prompts += 1
                    d = e.get('display', '')
                    if d.startswith('/'):
                        skill = d.split()[0]
                        skills[skill] += 1
            except: pass
    print(f"  Total prompts this month: {total_prompts}")
    print(f"  Skill invocations:")
    for skill, count in skills.most_common(15):
        print(f"    {skill}: {count}x")
except Exception as e:
    print(f"  Error: {e}")

# Recent session sampling — compute cache hit rate and turns from 5 most recent JSONL files
print("\n=== RECENT_SESSIONS (5 most recent) ===")
import glob

# Set this to your most-used Claude project directory
# Find yours with: ls ~/.claude/projects/ | head -5
proj_dir = os.path.expanduser('~/.claude/projects/')  # adapt to your project path
files = sorted(glob.glob(proj_dir + '*.jsonl'), key=os.path.getmtime, reverse=True)[:5]

for fpath in files:
    try:
        messages = []
        with open(fpath) as f:
            for line in f:
                try: messages.append(json.loads(line))
                except: pass

        assistant_msgs = [m for m in messages if m.get('type') == 'assistant']
        total_in, total_out, total_cr, total_cc = 0, 0, 0, 0
        models_used = set()
        for m in assistant_msgs:
            u = m.get('message', {}).get('usage', {})
            total_in += u.get('input_tokens', 0)
            total_out += u.get('output_tokens', 0)
            total_cr  += u.get('cache_read_input_tokens', 0)
            total_cc  += u.get('cache_creation_input_tokens', 0)
            model = m.get('message', {}).get('model', '')
            if model: models_used.add(model.replace('claude-','').replace('-20251001','').replace('-20251101','').replace('-20250929',''))

        total_tok = total_in + total_out + total_cr + total_cc
        hit_rate = round(total_cr / max(total_cr + total_cc + total_in, 1) * 100, 1)

        # Estimate cost based on primary model
        primary = 'opus-4-6' if 'opus-4-6' in models_used else ('sonnet-4-6' if 'sonnet-4-6' in models_used else list(models_used)[0] if models_used else '?')
        p = {'opus-4-6': {'in':15,'out':75,'cr':1.875,'cc':18.75}}.get(primary, {'in':3,'out':15,'cr':0.375,'cc':3.75})
        est_cost = (total_in*p['in'] + total_out*p['out'] + total_cr*p['cr'] + total_cc*p['cc']) / 1e6

        fname = os.path.basename(fpath)[:8]
        print(f"  {fname}... {len(messages)} msgs | models: {models_used} | turns: {len(assistant_msgs)} | cache_hit: {hit_rate}% | est: ${est_cost:.3f}")
    except Exception as e:
        print(f"  {os.path.basename(fpath)}: error — {e}")
EOF
```

---

## Synthesis

After collecting all outputs, produce this report. Fill in every `[X]` from the actual data. Do NOT present raw bash output — compute and summarize.

```
## AI Spend Audit — [today's date]

### Token overhead per turn (what you pay before doing any actual work)

| Source | Tokens | Est. $/month |
|--------|--------|--------------|
| MCP deferred tool names | ~[X],XXX | ~$[X] |
| Global rules + CLAUDE.md + memory | ~[X],XXX | ~$[X] |
| **Total fixed overhead** | **~[X],XXX** | **~$[X]** |

*Assumptions: [N] sessions/month × [N] turns/session avg; Opus cache read pricing ($1.875/M).*

---

### Skill file sizes (cost applies when invoked)

| Skill | Size | Note |
|-------|------|------|
| /prettier-slides | [X] KB | [cost driver] |
| /authnalyze | [X] KB | [cost driver] |
| ... (top 8 by size) | | |

---

### Lifetime model usage

| Model | Est. cost (lifetime) | Cache hit rate | Proportion |
|-------|---------------------|---------------|------------|
| claude-opus-4-6 | $[X] | [X]% | [X]% |
| claude-sonnet-4-6 | $[X] | [X]% | [X]% |
| ... | | | |

Cache hit rate = cache_read / (cache_read + cache_create + input). Higher = better. <70% suggests frequent cache invalidation (long sessions with many edits, or short sessions that don't reuse context).

---

### Session patterns (last 14 days)

| Metric | Value |
|--------|-------|
| Avg sessions/day | [X] |
| Avg messages/session | [X] |
| Avg tool calls/session | [X] |
| Peak day | [date] ([X] messages, [X] sessions) |

---

### Skill usage this month (top invocations)

| Skill | Invocations | Notes |
|-------|-------------|-------|
| /[skill] | [N]x | [flag if expensive] |
| ... | | |

---

### Recent session efficiency (5 most recent)

| Session | Turns | Models | Cache hit | Est. cost |
|---------|-------|--------|-----------|-----------|
| [id]... | [N] | [models] | [X]% | $[X] |
| ... | | | | |

---

### Recommendations

Apply these rules to the actual data. Only include rules that fire based on what you found:

**Model mix:**
- If opus cost >80% of lifetime est. cost: "Opus dominates at [X]% of estimated lifetime cost. Every skill without `model: sonnet` defaults to Opus. Adding `model: sonnet` to /[top-skill-without-override] would save ~$[estimate]/month at current usage."

**Cache efficiency:**
- If any model has cache hit <70%: "Low cache hit rate on [model] ([X]%). Likely cause: [short sessions OR many context edits OR skill chaining resetting cache]. Fix: consolidate related work into single sessions rather than many short ones."

**Setup overhead:**
- If MCP tool count >300: "MCP tool names add ~[X] tokens per turn. Current: [N] servers → ~[X] tools. Cleanup saved [X] tools on 2026-07-01. Further reduction possible: [specific servers]."
- If context files >10KB: "Fixed context overhead is [X] tokens/turn ([X] KB). Consider moving rarely-used rules to per-project CLAUDE.md files."

**Heavy skills:**
- For any skill >30KB: "/[skill] at [X]KB loads entirely on every invocation. [Specific split suggestion based on what's in the file]."

**Skill chaining:**
- If /ho appears in top invocations AND anti-sloppifier is chained: "/ho auto-chains /anti-sloppifier (Opus, reads full conversation). At [N] invocations/month, this costs ~$[estimate]. Make it opt-in with a flag."

**Session length:**
- If any session >500 messages: "Session [id] had [X] messages. Long sessions cause context compression and cache invalidation. Break work into focused sessions of <200 messages."
```

---

## Layer 1: Actual spend query (only if `--full` was passed)

If your organization provides LLM usage logs in a data warehouse, query them here for actual dollar spend. Adapt to your own table schema.

If you have Anthropic API billing access, you can also pull spend from the Anthropic console API or billing exports.

Add to the report:

```
### Actual dollar spend (last 30 days)

| Day | Model | Cost | Requests |
|-----|-------|------|----------|
| ... | ... | ... | ... |

**Total:** $[X] | vs prior 30 days: $[Y] ([+/-Z]%)
**Top model:** [model] ($[X], [N]%)
**Highest day:** [date] ($[X]) — [N] sessions that day
```

Then compare the local estimate from model usage stats against the actuals and note the delta.
