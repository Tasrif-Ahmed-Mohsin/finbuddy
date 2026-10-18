import os
import tempfile

# Keep test runs from writing to the real audit log: point the module-level app at a temp file
# before app.main is imported anywhere.
os.environ.setdefault("SATHI_AUDIT_PATH", os.path.join(tempfile.mkdtemp(prefix="sathi-test-"), "audit.jsonl"))
# Never call the real LLM from tests (no network, no cost); tests inject a fake client when needed.
os.environ["SATHI_LLM_ENABLED"] = "0"
# Fixed exchange rates in tests (deterministic numbers, no network); the real history CSV is still used for ranges.
os.environ["SATHI_FX_MODE"] = "fixture"
# Never send WhatsApp messages from tests; tests that need it build their own notifier with a fake transport.
os.environ["WHATSAPP_MODE"] = "off"
# Most tests are about other rules and approve with a plain call; the passkey tests switch the requirement back on.
os.environ["SATHI_PASSKEY_REQUIRED"] = "0"
# Most tests assume the family already said yes to the AI; the consent tests start from "not asked".
os.environ["SATHI_AI_DEFAULT"] = "1"
