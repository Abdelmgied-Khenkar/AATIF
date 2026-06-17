# AATIF — Project Map (Operational Brief)

## Last Updated
2026-04-14 (Safe-Path Hooks documented + Runtime Secrets Policy locked)

## Root
/Users/aatifsandbox/AATIF

---

## Architecture Overview

AATIF is a unified system composed of 4 main layers:

1. Governance Layer
2. Canonical Layer
3. Runtime Layer
4. Channel Layer

---

## Directory Structure

/Users/aatifsandbox/AATIF
├── 00_governance/aatif-os
├── 01_canonical/aatif-ollama
├── 10_runtime/aatif-sales-engine
├── 20_channels/aatif-lab
└── 90_snapshots/aatif_snapshots

---

## Layer Definitions

### 1) Governance (00_governance)
Path:
- /Users/aatifsandbox/AATIF/00_governance/aatif-os

Role:
- system rules
- identity authority
- architectural constraints
- governance truth

### 2) Canonical (01_canonical)
Path:
- /Users/aatifsandbox/AATIF/01_canonical/aatif-ollama

Role:
- AMI / CP-01
- core system meaning
- canonical definitions
- reference truth

### 3) Runtime (10_runtime)
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine

This is the live decision system.

Main files:
- api_server.py
- llm_bridge.py
- whatsapp_listener.py
- whatsapp_sender.py
- reply_base_mapper.py
- auto_send_response.py
- owner_command_layer.py
- intent_engine.py

### 4) Channels (20_channels)
Path:
- /Users/aatifsandbox/AATIF/20_channels/aatif-lab

Role:
- OpenClaw
- WhatsApp integration
- gateway / transport only

---

## Live System Identity

Primary entity:
- AI STUDIO PRO

Governance layer:
- AATIF

Human-facing expression:
- عاطف

Important rule:
- AI STUDIO PRO remains the primary entity
- AATIF is the governance / engineering layer
- عاطف is an expression layer, not the primary entity

---

## Current End-to-End Runtime Flow

WhatsApp
↓
OpenClaw
↓
whatsapp_listener.py
↓
reply_base_mapper.py
↓
api_server.py
↓
intent_engine.py
↓
auto_send_response.py
↓
llm_bridge.py
↓
provider
↓
whatsapp_sender.py
↓
OpenClaw
↓
WhatsApp

---

## Core Architectural Result

The system now works on:

meaning first
↓
intent result
↓
semantic reply
↓
behavior overlay
↓
governed model pass
↓
final reply

Main principle implemented:

"المعنى قبل النص"

AATIF now governs reply logic instead of allowing protocol shortcuts or model drift to overwrite meaning.

---

## Intent Engine Status (FINAL)

intent_engine.py is now the single source of meaning.

Confirmed live behavior:
- intent_result is built in api_server.py
- reply_base_mapper.py consumes intent-derived meaning
- auto_send_response.py uses intent_result instead of shadow semantic interpretation
- llm_bridge.py receives intent context inside prompt
- provider is now downstream from governed intent, not upstream of meaning

Confirmed prompt context now includes:
- surface_intent
- hidden_intent
- why_now_signal
- wrong_answer_risk

Architectural meaning:
- intent_engine.py = mind
- reply_base_mapper.py = tongue
- auto_send_response.py = behavior layer
- llm_bridge.py = model layer
- provider = subordinate execution layer

---

## Runtime Truth (Current File Roles)

### 1) intent_engine.py
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/intent_engine.py

Role:
- single source of intent / meaning
- central intent classification
- builds intent result object
- upstream mental layer

Current runtime responsibility:
- surface intent
- hidden intent
- why-now signal
- wrong-answer risk

Important note:
- this is now the only valid mind layer
- no other file should become a second intent brain

---

### 2) reply_base_mapper.py
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/reply_base_mapper.py

Role:
- semantic reply engine
- builds base governed reply from meaning
- business-aware rendering
- linguistic expression layer

Important functions:
- normalize_text
- detect_user_knowledge_level
- build_greeting
- build_semantic_plan
- render_identity_reply
- render_pricing_reply
- render_details_reply
- render_objection_reply
- resolve_business_case_hint
- adjust_reply_by_hidden_intent
- render_reply
- build_base_reply

Current truth:
- no longer acts as an independent mind
- now acts as guided semantic rendering

---

### 3) auto_send_response.py
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/auto_send_response.py

Role:
- behavior / protocol overlay layer
- follow-up shaping
- state-aware behavior adaptation
- learning trace support

Important functions:
- resolve_sales_protocol_intent
- adapt_protocol_if_repeated
- map_intent_to_protocol
- apply_protocol_overlay
- apply_einl_sales_mode
- apply_state_modifier

Current truth:
- cleaned from shadow semantic engine behavior
- no longer acts as a second mind
- now behaves as a sales / behavior layer only

Important note:
- pressure / comparison / investor overlays remain here
- central meaning must still come from intent_engine.py

---

### 4) llm_bridge.py
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/llm_bridge.py

Role:
- provider bridge
- prompt builder
- model normalization
- strong-base preservation

Important functions:
- _normalize_final_text
- _preserve_strong_base
- build_prompt
- call_local
- call_gemini
- call_openai
- call_ollama
- get_active_provider
- generate_final_reply

Current truth:
- now receives intent_result context
- provider no longer works on raw text alone
- prompt is governed by intent context

Important note:
- model is subordinate to governed base meaning
- strong base preservation remains active

---

### 5) api_server.py
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/api_server.py

Role:
- central runtime entry for compose-response
- builds intent_result
- passes intent_result through EINL and LLM bridge
- sends final response payload

Important route:
- POST /compose-response

Current truth:
- builds intent_result once
- passes same intent_result to:
  - apply_einl_sales_mode()
  - generate_final_reply()

This is the current unification point.

---

### 6) whatsapp_listener.py
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/whatsapp_listener.py

Role:
- live incoming HTTP entrypoint
- receives WhatsApp-side inbound payloads
- resolves relationship key
- reads debug context
- builds base reply
- calls API server
- optionally sends message
- supports TEST_NO_SEND mode

Important variables:
- AATIF_API_URL = http://localhost:8000/compose-response

Current truth:
- transport-facing runtime bridge
- should not become a logic brain

---

