# Artificial intelligence usage — IGNIS UY

Documentation must reflect **tools actually used by the team**, not tools mentioned by other projects or inferred from source-code files.

## Current application component

| Function | Verified technology | Use |
|---|---|---|
| Ask IGNIS (`ignis_ask.py`) | Explicit Python + Pandas rules | Answers statistical questions exclusively using files uploaded in the session |
| Geospatial and historical calculations | Python, NumPy, Pandas, SciPy | Deterministic counts, coordinates, thresholds, charts, and results |
| Generative AI at runtime | **Not identified** | Do not label Ask IGNIS as GPT, Gemini, or another LLM |

There is no evidence that an AI model generates report numbers or detects wildfires. Quantitative outputs come from application code.

## Team usage log to complete before submission

For each generative tool used during planning, research, design, programming, or review, specify:

| Tool / model and version | Stage | Work performed | Inputs supplied | Human review | Responsible person |
|---|---|---|---|---|---|
| Pending confirmation and completion | Pending confirmation | Pending confirmation | Pending confirmation | Pending confirmation | Pending confirmation |

Do not invent model names or versions, attribute scientific validation to an AI, or include secrets, personal information, or credentials in public documentation.

Using programming assistants **does not replace testing, scientific evaluation, or team responsibility**.

For any future generative analyst, maintain a deterministic tool layer and include citations and filters for each result. The model should only explain already calculated data and should indicate uncertainty.

**See also:** [SI usage and provenance](SI_USAGE.md) and [machine-readable disclosures](si_usage.json) for project-level declarations, including generated artwork and audio.
