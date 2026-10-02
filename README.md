# Message Triage Service

Reads customer messages from `messages.json` and uses an LLM (Groq) to classify each one: what the customer wants, what information can be extracted, what should happen next, and whether a human needs to review it.

---

## Requirements

- Python 3.9 or higher
- A Groq API key (instructions below)

---

## Step 1 - Get a Groq API key

1. Go to [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign in or create a account
3. Click **Create API key**
4. Copy the key - you will need it in **Step 3**

---

## Step 2 - Create and activate a virtual environment

Open a terminal in the project folder and run:

**On Mac / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

---

## Step 3 - Set your API key

Copy the example env file:

**On Mac / Linux:**
```bash
cp .env.example .env
```

**On Windows (Command Prompt):**
```cmd
copy .env.example .env
```

**On Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

Then open `.env` and fill in your Groq API key:

```
GROQ_API_KEY=paste_your_key_here
GROQ_MODEL=openai/gpt-oss-20b (or you can choose any similiar model)

# files
INPUT_FILE=messages.json
OUTPUT_FILE=results.json

# tuning
CONFIDENCE_THRESHOLD=0.75
MAX_RETRIES=3
RETRY_WAIT_SECONDS=30
DELAY_BETWEEN_CALLS=2
```

Only `GROQ_API_KEY` is required. All other values have sensible defaults and can be left as-is.

> `.env` is listed in `.gitignore` and will never be committed. `.env.example` is safe to commit - it contains no real keys.

---

## Step 4 - Run the service

Make sure your virtual environment is still active (you should see `(venv)` in your terminal prompt). Then run:

```bash
python run.py
```

The script will process each message one by one and print progress to the terminal. All 25 messages complete in under 2 minutes.

---

## Output

Results are written to `results.json` in the same folder.

The file contains:

- a `summary` block with counts (total, automated, needs human review, urgent)
- a `results` array with one object per message

### Example result object

```json
{
  "id": "MSG-001",
  "brand": "vitalis-wellness",
  "channel": "whatsapp",
  "received_at": "2026-09-28T09:14:00+05:30",
  "original_text": "Hi, ordered the magnesium capsules...",
  "intents": ["order_tracking"],
  "entities": {
    "order_id": "VW-48812",
    "product": "magnesium capsules"
  },
  "action": "query_shipping_api",
  "route_to": "automation",
  "confidence": 0.95,
  "flags": [],
  "notes": "Tracking has not updated in 4 days",
  "human_review": false
}
```

---

## Human review rule

A message is flagged for human review if **any** of the following are true:

| Condition | Reason |
|---|---|
| `confidence < 0.75` | LLM was not sure about intent or action |
| `route_to` is `human_agent` or `urgent_human` | Needs a person regardless of confidence |
| flags include `prompt_injection` | Possible adversarial input |
| flags include `medical_advice` | Cannot automate health guidance |
| flags include `live_emergency` | Immediate human response required |
| flags include `ambiguous` | Not enough context to act safely |
| flags include `suspicious` | Unusual or potentially fraudulent message |
| flags include `parse_error` | LLM response could not be parsed |

`route_to: ignore` always sets `human_review: false` - no actionable content means no human needed.

`flags: medical_advice` always clears the `notes` field - no partial health guidance is passed to non-clinical staff.

---

## Routing values

| `route_to` value | Meaning |
|---|---|
| `automation` | Safe to handle without a human |
| `human_agent` | Needs a person but not urgent |
| `urgent_human` | Needs immediate human attention |
| `ignore` | No actionable content (e.g. empty message) |

---

## Cost at scale (10,000 messages/day)

Using **Groq - openai/gpt-oss-20b**:

- Free tier: 14,400 requests/day, 30 requests/minute at zero cost
- Paid tier pricing: **$0.59 per 1 million input tokens**, **$0.79 per 1 million output tokens**

**Assumptions:**
- Average input per message (system prompt + message text): ~450 tokens
- Average output per message (JSON result): ~150 tokens
- 10,000 messages/day

**Calculation:**
- Input: 10,000 × 450 = 4,500,000 tokens → $0.59 × 4.5 = **$2.66**
- Output: 10,000 × 150 = 1,500,000 tokens → $0.79 × 1.5 = **$1.19**
- **Total: ~$3.85/day → ~$0.39 per 1,000 messages**

> The free tier covers 14,400 requests/day at zero cost - enough for the current volume with headroom. Paid tier pricing applies beyond that.

---

## Project structure

```
triage_service/
├── messages.json         input messages
├── run.py                entry point, reads input and writes output
├── triage.py             core logic, prompt building, llm call, parsing
├── requirements.txt      python dependencies
├── .env                  your api key (never committed)
├── .env.example          safe template to copy from
├── .gitignore            excludes venv, .env, results.json
├── README.md             this file
└── DECISION_LOG.md       design decisions and tradeoffs
```