### 7) whatsapp_sender.py
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/whatsapp_sender.py

Role:
- outbound sender
- OpenClaw CLI based sending
- final dispatch layer

Current truth:
- transport only
- no reply intelligence should live here

---

### 8) owner_command_layer.py
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/owner_command_layer.py

Role:
- owner/admin command handling
- debug context updates
- business_type debug control

Important functions:
- parse_owner_command
- load_debug_context
- write_debug_context
- set_debug_business_type
- clear_debug_business_type
- handle_owner_command

Current owner number:
- [REDACTED]

---

## Important Data / State Files

### aatif_debug_context.json
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/aatif_debug_context.json

Role:
- stores current debug business_type

Example:
{
  "business_type": "consulting"
}

### reply_access_memory.csv
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/reply_access_memory.csv

Role:
- reply status memory
- KNOWN / VIP / LEAD / INTERNAL / UNKNOWN / BLOCKED

### aatif_runtime.log
Path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/aatif_runtime.log

Role:
- main runtime log
- confirms incoming requests, base reply, send behavior, debug context

---

## Server / Port Map

Runtime root:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine

AATIF API server:
- api_server.py
- port 8000

WhatsApp listener:
- whatsapp_listener.py
- port 5051

Current live relationship:
- whatsapp_listener.py -> api_server.py
- api_server.py -> intent_engine.py
- api_server.py -> auto_send_response.py
- api_server.py -> llm_bridge.py
- llm_bridge.py -> provider
- reply_base_mapper.py builds base reply before governed model pass

---

## Provider Status

Current intended provider:
- LLM_PROVIDER=ollama
- OLLAMA_BASE_URL=http://127.0.0.1:11434
- OLLAMA_MODEL=qwen2.5:7b

Supported paths in llm_bridge.py:
- local
- gemini
- openai
- ollama

Current operational truth:
- Ollama is the active governed provider direction
- local fallback remains valid
- Gemini remains optional later
- provider must never become the source of meaning

---

## Phone / Channel Map

Server / WhatsApp line:
- [REDACTED]

Owner:
- [REDACTED]

Repeated test client:
- [REDACTED]

Additional discussed client context:
- [REDACTED]

Important rule:
- owner must remain separate from server line

---

## OpenClaw Status

Outbound:
- confirmed working

Inbound:
- not yet fully wired into Flask /incoming path

Observed before:
- outbound messages sent
- WhatsApp linked
- inbound routing remained incomplete in some tests

Conclusion:
- transport wiring still separate from semantic success
- semantic system itself is working
- remaining issue is channel routing, not meaning logic

---

## Current Policy

System behavior:
- receive from any number at transport level
- do not auto-reply to everyone
- reply selectively inside runtime

Important rule:
- access layer != decision layer

Meaning:
- OpenClaw = transport
- AATIF = meaning / decision / governance
- provider = language generation only

---

## Important Fixes Already Completed

### FIX 1
business_type existed but was weakly connected

Result:
- business-aware hints now affect reply output

### FIX 2
EINL used to crush strong semantic replies

Result:
- strong base preservation introduced
- behavior layer no longer blindly overwrites real meaning

### FIX 3
provider rewrites weakened strong replies

Result:
- llm_bridge strong-base preservation added
- governed base survives weak candidate output

### FIX 4
local testing could trigger real sends

Result:
- TEST_NO_SEND mode added

### FIX 5
shadow semantic duplication existed in sales engine

Result:
- auto_send_response.py cleaned
- resolve_sales_protocol_intent now acts as behavior resolver, not a second mind

### FIX 6
intent context was not reaching model layer

Result:
- llm_bridge prompt now includes intent context
- provider is downstream from governed meaning

---

## Anti-Duplication Status

Current anti-duplication coverage now exists in two places:

### 1) Inbound anti-duplication
File:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/whatsapp_listener.py

Related file:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/inbound_dedupe_memory.csv

Current behavior:
- blocks exact duplicate inbound messages
- same phone + same normalized message
- within 90 seconds
- duplicate is ignored before semantic processing and before send path

Current fields used:
- phone
- normalized_message
- timestamp
- relationship_key
- raw_message

Important rule:
- current inbound dedupe is exact / literal, not semantic
- it must not guess meaning
- it must not block negation-sensitive changes such as:
  - ابي التفاصيل
  - ما ابي التفاصيل

### Smart inbound dedupe refinement

Current status:
- exact duplicate block is active
- safe near-duplicate block is active
- negation-sensitive reversal is protected

Current behavior examples:
- "انا ابغي اعرف التفاصيل" == "انا ابغى اعرف التفاصيل" -> block
- "انا ابغي اعرف التفاصيل" != "انا ما ابغي اعرف التفاصيل" -> allow
- "I want details" != "I do not want details" -> allow

Important rule:
- smart dedupe must remain safe
- it may normalize light Arabic spelling variation
- it must not collapse negation or meaning reversal into one message

Implementation note:
- smart inbound dedupe currently lives in:
  - /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/whatsapp_listener.py
- inbound memory file:
  - /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/inbound_dedupe_memory.csv

### 2) Outbound anti-duplication
File:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/auto_send_response.py

Related guard:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/anti_duplicate_guard.py

Current behavior:
- blocks duplicate or near-duplicate outbound sends
- works at behavior / dispatch layer

Operational note:
- inbound dedupe protects the entrypoint
- outbound dedupe protects the send path
- current architecture now has duplicate protection on both sides

Future note:
- if smart dedupe is added later, it must remain safe around negation and meaning reversal
- do not let smart dedupe block messages whose wording changes the meaning

---

## Current Capability

System now:
- receives from anyone at transport level
- filters reply internally
- supports owner commands
- supports debug business_type injection
- builds governed semantic replies
- preserves strong replies through behavior and model layers
- passes intent_result end-to-end
- keeps provider subordinate to meaning

---

## Current Tested Runtime Truth

Confirmed test pattern:
- value questions remain value-shaped
- resistance questions remain resistance-shaped
- pricing meaning is preserved
- pressure framing works
- difference framing works
- investor framing works
- thanks / no-sales-intent remains neutral

Confirmed final direction:
- no shadow mind remains in sales layer
- no raw-text-only model pass remains in LLM bridge
- base meaning can survive full runtime path

---

