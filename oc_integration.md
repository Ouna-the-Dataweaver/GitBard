OpenCode can emit raw JSON events with --format json.
Those events include text parts you can safely concatenate into the final answer.

Bash + tiny Python extractor
```
cd "$REPO_DIR"

opencode run \
  --format json \
  --model "provider/model" \
  --agent "review" \
  "Answer this GitLab thread question:\n\n$QUESTION" \
  | tee opencode_events.jsonl \
  | python3 - <<'PY'
import sys, json
chunks = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    evt = json.loads(line)
    if evt.get("type") == "text":
        chunks.append(evt["part"]["text"])
print("".join(chunks).strip())
PY \
  > opencode_reply.md
```

Model to use: minimax/MiniMax-M2.1
Agent: Build

Now you get:

opencode_reply.md = final answer only

opencode_events.jsonl = full trace (useful for debugging)

If you want to detect completion / capture a session id, step_finish events include sessionID and a stop reason.