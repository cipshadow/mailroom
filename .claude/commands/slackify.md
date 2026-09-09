---
model: sonnet
name: slackify
description: Take text and make it cleanly pastable into Slack by removing artificial line breaks introduced by terminal wrapping, while preserving intentional structure.
---
Take text and make it cleanly pastable into Slack by removing artificial line breaks introduced by terminal wrapping, while preserving intentional structure.

## Input

Accept one of:
- A file path argument (read the file)
- If no argument, take the last substantial text output from this conversation

## Rules

1. **Unwrap paragraphs.** Join lines that were split mid-sentence by terminal column width. A line that ends without a period, colon, or list marker and is followed by a line that starts lowercase or continues a sentence — join them.

2. **Preserve intentional breaks:**
   - Blank lines between paragraphs → keep as single blank line
   - Lines starting with `•`, `-`, `*`, or `1.`–`99.` → keep as new lines (these are list items)
   - Lines that are headings (all caps, or very short followed by a blank line) → keep
   - Lines ending with `:` → keep (they introduce something)

3. **Strip markdown formatting that Slack doesn't understand:**
   - `**bold**` or `__bold__` → leave as plain text (Slack uses its own bold with surrounding text)
   - ` ``` ` code fences → keep the content, remove the fences
   - `> ` blockquote markers → remove

4. **Don't touch:**
   - URLs
   - Code blocks (content within fences)
   - Emoji shortcodes like `:thread:`

## Output

1. Write the cleaned text to a temporary file at `/tmp/slackified.txt`
2. Copy it to clipboard using `pbcopy < /tmp/slackified.txt`
3. Confirm: "Copied to clipboard. Paste into Slack."
4. Also print the cleaned text so I can verify it looks right.