## Definition of Reply in AATIF

Reply != text generation

Reply =

Should reply?
↓
To whom?
↓
Why?
↓
With what intent?
↓
With what tone?
↓
With what behavioral frame?
↓
Then generate message

---

## Current Mode

Receive: OPEN
Reply: CONTROLLED
Meaning: GOVERNED
Behavior: GOVERNED
Model: SUBORDINATE

---

## Operational Focus / Do Not Drift

Current decision:
- do not modify architecture now

Current operational priorities:
1. OpenClaw inbound wiring
2. anti-duplication
3. expression layer later

Important caution:
- the system is now clean and role-separated
- shadow mind is removed from the sales layer
- reply_base_mapper.py must not slowly turn back into a second mind
- any real meaning logic must remain inside intent_engine.py

Architect memory line:

Conceptual truth:
mind -> behavior -> tongue -> model

Current runtime order:
mind -> tongue -> behavior -> model

Interpretation:
- intent_engine.py = mind
- auto_send_response.py = behavior
- reply_base_mapper.py = tongue
- llm_bridge.py = model

Important note:
- conceptual order is the target architectural truth
- current runtime order is an implementation detail, not the final ideal
- if expression grows later, keep it as expression only
- do not let expression become intent classification
- do not let behavior become a second intent engine
- do not let transport become logic
- do not let model become source of meaning

---

## Notes for Future Agents

- do not create a second intent engine
- do not put central meaning logic inside auto_send_response.py
- do not let llm_bridge.py become a semantic decision layer
- do not move logic into transport files
- if changing behavior, preserve:
  - intent_engine.py as single source of meaning
  - reply_base_mapper.py as expression layer
  - auto_send_response.py as behavior layer
  - llm_bridge.py as model layer

Golden rule:
mind first, then tongue, then behavior, then model

---

## One-Line Memory Anchor

AATIF now runs as a governed pipeline:
intent_engine.py builds the mind,
reply_base_mapper.py expresses the meaning,
auto_send_response.py shapes behavior without becoming a second mind,
llm_bridge.py passes governed intent to the provider,
and the model remains subordinate to AATIF.

---

## Execution Control Layer (Runtime Authority Map)

This section defines strict execution authority inside runtime.

### Authority Distribution

1) intent_engine.py
- ONLY source of meaning
- builds intent_result
- decides:
  - should reply
  - intent type
  - user classification
  - business logic direction

STRICT RULE:
- no other file may generate or modify intent_result

---

2) reply_base_mapper.py
- expression layer ONLY
- converts intent → structured reply base

STRICT RULE:
- must NOT:
  - classify intent
  - generate meaning
  - override intent_engine output

---

3) auto_send_response.py
- behavior orchestration layer
- handles:
  - pacing
  - follow-ups
  - anti-duplication
  - message timing

STRICT RULE:
- must NOT:
  - re-interpret intent
  - generate new meaning logic
  - become second decision engine

---

4) llm_bridge.py
- model communication layer ONLY

STRICT RULE:
- must NOT:
  - decide reply
  - modify intent
  - inject business logic
  - override structured prompt

model = executor, not thinker

---

5) Transport Layer (whatsapp_listener / sender)
- input/output only

STRICT RULE:
- must remain logic-free

---

## Hard System Laws

- Single Mind Law:
  intent_engine.py is the ONLY mind

- No Shadow Mind Law:
  no secondary decision logic allowed anywhere

- Layer Isolation Law:
  meaning / expression / behavior / model must remain separated

- Model Subordination Law:
  model never defines meaning

---

## Failure Conditions

If any file:
- classifies intent outside intent_engine.py
- adds business logic outside intent_engine.py
- overrides intent_result

→ system is considered CORRUPTED

---

## Enforcement Anchor

mind → tongue → behavior → model

This order is NOT allowed to change.


---

## Behavior Native Mind Guard

Date locked:
2026-04-05

Current architectural decision:

- behavior-first is conceptually correct
- but behavior must NOT be promoted into intent_engine.py using shallow lexical triggers only

Important rule:
- if behavior classification depends only on keyword matching,
  then it is NOT true mind logic
- it must remain outside the core mind until semantic-grade detection exists

Current allowed state:
- behavior-first fallback may exist in expression/runtime path
- but intent_engine.py must not be polluted with fake semantic upgrades based only on trigger words

Meaning:
- do not move:
  - pressure_test
  - difference_probe
  - investor_frame
into the mind layer unless detection is based on real meaning signals, not shallow keyword activation

Architectural warning:
- moving lexical triggers into the mind creates a false mind
- a false mind is more dangerous than an honest fallback

Temporary truth:
- behavior-first runtime path is acceptable
- fake semantic mind is not acceptable


---

## Signal Layer / Fingerprint Layer Direction

Date locked:
2026-04-05

Current architectural direction:

intent must not be derived from shallow keyword triggers only.

Target formula:

intent = derive_from_features(text, context, state)

Meaning:
- text alone is not enough
- context alone is not enough
- state alone is not enough
- intent must be derived from the combined signal structure

### Accepted signal sources

1) text features
- question shape
- negation
- comparison framing
- pressure/challenge tone
- pricing framing
- objection structure
- clarity request
- trust-check pattern

2) context features
- what came before
- what the current message is replying to
- repeated objection vs first objection
- timing after explanation / quote / silence
- whether the message is standalone or follow-up

3) state features
- person state
- company state
- relationship stage
- fallback position
- business context

4) pattern fingerprint
- repeated behavioral pattern across messages
- short challenge vs real comparison vs hidden resistance
- reversal patterns
- disguised price resistance
- disguised trust probe

### Hard rule

- keyword triggers may help extraction
- but keyword triggers alone must NOT be treated as true meaning

### Architectural warning

A lexical trigger moved into the mind layer without semantic-grade feature structure creates a false mind.

### Temporary truth

- behavior-first runtime fallback is acceptable
- fake semantic mind is not acceptable
- true mind upgrade requires:
  - signal extraction
  - fingerprint construction
  - intent derivation from combined features


---

## Signal Layer v1 / Negation Reversal Progress

Date locked:
2026-04-05

Current confirmed upgrade:
AATIF moved from shallow trigger-style hidden behavior handling toward signal-based hidden intent derivation.

### Confirmed architectural shift

