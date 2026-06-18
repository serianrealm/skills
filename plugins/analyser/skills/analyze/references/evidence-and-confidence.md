# Evidence and Confidence

Claim types:

- `static_fact`: deterministic repository observation
- `semantic_interpretation`: concise meaning added by the analyzer or model
- `engineering_inference`: reasoned conclusion from multiple facts

Confidence:

- `high`: direct deterministic evidence
- `medium`: strong pattern with explicit evidence
- `low`: weak signal, incomplete parser support, or ambiguous mapping

Every conclusion must list evidence locations. Low-confidence items must also appear in `evidence.low_confidence_items`.
