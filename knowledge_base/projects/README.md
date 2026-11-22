# Project KB snippets (Site chat)

Canonical files loaded by chat (`responses_api._PROJECT_KB_FILES` + allowlist in `get_knowledge`):

| Key | File | Project page |
|-----|------|--------------|
| `wakesurf_safari` | `wakesurf_safari.txt` | `/projects/wakesurf-safari` |
| `wake_challenge` | `wake_challenge.txt` | `/projects/wakesurf-challenge-2025` |
| `mywave_ruza_camp` | `mywave_ruza_camp.txt` | `/projects/mywave-ruza-camp` |

Do **not** add extra `*.txt` here without updating the allowlist — legacy `get_knowledge('projects')` used to dump the whole directory.

Agents / Owner memory uses `knowledge_intake` in AI-Team, not these files.
 See `docs/contracts/SITE_KB_AGENTS_INTAKE_BOUNDARY.md` in mywave-ai-team.