Previous weak pattern:
text -> keyword -> intent

Current improved pattern:
text -> signals -> hidden_intent -> why_now / risk / outcome / trust -> reply

This is still Text-Signal Layer v1 only.
It is not yet full context-chain reasoning and not yet fingerprint-complete.

### What was added

1) Signal Layer v1 in intent_engine.py
- SignalFeatures introduced
- extract_signal_features(text) introduced
- hidden intent no longer depends only on direct shallow trigger mapping
- hidden intent now derives from grouped signal structure

2) Native hidden-intent upgrades confirmed
The following now classify correctly inside the mind layer:
- اثبتها -> pressure_probe
- وش الفرق -> difference_probe
- مستثمر -> investor_probe
- هل يسوي -> value_test
- غالي -> price_resistance

3) Negation / reversal logic started
A true meaning flip was introduced for details intent.

Confirmed distinction:
- "أبغى التفاصيل" -> clarity_probe
- "ما أبغى التفاصيل" -> clarity_rejection
- "أنا ما أبغى التفاصيل" -> clarity_rejection
- "ما ابي تفاصيل" -> clarity_rejection

This is not treated as simple negation text.
It is treated as a semantic boundary signal.

### clarity_rejection wiring status

clarity_rejection is now connected across the mental chain:

- hidden_intent = clarity_rejection
- why_now_signal = boundary_signal
- wrong_answer_risk = overselling_after_boundary
- outcome_mode = respect_boundary
- trust_mode = calm_respectful

### Tongue-layer integration confirmed

reply_base_mapper.py now respects clarity_rejection.

Confirmed reply behavior:
- details request -> explain
- details rejection -> respect boundary and do not over-explain

Example confirmed behavior:
- "أبغى التفاصيل"
  -> explanatory response

- "ما أبغى التفاصيل"
  -> "واضح، ما عندك رغبة تدخل في التفاصيل الحين. نخليها بشكل مختصر جدًا، وإذا حبيت ترجع لها لاحقًا أشرحها لك."

### Architectural meaning of this step

This upgrade proves an important principle:

Meaning can flip without changing the surface topic.

Example:
- surface_intent remains: details
- hidden_intent changes from: clarity_probe
- to: clarity_rejection

This confirms that AATIF must separate:
- topic surface
- hidden meaning
- decision boundary
- response posture

### Current truth after this phase

AATIF now supports:
- signal-derived hidden intent
- partial behavior-native mind logic
- first working negation/reversal behavior
- first boundary-respecting reply logic

### What is still NOT complete

This is not full semantic mind yet.

Still missing later:
- context-linked intent derivation
- cross-message fingerprinting
- sender-pattern memory integration into intent derivation
- company-state / person-state influence inside derive_from_features(...)
- value_rejection
- pricing_rejection
- richer reversal families beyond details

### Locked architectural rule

Do NOT regress back to:
keyword -> intent

Do NOT promote fake semantic behavior into the mind using shallow lexical triggers only.

Signal composition is acceptable.
False mind shortcuts are not acceptable.

### Current formula to preserve

intent = derive_from_features(text, context, state)

Current implemented subset:
intent = derive_from_features(text_signals)

Future target:
intent = derive_from_features(text_signals, context_chain, state, fingerprint)


---

## Boundary vs Not-Now Meaning Phase

Date locked:
2026-04-05

Current confirmed upgrade:
AATIF now distinguishes between:
- hard boundary
- temporal boundary ("not now")

This distinction is no longer treated as surface text only.
It now affects reply posture through the intent chain.

### Confirmed meaning rule

Same hidden rejection family can produce different response posture depending on why_now_signal.

Formula now confirmed:

hidden_intent + why_now_signal -> reply posture

### Confirmed rejection families working

1) clarity_rejection
2) price_rejection
3) value_rejection

### Confirmed why_now split

A) boundary_signal
Meaning:
- user is setting a limit
- do not pressure
- do not reopen the same topic immediately

Reply posture:
- respect boundary
- move forward without pressure

B) timing_pressure
Meaning:
- user is not refusing permanently
- user is declining now / postponing now
- leave the door open later

Reply posture:
- respect current boundary
- keep return path open later
- do not push now

### Confirmed tongue-layer behavior

1) pricing
- boundary_signal:
  "واضح إنك ما تبغى تدخل في السعر. تمام، نخليه خارج النقاش ونمشي بدون ضغط على هالنقطة."

- timing_pressure:
  "واضح إنك ما تبغى تدخل في السعر الآن. تمام، نخليه خارج النقاش حاليًا، وإذا حبيت نرجع له لاحقًا ندخله بشكل مختصر وواضح."

2) details
- boundary_signal:
  "واضح، ما عندك رغبة تدخل في التفاصيل. تمام، نخليها خارج النقاش ونمشي بدون ضغط على هالنقطة."

- timing_pressure:
  "واضح، ما عندك رغبة تدخل في التفاصيل الآن. تمام، نخليها مختصرة جدًا حاليًا، وإذا حبيت ترجع لها لاحقًا أشرحها لك."

3) value
- boundary_signal:
  "واضح إنك ما تبغى تدخل في تقييم القيمة. تمام، نخليها خارج النقاش ونمشي بدون ضغط على هالنقطة."

- timing_pressure:
  "واضح إنك ما تبغى تدخل في تقييم القيمة الآن. تمام، نخليها خارج النقاش حاليًا، وإذا حبيت نرجع لها لاحقًا نرجع لها بشكل مختصر وواضح."

### Architectural meaning

This phase confirms that:
- rejection is not one thing
- "no" is different from "not now"
- surface topic may remain the same
- hidden intent family may remain the same
- but reply posture must shift according to temporal boundary meaning

### Important design truth

Do NOT multiply hidden intents unnecessarily when posture can be derived from:
- hidden_intent
- why_now_signal

This keeps the mind cleaner.

Preferred pattern:
- keep hidden intent family stable
- let timing / boundary signals shape the response posture

### Current status after this phase

AATIF now supports:
- signal-based hidden intent v1
- negation/reversal v1
- boundary-aware reply logic
- temporal-boundary-aware reply logic
- first posture split between:
  - respect boundary
  - respect boundary but leave door open later

### Still missing later

