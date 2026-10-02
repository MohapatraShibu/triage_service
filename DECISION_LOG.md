# Decision Log

## What I noticed in the data

Before writing any code I read all 25 messages. Several shaped the design directly:

**MSG-005 is a prompt injection attack.** A message arriving in a customer channel that says "ignore all previous instructions" and demands a refund approval is not a confused customer. It is an adversarial input. The system needed to detect and flag this without acting on it.

**MSG-006 is code-switched Hindi and English.** Real customer messages are not clean English. The model handles this without any special treatment, which is the right outcome.

**MSG-012 has no context.** "What about the other one" cannot be resolved without conversation history. The system correctly flags it as ambiguous rather than guessing.

**MSG-008 and MSG-014 have multiple intents.** One message can contain a refund request and a new order simultaneously. The output captures all intents but the `action` field is singular, which is a known limitation noted below.

**MSG-016 is a live emergency.** A passenger stranded at Pearson with a cancelled connection and an elderly traveller is not a support ticket. It needs a human on the phone within minutes, not a queue. This drove the `urgent_human` routing value and the `live_emergency` flag.

**MSG-019 is a medical liability risk.** Asking whether ashwagandha interacts with blood pressure medication is a drug interaction question. Automating a response, even a cautious one, creates liability. The notes field is suppressed entirely on `medical_advice` results so no partial guidance reaches non-clinical staff.

**MSG-021 looks like a vendor phishing attempt.** An invoice with bank details arriving in a customer support channel is not a customer message. It is either misdirected or malicious. Flagged as `suspicious` and routed to a human.

**MSG-025 has a null body.** The input file is not clean. The service handles null, empty, and missing text fields without crashing.

---

## What I chose not to build, and why

**No database or queue.** The brief asks for a service that processes a file. Adding Postgres or a message queue would be correct for production but wrong here, it would obscure the logic without adding signal.

**No frontend UI.** Nothing in the brief asks for one. A clean JSON output file is the deliverable.

**No async batching.** At 25 messages a 2-second delay between calls is sufficient. At 10,000 messages/day I would replace the sleep with async workers and a concurrency semaphore, straightforward to add but left out here because it would make the code harder to walk through without changing the output.

**No fine-tuning or embeddings.** The message set is small and spans multiple brands and intents. A well-written prompt on a capable general model outperforms a custom classifier here and is far easier to update when intent categories change.

**Groq over other providers.** Gemini's free tier allows only 5 requests/minute, which causes rate limit failures mid-run on a 25-message file. Groq's free tier allows 30 requests/minute and 14,400 requests/day. `openai/gpt-oss-20b` on Groq follows structured JSON instructions reliably and is the latest available model on the platform.

**All tuning values are configurable via `.env`.** Confidence threshold, retry count, retry wait, delay between calls, input and output file paths, none are hardcoded. They can be changed without touching the code.

**`temperature` is hardcoded to 0.** This is intentional. A triage classifier needs deterministic output, the same message should always produce the same routing decision. It is not a tunable parameter.

---

## Where this breaks, in my own assessment

**Context-less follow-ups (MSG-012).** Without conversation history the model cannot resolve the reference. It correctly flags this as ambiguous and routes to a human, but that human still has to find the prior thread manually. A thread ID on each message would fix this.

**Multi-intent messages (MSG-008, MSG-014).** The model captures all intents correctly, but the `action` field is singular. A downstream system acting on one action would silently drop the second request. In production this needs a multi-action output shape.

**Prompt injection (MSG-005).** The model detects and flags this correctly. But a sufficiently sophisticated injection could still manipulate the output. The defence is the JSON schema validation added in this version, any response that does not match the expected shape is rejected entirely and falls back to human review.

**Rate limits at scale.** The free tier allows 14,400 requests/day and 30 requests/minute. At 10,000 messages/day the daily volume is covered, but sequential processing with a 2-second sleep would take nearly 14 hours. The fix is async batching with a concurrency semaphore.

**Malformed LLM output.** If the model returns unparseable JSON, the message falls back to `human_review: true` with a `parse_error` flag. This is safe but the human sees no triage information. Schema validation now catches structural problems before they silently corrupt results.

---

## What I would do with another day

- Replace the sleep-based rate limiting with async batching using `asyncio` and a semaphore, reducing 10,000 messages from hours to minutes
- Add a conversation thread ID field so follow-up messages like MSG-012 can be linked to their parent
- Build a small eval set: 10 messages with known correct outputs, run automatically after any prompt change to catch regressions
- Add a multi-action output shape to handle messages like MSG-008 where two separate actions are needed

---

## AI tools used and for what

**Claude based IDE assistant:** used throughout to scaffold the project, draft the README and cross-check the output schema against the actual message data. All prompt design, routing logic, flag definitions, data observations, and decisions in this log are my own. Assistant was used as a fast pair programmer, not as a decision-maker.
