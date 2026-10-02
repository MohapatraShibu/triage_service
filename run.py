import json
import os
import time
from groq import Groq
from dotenv import load_dotenv
from triage import triage_message

# load all config
load_dotenv()

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise EnvironmentError("GROQ_API_KEY is not set")

model_name = os.environ.get("GROQ_MODEL")
input_file = os.environ.get("INPUT_FILE", "messages.json")
output_file = os.environ.get("OUTPUT_FILE", "results.json")
delay_between = float(os.environ.get("DELAY_BETWEEN_CALLS", "2"))

# config passed into triage logic - all values come from .env
config = {
    "confidence_threshold": float(os.environ.get("CONFIDENCE_THRESHOLD")),
    "max_retries": int(os.environ.get("MAX_RETRIES")),
    "retry_wait": int(os.environ.get("RETRY_WAIT_SECONDS")),
}

client = Groq(api_key=api_key)

# load input messages
if not os.path.exists(input_file):
    raise FileNotFoundError(f"{input_file} not found")

with open(input_file, "r", encoding="utf-8") as f:
    messages = json.load(f)

if not isinstance(messages, list):
    raise ValueError(f"{input_file} must contain a json array at the top level.")

results = []
for i, message in enumerate(messages):
    msg_id = message.get("id", f"index-{i}") if isinstance(message, dict) else f"index-{i}"
    print(f"processing {msg_id} ({i + 1}/{len(messages)})...")

    result = triage_message(message, client, model_name, config)
    results.append(result)

    # small delay between calls
    time.sleep(delay_between)

# summary counts for quick review
total = len(results)
needs_human = sum(1 for r in results if r["human_review"])
urgent = sum(1 for r in results if r["route_to"] == "urgent_human")
automated = sum(1 for r in results if r["route_to"] == "automation")

output = {
    "summary": {
        "total_messages": total,
        "automated": automated,
        "needs_human_review": needs_human,
        "urgent": urgent,
    },
    "results": results,
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\ndone. results written to {output_file}")
print(f"  total: {total} | automated: {automated} | human review: {needs_human} | urgent: {urgent}")
