---
model: sonnet
description: Converts a pretty-slides HTML deck to Google Slides and uploads it to Drive
argument-hint: deck.html [--share email1,email2] [--folder FOLDER_ID]
---

# HTML to Google Slides

Full pipeline: pretty-slides HTML → Puppeteer screenshots → PPTX → Google Slides (uploaded + shared).

## Workflow

### Step 1: Parse arguments from `$ARGUMENTS`

- Required: `<deck.html>` — filename relative to `~/.claude/slides/` (with or without `.html`). Also accepts an absolute path.
- Optional: `--share email1,email2` — full email addresses to share with. Default: none.
- Optional: `--folder FOLDER_ID` — Google Drive folder to upload into. Default: `DEFAULT_SLIDES_FOLDER_ID` below.

Derive `DECK_NAME` by stripping the `.html` extension and any directory prefix.

**DEFAULT_SLIDES_FOLDER_ID**: `YOUR_DRIVE_FOLDER_ID`
> Replace this with your own Google Drive folder ID.

### Step 2: Screenshot every slide

If the HTML file is not already in `~/.claude/slides/`, copy it there first:

```bash
cp /path/to/deck.html ~/.claude/slides/
```

Then screenshot:

```bash
cd ~/.claude/slides
node screenshot-slides.js ${DECK_NAME}.html
```

Produces `screenshots/${DECK_NAME}/slide-01.png`, `slide-02.png`, etc. at 3840×2160 (3× retina).

### Step 3: Compress screenshots

Large slides can produce huge PPTX files. Compress to keep the upload fast:

```bash
for f in ~/.claude/slides/screenshots/${DECK_NAME}/*.png; do
  sips -Z 1280 "$f" --out "$f" -s format jpeg -s formatOptions 85 2>/dev/null
  mv "${f%.png}.jpeg" "${f%.png}.png" 2>/dev/null || true
done
```

### Step 4: Build PPTX

```bash
cd ~/.claude/slides
python3 build-pptx.py ${DECK_NAME}
```

Produces `~/.claude/slides/${DECK_NAME}.pptx` (target: under 1MB).

### Step 5: Upload and convert to Google Slides

Use this Python one-liner (avoids the base64 size limit in MCP tool parameters):

```bash
python3 /tmp/upload_to_drive.py ${DECK_NAME} ${FOLDER_ID}
```

Write `/tmp/upload_to_drive.py` with this content:

```python
import json, subprocess, tempfile, os, base64, sys

deck_name = sys.argv[1]
folder_id = sys.argv[2] if len(sys.argv) > 2 else 'YOUR_DRIVE_FOLDER_ID'
pptx_path = os.path.expanduser(f'~/.claude/slides/{deck_name}.pptx')

with open(pptx_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

req = {
  'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
  'params': {
    'name': 'upload_google_drive_file',
    'arguments': {
      'folder_id': folder_id,
      'file_name': f'{deck_name}.pptx',
      'file_content_base64': b64,
      'mime_type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'convert': True
    }
  }
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(req, f)
    fname = f.name

result = subprocess.run(
    ['sc-curl', '--fail-with-body',
     '-H', 'Content-Type: application/json',
     '-H', 'Accept: application/json',
     '-H', 'X-Requested-With: curl',
     '-d', f'@{fname}',
     'http://YOUR_MCP_ENDPOINT/mcp'],  # replace with your MCP server URL
    capture_output=True, text=True, timeout=60
)
os.unlink(fname)
resp = json.loads(result.stdout)
print(json.loads(resp['result']['content'][0]['text'])['file_link'])
```

The script prints the Google Slides URL on success.

### Step 6: Share

### Step 6: Share

For each email in `--share`, call `share_google_drive_doc`:
- `doc_id`: `file_id` from Step 5
- `action`: `add`
- `email`: the full email address
- `role`: `reader`
- `send_notification`: `false`

**Limitation**: the share tool does user-level shares only. For "anyone with link" access, open the file in Drive → Share → Change to "Anyone with the link can view".

### Step 7: Report back

Return:
- The Google Slides URL (`file_link` from Step 5)
- Who it was shared with
- Deck name and slide count

## Notes on output quality

- Slides are flat images — no editable text, no animations in the PPTX
- Fonts render exactly as in the browser (Proxima Nova, colors, gradients)
- If an animation class is missing from the screenshot script's force-visible list, elements may be invisible — check the deck before sharing

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `upload_google_drive_file` fails | Check your MCP server OAuth config |
| Blank slides in output | Run step 2 manually and inspect the PNGs first |
| Share fails | Check email address is correct and has a Drive account |
| Wrong slide count | Deck may use a CSS class other than `.slide` — update line 17 of `screenshot-slides.js` |
| PPTX too large for upload | Compress: `for f in screenshots/${DECK_NAME}/*.png; do sips -Z 1280 "$f" --out "$f" -s format jpeg -s formatOptions 85; done` |