- context-chain reasoning
- message-to-message fingerprinting
- company-state influence on derive_from_features(...)
- person-state influence on derive_from_features(...)
- stronger English expression rendering
- richer non-sales boundary families
- cross-turn memory-based intent reinforcement


---

## Context Passthrough v1 + Context-Aware Mind/Tongue v1

Date locked:
2026-04-06

### 1) Context Passthrough v1
Confirmed runtime path now passes relationship context through the system:

whatsapp_listener.py
-> relationship_key
-> api_server.py
-> relationship_context_resolver.py
-> intent_engine.py
-> IntentResult
-> to_plan_dict()
-> reply_base_mapper.py

Confirmed current context source files:
- conversation_state.csv
- relationship_memory.csv
- contact_relationship_memory.csv

Confirmed current resolver output families:
- conversation_state / last_state / state_reason / last_route
- relationship_state / last_outcome / next_action / cooldown_days / do_not_contact
- response_status / sentiment_score / contact_fatigue / cooldown_until / interaction_count / ignore_count

Important truth:
- context is now visible to the mind and tongue
- but not all context fields are used yet

### 2) Context-Aware Mind v1 (limited)
Confirmed current mind-level context usage is limited and intentional.

Currently affected mind layers:
- detect_why_now_signal(...)
- resolve_trust_mode(...)

Current context-sensitive signals proven:
- relationship_state = not_now
- response_status = Ignored / ignored
- contact_fatigue = high

Current proven effects:
- same text can now produce different why_now_signal under different relationship context
- same text can now produce different trust_mode under different relationship context

Examples confirmed:
- details probe + relationship_state=not_now -> why_now shifts toward timing_pressure
- details probe + Ignored/high fatigue -> why_now can shift toward boundary_signal and trust toward calm_respectful
- price rejection + relationship_state=not_now -> why_now shifts toward timing_pressure

Important note:
- hidden_intent was intentionally not expanded yet
- context currently modifies interpretation posture, not topic classification

### 3) Context-Aware Tongue v1 (details-first)
Confirmed first tongue-level consumption of context-aware mind now exists in details flow.

Primary file:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/reply_base_mapper.py

Primary function upgraded:
- render_details_reply(plan)

Current rule:
- clarity_probe + why_now_signal=timing_pressure
  -> brief respectful defer-now explanation
- clarity_probe + trust_mode=calm_respectful
  -> minimal non-pushy explanation
- mechanism_probe/depth_probe + trust_mode=calm_respectful
  -> shortened safer explanation with future reopen path

Architectural meaning:
- mind can now reinterpret probe posture under relationship context
- tongue can now soften explanation intensity under that new posture
- this is the first real bridge from relationship context into response form

### 4) Current boundary of truth
What is confirmed now:
- context passthrough works
- mind uses context in limited posture logic
- tongue uses that limited posture logic in details flow

What is NOT yet confirmed:
- context-aware tongue for pricing flow beyond current rejection handling
- context-aware tongue for value flow beyond current rejection handling
- context-aware hidden_intent derivation
- context-aware outcome_mode derivation
- context-aware business_case_hint derivation
- cross-turn fingerprint interpretation

### 5) Safe next direction
If continuing later, preserve this order:
1. context-aware tongue for pricing/value probes
2. limited context-aware outcome_mode
3. only then consider limited hidden_intent influence

Do not skip directly to large semantic rewrites.

Golden rule:
context should modify interpretation posture first,
then reply form,
and only later deeper semantic classification if still needed.


---

## Context-Aware Tongue v2 (pricing/value probes)

Date locked:
2026-04-06

Current confirmed upgrade:
AATIF now extends context-aware tongue behavior beyond details flow into:
- pricing probes
- value probes

Primary file:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine/reply_base_mapper.py

Primary upgraded areas:
- render_pricing_reply(plan)
- render_reply(plan) value branch

### Confirmed current rule
If probe-type pricing/value requests arrive under softer relationship posture, the tongue no longer answers with the same full explanatory strength.

Current proven consumption signals:
- why_now_signal = timing_pressure
- trust_mode = calm_respectful

### Current pricing behavior
pricing/value-adjacent probe flow now softens when:
- relationship_state = not_now
- contact_fatigue = high
- response_status = Ignored / ignored
through the already-derived mind posture

Current tongue effect:
- not-now pricing/value probes -> defer-now / leave-door-open wording
- calm_respectful pricing/value probes -> minimal non-pushy wording
- normal engaged probes -> original stronger explanation remains allowed

### Architectural meaning
This phase extends the same proven bridge pattern:
relationship context
-> limited mind posture change
-> tongue softening
-> safer reply form

This was intentionally done without changing:
- surface_intent
- hidden_intent
- core semantic classification

### Confirmed system truth after this phase
AATIF now has context-aware tongue consumption in:
1. details flow
2. pricing probes
3. value probes

### Still not yet confirmed
- context-aware outcome_mode derivation
- context-aware hidden_intent derivation
- context-aware business_case_hint derivation
- cross-turn fingerprint interpretation
- company-state/person-state full derivation in mind logic

### Safe next order remains
1. limited context-aware outcome_mode
2. only then consider limited hidden_intent influence
3. fingerprint/cross-turn work later

Golden rule preserved:
context should first alter posture,
then reply form,
and only later deeper semantic classification.


---

## Correct Runtime Flow (Parallel Tracks Clarification)

Date locked:
2026-04-06

Previous simplified description:
- mind → tongue → behavior → model

This is conceptually useful but operationally inaccurate.

### Correct runtime structure

AATIF does NOT operate as a strict linear chain after the mind.

Actual structure:

mind (intent_engine.py)
→ produces intent_result

Then:

intent_result
→ tongue track (reply_base_mapper.py)
→ behavior track (auto_send_response.py)

These two tracks operate in parallel.

### Parallel Track Definition

1) Tongue Track (Expression Track)
- builds semantic base reply
- applies linguistic shaping
- expresses meaning

2) Behavior Track (Protocol Track)
- applies sales protocol overlays
- handles pacing / pressure / framing
- applies anti-duplication and send logic

### Merge Point

tongue output + behavior overlays
→ merged before model layer

Then:

merged governed base
→ llm_bridge.py (model execution)

### Final flow

mind
→ {tongue track + behavior track}
→ governed merge
→ model

---

