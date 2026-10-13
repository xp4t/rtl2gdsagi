#!/usr/bin/env python3
"""Record a minimal live provider availability probe without logging credentials."""
import datetime
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from rtl2gdsagi.agent.client import redact_sensitive_text
import anthropic

record = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'provider': 'Anthropic', 'requested_model': 'claude-sonnet-5',
          'scope': 'Minimal live availability probe; not a repair proposal.'}
try:
    response = anthropic.Anthropic(timeout=30).messages.create(
        model='claude-sonnet-5', max_tokens=8,
        messages=[{'role': 'user', 'content': 'Reply OK.'}])
    record.update(available=True, observed_model=response.model,
                  input_tokens=response.usage.input_tokens,
                  output_tokens=response.usage.output_tokens)
except Exception as exc:
    record.update(available=False, error_type=type(exc).__name__,
                  http_status=getattr(exc, 'status_code', None),
                  error=redact_sensitive_text(str(exc)))
output = ROOT / 'rtl2gdsagi_paper/evidence/provider_credit_probe_frozen.json'
output.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
