"""Stage 12 Phase II professional notes — a lightweight, non-blocking review signal, not a
moderation system or a clinical record. See MEDICAL_SAFETY.md section 1 for the prohibited-
pattern list this mirrors, and PRIVACY.md's coach_sharing consent purpose."""

# Deliberately broad substring matching (not word-boundary), since this is a review flag, not
# an enforcement gate — a false positive just means a legitimate note gets flagged for the
# founder's periodic review query (see app/routers/coach.py's create_note docstring), never
# blocked. The note always saves either way.
BLOCKED_TERMS: tuple[str, ...] = (
    "nodule",
    "dysphonia",
    "vocal fold",
    "vocal cord",
    "diagnos",  # catches diagnose / diagnosis / diagnosed
    "damaged",
    "polyp",
    "lesion",
    "paralysis",
    "paresis",
)


def find_flagged_terms(body: str) -> list[str]:
    lowered = body.lower()
    return [term for term in BLOCKED_TERMS if term in lowered]