## Response Expression Layer (Inside Tongue)

Date locked:
2026-04-06

Current issue discovered:
- reply_base_mapper mixes:
  - semantic meaning
  - expression style

This causes:
- static sentences
- system-like tone
- loss of natural variation

### Definition

Response Expression is NOT a new external layer.

It is an internal layer INSIDE the tongue.

### Structure inside reply_base_mapper

tongue =
    semantic_base (what to say)
    +
    response_expression (how it should sound)

### Responsibilities of Response Expression

- control tone (calm / direct / soft)
- control expansion (short / detailed)
- control pressure (no_push / light_open / guided)
- control posture rendering (boundary / timing / neutral)

### Important rule

Response Expression must:
- NOT classify intent
- NOT override intent_engine
- NOT introduce new meaning
- ONLY shape expression

### Architectural constraint

Response Expression is driven by:
- hidden_intent
- why_now_signal
- trust_mode

But it does NOT modify them.

### Example

Wrong:
pricing + calm_respectful → fixed sentence

Correct:
pricing + calm_respectful →
    expression_mode:
        light_answer
        no_push
        low_expansion

→ model generates final wording

---

## Architectural Integrity Rule (Updated)

mind remains:
- single source of meaning

tongue becomes:
- semantic + expression

behavior remains:
- protocol + orchestration

model remains:
- executor only

No layer may:
- duplicate intent logic
- override intent_result
- convert expression into a second mind

---

## Next Safe Step

After this phase:

1) introduce controlled expression modes
2) map expression_mode from:
   - why_now_signal
   - trust_mode
3) keep semantic_base untouched
4) allow model to realize expression dynamically

Golden rule remains:

meaning first
→ expression shaping
→ behavior overlay
→ model realization


---

## Matrix Architecture Clarification + Expression Matrix Schema v1

Date locked:
2026-04-06

### 1) Architectural correction

AATIF is NOT built as a linear chain.
It is built as a governed matrix.

Incorrect simplification:
- mind -> tongue -> behavior -> model

Operationally more correct:
- mind emits governed meaning coordinates
- tongue track and behavior track operate in parallel
- governed merge happens before model realization

Runtime shape:
mind
-> tongue track
-> behavior track
-> governed merge
-> model realization

Important note:
This is still not “free parallelism”.
All tracks remain governed by:
- Constitution
- Safety
- Supervisor
- Intent authority

### 2) Tongue clarification

Tongue is not only wording.
Tongue contains two internal substructures:

1. semantic_base
   - what should be said

2. response_expression
   - how it should sound

So the tongue track is:

tongue =
    semantic_base
    +
    response_expression

### 3) Response Expression principle

Response Expression does NOT:
- classify intent
- create meaning
- override intent_engine
- become a second mind

Response Expression ONLY:
- shapes tone
- shapes expansion
- shapes posture rendering
- shapes how governed meaning appears in language

### 4) Expression Matrix principle

Response Expression must be built as a matrix,
not as fixed sentence mapping.

Wrong pattern:
pricing + calm_respectful -> fixed sentence

Correct pattern:
pricing + calm_respectful ->
    expression coordinates
    then wording is realized from those coordinates

### 5) Scalability law for this layer

Anything added from this point must be expandable without breaking structure.

Required rule:
- schema first
- population later

Meaning:
- dimensions may be reserved before they are fully activated
- future additions must fit the matrix without rewriting the architecture
- no dimension may be introduced later in a way that forces structural collapse

This layer must support:
- controlled extension
- partial activation
- future reserved slots
- stable backward compatibility

### 6) Expression Matrix Schema v1

Current input authority for expression:
- hidden_intent
- why_now_signal
- trust_mode

These inputs guide expression,
but expression does NOT modify them.

### 7) Active dimensions (v1 active)

The first active expression dimensions are:

1. pressure
   - no_push
   - light_open
   - guided

2. expansion
   - minimal
   - concise
   - expanded

3. warmth
   - neutral
   - calm
   - warm

4. stance
   - direct_answer
   - defer_now
   - respectful_boundary
   - explanatory

These are the first active dimensions only.

### 8) Reserved dimensions (v1 reserved for later)

The following dimensions are intentionally reserved now,
even if not fully implemented yet:

5. initiative
   - reserved
   - governs whether the reply opens the next move or stays still

6. distance
   - reserved
   - governs social/relational closeness vs formal spacing

7. authority
   - reserved
   - governs degree of firmness / decisiveness / weight

8. confidence
   - reserved
   - governs degree of assertion vs restraint

Important rule:
Reserved dimensions MUST remain structurally present in the schema,
even if their runtime population is delayed.

Preferred placeholder value:
- unset

### 9) Schema form

Canonical expression schema shape:

response_expression = {
    "pressure": "...",
    "expansion": "...",
    "warmth": "...",
    "stance": "...",
    "initiative": "unset",
    "distance": "unset",
    "authority": "unset",
    "confidence": "unset"
}

### 10) v1 activation rule

Expression Matrix v1 activates only the following dimensions:
- pressure
- expansion
- warmth
- stance

The following remain reserved only:
- initiative
- distance
- authority
- confidence

No fake implementation is allowed.
No dimension may be claimed active before it has real routing logic.

### 11) Architectural safety rule

Response Expression must remain:
- expression-only
- matrix-shaped
- scalable
- backward-safe

It must NOT drift into:
- semantic classification
- behavior orchestration
- protocol routing
- model authority

### 12) Safe next step

After this schema lock,
the next safe implementation step is:

1. map active expression dimensions from:
   - hidden_intent
   - why_now_signal
   - trust_mode

2. keep reserved dimensions present as unset

3. implement expression coordinates before replacing sentence-level branches

### 13) Golden rule

Meaning stays upstream.
Expression stays governed.
Behavior stays separate.
Model stays subordinate.

And all new building from here must be:
expandable without architectural break.


---

## Response Expression Architecture Progress

Date locked:
2026-04-07

### Current confirmed architectural upgrade
AATIF now includes an explicit response-expression layer separated from intent meaning.

Confirmed current split:

- intent_engine.py
  -> decides meaning

- reply_base_mapper.py
  -> now includes expression shaping logic
  -> controls how meaning is said

### New architectural concepts now active

1) Response Expression Matrix
Current dimensions introduced:

