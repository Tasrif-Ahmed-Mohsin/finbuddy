import os
import tempfile

# Keep test runs from writing to the real audit log: point the module-level app at a temp file
# before app.main is imported anywhere.
os.environ.setdefault("SATHI_AUDIT_PATH", os.path.join(tempfile.mkdtemp(prefix="sathi-test-"), "audit.jsonl"))
# Never call the real LLM from tests (no network, no cost); tests inject a fake client when needed.
os.environ["SATHI_LLM_ENABLED"] = "0"