- pressure
- expansion
- warmth
- stance
- execution_mode

Future placeholders already reserved:
- initiative
- distance
- authority
- confidence

Important truth:
This layer is not the mind.
It does not decide user meaning.
It only shapes delivery.

### Explicit Intent Lock
Confirmed architectural law:

explicit request > relationship posture

Meaning:
If the user gives a direct request such as:
- ارسل التفاصيل
- كم السعر
- اشرح

the system must execute now.

Context may soften tone only.
Context must not reverse the request.

Forbidden:
request -> defer

Allowed:
request -> execute + tone shaping

### Execution Mode
A new control dimension now exists:

- execute_now
- defer
- respect_stop
- shape_only

Architectural meaning:
expression alone is not enough;
the system must also decide whether the reply should proceed now.

### Tone Domain Direction
AATIF now distinguishes between:
- casual
- professional human
- formal

Current target:
professional human

Meaning:
- no slang
- no corporate stiffness
- no robotic phrasing

Confirmed example cleanup:
- removed casual slang like "الزبدة"
- replaced with business-human phrasing like:
  "أكيد، أرسل لك التفاصيل بشكل واضح ومختصر."

### Current system truth
The current response pipeline now moves toward:

meaning
-> execution control
-> expression matrix
-> base reply
-> expression shaping
-> optional LLM refinement

### Important architectural note
Current expression shaping inside reply_base_mapper.py is still transitional.

It currently uses rule-based realization blocks.
This is not the final ideal form.

Target future direction:
expression constraints
-> controlled language realization
-> optional LLM refinement with domain lock

### Locked lessons from this phase

1. Expression must not change domain
   - pricing stays pricing
   - details stay details
   - value stays value

2. Context must not reverse explicit present intent

3. Tone quality must be governed separately from intent meaning

4. Business-human language must avoid both:
   - slang
   - stiff formal writing

### Current stable examples

- "ارسل التفاصيل"
  -> "أكيد، أرسل لك التفاصيل بشكل واضح ومختصر."

- "كم السعر"
  -> "يعتمد على اللي تحتاجه، وإذا حاب أحدد لك بشكل أدق أقدر أوضح بعد ما أعرف احتياجك."

These are not final universal templates,
but they confirm the current tone direction.


---

## LLM Scope Decision (A-Scope Lock)

Date locked:
2026-04-07

### Current architectural decision
AATIF now uses LLM in a restricted scope only.

This is a deliberate controlled design decision.

### Scope rule

LLM is allowed only in heavier meaning zones such as:
- value
- objection
- identity

LLM is bypassed in direct execution zones such as:
- explicit details send
- direct pricing ask
- execute_now responses
- simple direct-answer paths that are already clean

### Reason

The model may improve language in complex meaning zones,
but it introduces drift in precision-critical direct execution replies.

Confirmed failure patterns seen before:
- tone degradation
- slang leakage
- pronoun drift
- domain drift
- over-compression
- unnecessary rewriting of already-clean governed replies

### New control rule

execute_now = precision zone

Meaning:
- no model rewriting
- governed base reply is sent as-is

### Runtime effect

Current behavior now confirmed:

- "ارسل التفاصيل"
  -> provider = bypass_from_execute_now

- "كم السعر"
  -> provider = bypass_from_execute_now

- "هل يسوي"
  -> provider = ollama

### Architectural meaning

LLM is not the default writer anymore.
It is now a scoped refinement layer.

This keeps:
- meaning authority upstream
- execution precision protected
- model creativity limited to the zones where it is actually useful

### Locked principle

LLM = refinement tool
NOT execution authority


---

## Behavior Overlay Scope Lock (A-Scope Completion)

Date locked:
2026-04-07

### Current confirmed decision
Behavior overlays are no longer allowed to attach to direct execution replies.

Confirmed direct execution examples now excluded from cost/value overlay:
- "كم السعر"
- "ارسل التفاصيل"

Confirmed heavier meaning zone still allowed:
- "هل يسوي"

### Architectural rule
Behavior overlay must remain overlay-only.

It must NOT:
- rewrite direct execution replies
- append cost/value framing to direct price asks
- append cost/value framing to direct details send requests

### Current scope rule
Allowed overlay zone:
- value meaning
- objection / resistance zones
- heavier framing zones only

Disallowed overlay zone:
- direct execution requests
- explicit direct answer paths
- execute_now replies

### Meaning
This completes A-scope consistency:

- direct execution replies remain governed and stable
- overlays stay downstream and limited
- behavior no longer acts as shadow tongue on execution-critical messages


---

## Identity Expression Structure Layer (Tone-Driven Structure)

Date locked:
2026-04-07

### Architectural clarification

Identity messages must not be implemented as fixed templates with minor tone variation.

Instead, identity expression must follow:

meaning
→ expression coordinates (pressure, expansion, warmth, stance)
→ structure selection
→ wording realization

### Rule

Tone does NOT select words only.

Tone selects:
- message structure
- level of explanation
- entry point of the idea
- depth of expansion

### Approved structures (v1)

1) conversational structure
- short
- low expansion
- human simplified framing
- no heavy explanation blocks

2) formal structure
- clear definition
- structured explanation
- medium expansion
- stable professional tone

3) positioning structure
- starts from differentiation
- focuses on decision/control layer
- avoids traditional introduction
- emphasizes "how it works" over "what it is"

### Important constraints

- structure must remain expression-only
- structure must NOT:
  - classify intent
  - introduce new meaning
  - override intent_engine
- semantic_base must remain intact
- only presentation shape changes

### Mapping rule

response_expression
→ selects structure family

NOT:
tone → fixed sentence

### Architectural meaning

This layer upgrades identity from:
template variation
→ structured expression system

This aligns with:

tongue =
    semantic_base
    +
    response_expression
    +
    structure realization

### Safety rule

This layer must NOT evolve into:
- semantic decision layer
- business logic layer
- intent classifier

It is strictly:
expression shaping only

### Status

- v1 concept locked
- implementation allowed inside:
  identity_message_builder.py
- must remain lightweight and extendable


---

## Identity Anchor Preservation Rule

Date locked:
2026-04-07

### Purpose

Prevent identity drift when multiple tone-driven structures are introduced.

### Definition

Identity expression may change structure, length, and entry point.

However, certain core elements MUST remain present across all structures.

These are called:

Identity Anchors

### Required anchors (v1)

Every identity message must preserve:

1) Primary entity:
- AI STUDIO PRO must be clearly present

2) Engineering layer:
- AATIF must be mentioned as a governance layer
- not a tool, not a feature

3) Linguistic layer:
- عاطف must be referenced as a human-facing expression
- not as the primary entity

4) Core effect (at least one form):
- reduction of randomness
OR
- improved decision consistency
OR
- structured understanding / decision flow

### Flexibility rules

Structures may:
- reorder anchors
- compress anchors
- merge anchors into one sentence
- distribute anchors across sentences

Structures must NOT:
- remove anchors
- replace anchors with weaker meaning
- distort relationships between:
  entity / governance / linguistic layers

### Compression allowance

In short/conversational structures:
- anchors may be compressed into minimal wording
- but must still be semantically present

### Enforcement note

This rule applies to:
- identity_message_builder.py
- any future identity rendering inside reply_base_mapper.py

### Architectural meaning

This ensures:

expression can evolve
without breaking identity truth

Meaning:
- structure is flexible
- truth is fixed


---

## Runtime Path Canonical Resolution

Date locked:
2026-04-07

Current runtime path note:

Logical runtime path:
- /Users/aatifsandbox/AATIF/10_runtime/aatif-sales-engine

Physical runtime path:
- /Users/aatifsandbox/aatif-sales-engine

Confirmed status:
- the logical runtime path is a symlink to the physical runtime path
- both paths point to the same files
- inode checks confirmed no duplicate runtime copy exists

Meaning:
- edits through either path affect the same runtime files
- there is no separate shadow runtime directory at this time

Operational rule:
- project references may continue to use the logical AATIF path
- but file resolution may display the physical path during runtime checks



---

## API Safe-Path Hooks (Demo Bypass)

Date locked:
2026-04-14

### What this documents

`api_server.py` contains four hardcoded reply paths that intentionally bypass
the tongue/behavior/model pipeline. This is an explicit, governed exception —
not a shadow mind.

### The four Safe-Path Hooks

Inside `_build_governed_response`, after `build_intent_result` and
`build_governed_reply_payload_from_intent` run, the function
`select_sales_hook_from_intent(intent_result, incoming_text)` may return one
of the following hook names:

- `"intro"`    → reply produced by `_build_intro_reply(lang)`
- `"price"`    → reply produced by `_build_price_reply(lang)`
- `"onboarding"` → reply produced by `_build_onboarding_reply(lang)`
- `"roi"`      → reply produced by `_build_roi_reply(lang)`

When any of these hooks fires, the API returns the hook's hardcoded bilingual
reply and skips `generate_final_reply` entirely. The LLM is not called.

### Why this exists

To guarantee predictable, safe, on-brand replies in demo / investor / VIP
contexts where even the governed model pass is considered unnecessary risk.

This aligns with two existing locked principles:
- LLM Scope Lock (2026-04-07): LLM is a refinement tool, not execution
  authority.
- Behavior Overlay Scope Lock (2026-04-07): direct execution zones are
  precision zones and should not be rewritten downstream.

Safe-Path Hooks extend this logic: for the four intents above, even the
governed base reply is skipped in favor of a hardcoded canonical message.

### What this is NOT

Safe-Path Hooks are NOT:
- a second mind (they do not classify intent — they consume intent_result)
- a second tongue (they do not expand expression — they return fixed strings)
- a replacement for `reply_base_mapper.py`
- an autonomy surface (they produce deterministic output only)

The intent_engine still runs. The reply_base_mapper still builds
`governed_base` and `semantic_pack`. Those outputs are simply not used when a
Safe-Path Hook returns a non-null hook name.

### Operational rules

- Safe-Path Hooks are permitted to exist ONLY in `api_server.py`.
- They MUST NOT be replicated in any other runtime file.
- They MUST use only the four hook names listed above (no expansion without
  an architect-approved map update).
- New hook names require a new entry in this section first.
- Hardcoded reply content inside the hook builders (`_build_intro_reply`,
  `_build_price_reply`, `_build_onboarding_reply`, `_build_roi_reply`) counts
  as canonical brand copy; changes require Architect approval.

### Failure containment

If `select_sales_hook_from_intent` returns `None` or any value not in
{intro, price, onboarding, roi}, execution falls through to the full
tongue/behavior/model pipeline. This is the default path.

### Golden rule

Safe-Path Hooks are an exception, not the architecture.
Default flow is:

    mind → tongue → behavior → model

Hooks are a narrow bypass for four explicitly named brand-critical intents.


---

## Runtime Secrets Policy

Date locked:
2026-04-14

### What this documents

The API server's authentication key (`AATIF_API_KEY`) must come from the
environment only. No token value may live in source code, even as a default.

### Rule

- `api_server.py` reads `AATIF_API_KEY` from `os.environ` only.
- If the variable is missing or empty, the server raises `RuntimeError` at
  import time and refuses to start. This is fail-closed behavior.
- The token is loaded from a local env file named `.env.aatif` sitting next
  to `api_server.py` in the runtime directory.
- `.env.aatif` is mode 600 (owner-only), and contains no other runtime logic.
- `run_aatif.sh` sources `.env.aatif` before launching the Python processes
  and aborts immediately if the file is missing.

### What the env file contains

```
export AATIF_API_KEY="<secret>"
export AATIF_ROOT="/Users/aatifsandbox/AATIF"
export OLLAMA_BASE_URL="http://127.0.0.1:11434"
export OLLAMA_MODEL="qwen2.5:7b"
```

### Rotation

To rotate the API key:
1. Edit `.env.aatif` with a new secret value.
2. Restart the servers: `./run_aatif.sh`.

No source file needs to be touched to rotate the token.

### Prior state (pre-lock)

Before 2026-04-14, `api_server.py` contained a literal default token value
on the `os.environ.get(...)` call. That token was visible to anyone reading
the source file. The default value has been removed; any copy of that prior
token is considered revoked.

### Operational rule

Secrets, API keys, and tokens may NEVER appear in:
- source `.py` files
- source `.sh` files tracked alongside code
- documentation committed to the repository
- project map files

They live ONLY in `.env.aatif` (or equivalent ops-managed env files).
