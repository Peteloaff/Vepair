"""The Stage 6 exercise library: canonical, hand-curated exercise definitions.

This is data, not user-generated content — kept as plain Python so it's diffable, reviewable,
and importable directly by both the seed script (`scripts/seed_exercises.py`) and the routine
generator's tests, with one source of truth (matched into the `exercises` DB table by name).

**Deliberately excluded**: any aggressive screaming/distortion technique. The product brief is
explicit that these must not appear "unless a qualified methodology and appropriate safeguards
are established" — neither exists yet, so none are included. Every exercise here is a
well-established, low-risk vocal warmup/cooldown/rehabilitation technique (SOVT work, gentle
humming, lip/tongue trills, breathing) drawn from standard voice-training and voice-therapy
practice, not invented.

Every entry carries `audio_demo_url: None` — an explicit placeholder per the brief ("audio
demonstration placeholder"), not a missing feature. No real audio assets exist yet.
"""

from dataclasses import dataclass

# How demanding a category is on the voice, used by app/exercise_routine.py to filter what's
# safe to include given today's signals. Not a clinical claim — a coarse, defensible ordering:
# SOVT/breathing/humming/cooldown are the field-standard "safe to do almost any day" techniques;
# pitch glides and range exploration deliberately push toward the edges of comfortable range,
# which is exactly what should be held back when there's discomfort, heavy recent load, or a
# red recovery status.
CATEGORY_INTENSITY: dict[str, str] = {
    "Breathing": "low",
    "Vocal cooldown": "low",
    "SOVT": "low",
    "Straw phonation": "low",
    "Gentle humming": "low",
    "Resonant voice exercises": "moderate",
    "Lip trill": "moderate",
    "Tongue trill": "moderate",
    "Speaking voice recovery": "moderate",
    "Gentle sirens": "moderate",
    "Pitch glides": "high",
    "Range exploration": "high",
}

# A routine always opens with Breathing and closes with Vocal cooldown when the routine is long
# enough to fit them — standard warmup/cooldown structure, not a medical requirement.
OPENING_CATEGORY = "Breathing"
CLOSING_CATEGORY = "Vocal cooldown"


@dataclass(frozen=True)
class ExerciseDef:
    name: str
    category: str
    purpose: str
    instructions: str
    duration_seconds: int
    difficulty: str  # "easy" | "moderate" | "hard"
    contraindications: str | None
    target_measurement: str | None
    expected_result: str


SEED_EXERCISES: list[ExerciseDef] = [
    ExerciseDef(
        name="Diaphragmatic breathing",
        category="Breathing",
        purpose="Establish low, relaxed breath support before any phonation.",
        instructions=(
            "Sit or stand tall. Place a hand on your belly. Inhale slowly through the nose so "
            "your belly expands, keeping shoulders relaxed. Exhale slowly through pursed lips. "
            "Repeat for the full duration."
        ),
        duration_seconds=90,
        difficulty="easy",
        contraindications=None,
        target_measurement=None,
        expected_result="A relaxed, low breath pattern with minimal shoulder tension.",
    ),
    ExerciseDef(
        name="4-4-8 breath pacing",
        category="Breathing",
        purpose="Build steady, controlled airflow for sustained phonation.",
        instructions=(
            "Inhale for a slow count of 4, hold gently for 4, exhale for a slow count of 8. "
            "Keep the exhale smooth and even, not forced."
        ),
        duration_seconds=90,
        difficulty="easy",
        contraindications=(
            "Skip the breath hold if it feels uncomfortable — exhale on your own count instead."
        ),
        target_measurement=None,
        expected_result="An even, controlled exhale without straining.",
    ),
    ExerciseDef(
        name="Gentle hum on a comfortable pitch",
        category="Gentle humming",
        purpose="Warm up voiced sound with minimal vocal fold effort.",
        instructions=(
            "With lips lightly closed, hum on a single comfortable pitch — not your highest or "
            "lowest. Feel for a light buzzing/vibration around your lips and nose, not tension "
            "in your throat."
        ),
        duration_seconds=60,
        difficulty="easy",
        contraindications=None,
        target_measurement="hnr_db",
        expected_result="A steady, buzzy hum with no throat strain.",
    ),
    ExerciseDef(
        name="Humming pitch steps",
        category="Gentle humming",
        purpose="Extend the gentle hum across a few comfortable steps.",
        instructions=(
            "Hum a comfortable pitch, then step up one note, then back down, then one note "
            "below your start, then back. Keep every step within your easy, comfortable range."
        ),
        duration_seconds=75,
        difficulty="easy",
        contraindications=None,
        target_measurement="pitch_stability_semitones",
        expected_result="Smooth pitch changes with the same light, buzzy quality throughout.",
    ),
    ExerciseDef(
        name="Lip trill on a comfortable pitch",
        category="Lip trill",
        purpose=(
            "Semi-occluded exercise that eases vocal fold effort while building breath support."
        ),
        instructions=(
            "Relax your lips and let them vibrate ('motorboat' sound) while sustaining a "
            "comfortable pitch. If lips won't vibrate easily, lightly support your cheeks with "
            "two fingers."
        ),
        duration_seconds=60,
        difficulty="moderate",
        contraindications=(
            "Stop if you feel lightheaded from the airflow — pause and breathe normally."
        ),
        target_measurement="jitter_percent",
        expected_result="A steady lip trill without needing to force extra air.",
    ),
    ExerciseDef(
        name="Lip trill glide",
        category="Lip trill",
        purpose="Combine the lip trill with a gentle, comfortable pitch glide.",
        instructions=(
            "Start the lip trill on a comfortable low-mid pitch, glide gently upward within your "
            "comfortable range, then glide back down. Keep the trill smooth and unforced "
            "throughout."
        ),
        duration_seconds=75,
        difficulty="moderate",
        contraindications="Stay within a comfortable range — this is not a maximum-range exercise.",
        target_measurement="pitch_stability_semitones",
        expected_result="A smooth glide with the trill staying continuous, not sputtering.",
    ),
    ExerciseDef(
        name="Tongue trill on a comfortable pitch",
        category="Tongue trill",
        purpose="Another semi-occluded warmup option for those who find lip trills difficult.",
        instructions=(
            "Roll your tongue ('rrrr') while sustaining a comfortable pitch. If you can't roll "
            "your tongue, try the lip trill exercise instead."
        ),
        duration_seconds=60,
        difficulty="moderate",
        contraindications=None,
        target_measurement="jitter_percent",
        expected_result="A steady tongue trill without jaw or throat tension.",
    ),
    ExerciseDef(
        name="Resonant 'ng' hum",
        category="Resonant voice exercises",
        purpose="Find forward, easy resonance with minimal vocal effort.",
        instructions=(
            "Sustain an 'ng' sound (as in 'sing') on a comfortable pitch. Feel for vibration in "
            "the front of your face rather than tightness in your throat."
        ),
        duration_seconds=60,
        difficulty="moderate",
        contraindications=None,
        target_measurement="hnr_db",
        expected_result="A forward, buzzy resonance with an easy, unforced sound.",
    ),
    ExerciseDef(
        name="Resonant voice into speech",
        category="Resonant voice exercises",
        purpose="Carry easy resonance from a hum into spoken words.",
        instructions=(
            "Hum 'mmm', then let the hum open into a simple word starting with 'm' (e.g. 'mmm-"
            "mom', 'mmm-me'). Keep the same easy, forward feeling as you move into the word."
        ),
        duration_seconds=90,
        difficulty="moderate",
        contraindications=None,
        target_measurement=None,
        expected_result="Speech that keeps the same easy, resonant quality as the hum.",
    ),
    ExerciseDef(
        name="Straw phonation (SOVT)",
        category="SOVT",
        purpose="Semi-occluded vocal tract exercise to balance breath pressure and reduce effort.",
        instructions=(
            "Phonate a comfortable, sustained pitch through a narrow straw (or pursed lips if no "
            "straw is available). Keep the airflow steady and unforced for the full duration."
        ),
        duration_seconds=60,
        difficulty="easy",
        contraindications=(
            "Stop if you feel lightheaded — this exercise changes airflow resistance."
        ),
        target_measurement="hnr_db",
        expected_result="A steady tone with a light, easy sensation, not pressure or strain.",
    ),
    ExerciseDef(
        name="Straw phonation glide (SOVT)",
        category="SOVT",
        purpose="Extend straw phonation across a gentle pitch glide.",
        instructions=(
            "Phonate through a straw while gliding gently from a comfortable low pitch to a "
            "comfortable higher pitch and back, without straining at either end."
        ),
        duration_seconds=75,
        difficulty="moderate",
        contraindications="Stop if you feel lightheaded.",
        target_measurement="pitch_stability_semitones",
        expected_result="A smooth glide with even airflow throughout.",
    ),
    ExerciseDef(
        name="Straw-in-water phonation",
        category="Straw phonation",
        purpose="A resistance-based SOVT variant used widely in voice therapy warmups.",
        instructions=(
            "With the straw's end submerged shallowly in a glass of water, phonate a comfortable "
            "pitch so a steady stream of bubbles forms. Keep the bubbling even, not sputtering."
        ),
        duration_seconds=60,
        difficulty="easy",
        contraindications="Stop if you feel lightheaded.",
        target_measurement="hnr_db",
        expected_result="Even, continuous bubbling with an easy, unforced tone.",
    ),
    ExerciseDef(
        name="Straw-in-water pitch glide",
        category="Straw phonation",
        purpose="Combine the water-resistance SOVT technique with a gentle pitch glide.",
        instructions=(
            "With the straw shallowly submerged, glide gently from a comfortable low note to a "
            "comfortable higher note and back, keeping the bubbling continuous throughout."
        ),
        duration_seconds=75,
        difficulty="moderate",
        contraindications="Stop if you feel lightheaded.",
        target_measurement="pitch_stability_semitones",
        expected_result="A smooth glide with continuous, even bubbling.",
    ),
    ExerciseDef(
        name="Gentle pitch glide",
        category="Pitch glides",
        purpose="Explore smooth pitch transitions within your comfortable range.",
        instructions=(
            "On an 'ee' or 'oo' vowel, glide smoothly from a comfortable low pitch to a "
            "comfortable high pitch and back down, like a gentle siren. Stop well short of any "
            "strain."
        ),
        duration_seconds=60,
        difficulty="moderate",
        contraindications=(
            "Never glide into a pitch that feels strained, pressed, or uncomfortable."
        ),
        target_measurement="pitch_stability_semitones",
        expected_result="A smooth, connected glide with no obvious breaks or strain.",
    ),
    ExerciseDef(
        name="Two-octave-feel glide",
        category="Pitch glides",
        purpose="A longer, fuller gentle glide once the voice is warmed up.",
        instructions=(
            "On a comfortable vowel, glide slowly from your comfortable low range up through "
            "your comfortable high range and back, keeping the motion smooth and even. This is "
            "about smoothness, not maximum range."
        ),
        duration_seconds=90,
        difficulty="hard",
        contraindications="Stop immediately if any part of the glide feels strained or painful.",
        target_measurement="f0_max_hz",
        expected_result="A smooth, connected glide across your comfortable range.",
    ),
    ExerciseDef(
        name="Gentle siren",
        category="Gentle sirens",
        purpose="A classic warmup connecting registers smoothly.",
        instructions=(
            "On an 'oo' vowel, glide up and down like a gentle siren, staying light and easy. "
            "Focus on a smooth connection through any register shifts rather than volume."
        ),
        duration_seconds=60,
        difficulty="moderate",
        contraindications="Keep it light — this is not a loud or forceful exercise.",
        target_measurement="pitch_stability_semitones",
        expected_result="A smooth siren with an even, connected quality across the glide.",
    ),
    ExerciseDef(
        name="Slow siren with breath control",
        category="Gentle sirens",
        purpose="Combine the siren glide with slower, more controlled breath pacing.",
        instructions=(
            "Take a relaxed breath, then siren slowly up and down on 'oo', trying to make one "
            "full up-and-down cycle last the whole exhale without running out of air abruptly."
        ),
        duration_seconds=75,
        difficulty="moderate",
        contraindications="Keep it light and unforced.",
        target_measurement="duration_seconds",
        expected_result="A full, controlled siren cycle without gasping at the end.",
    ),
    ExerciseDef(
        name="Comfortable range exploration",
        category="Range exploration",
        purpose="Gently map how your comfortable range feels today, without forcing extremes.",
        instructions=(
            "Starting from a comfortable mid pitch, step upward note by note as long as it feels "
            "completely comfortable, then do the same stepping downward. Stop well before any "
            "strain — this is not a test of your maximum range."
        ),
        duration_seconds=90,
        difficulty="hard",
        contraindications=(
            "Stop immediately at the first sign of strain, pressure, or discomfort. This "
            "exercise is never meant to be pushed."
        ),
        target_measurement="f0_max_hz",
        expected_result="A clear sense of today's comfortable range, without any strain.",
    ),
    ExerciseDef(
        name="High-note approach",
        category="Range exploration",
        purpose="Gently approach the upper edge of comfortable range with light onset.",
        instructions=(
            "On a gentle 'ee', step upward in small intervals toward the top of your comfortable "
            "range, using a light, breathy onset rather than pushing. Stop the moment it stops "
            "feeling easy."
        ),
        duration_seconds=90,
        difficulty="hard",
        contraindications="Never force or push into an uncomfortable note.",
        target_measurement="f0_max_hz",
        expected_result="Reaching the upper part of your comfortable range with a light onset.",
    ),
    ExerciseDef(
        name="Vocal cooldown hum",
        category="Vocal cooldown",
        purpose="Bring the voice back down to a relaxed, resting state after use.",
        instructions=(
            "Hum gently on a low, comfortable pitch, letting the sound trail off naturally. "
            "Repeat a few times, each one softer and more relaxed than the last."
        ),
        duration_seconds=60,
        difficulty="easy",
        contraindications=None,
        target_measurement=None,
        expected_result="A relaxed, low, easy hum with no residual tension.",
    ),
    ExerciseDef(
        name="Cooldown straw phonation",
        category="Vocal cooldown",
        purpose="A gentle SOVT cooldown to release tension after a routine.",
        instructions=(
            "Phonate softly through a straw on a low, comfortable pitch for a few slow breaths, "
            "letting each one feel easier than the last."
        ),
        duration_seconds=60,
        difficulty="easy",
        contraindications="Stop if you feel lightheaded.",
        target_measurement=None,
        expected_result="A relaxed, easy feeling in the throat at the end of the routine.",
    ),
    ExerciseDef(
        name="Easy conversational reading",
        category="Speaking voice recovery",
        purpose="Reintroduce speaking voice gently after focused vocal exercises.",
        instructions=(
            "Read a short passage aloud in your normal, comfortable speaking voice — no "
            "projecting or performing. Focus on relaxed, natural pacing and breath."
        ),
        duration_seconds=90,
        difficulty="easy",
        contraindications=None,
        target_measurement=None,
        expected_result="Natural, relaxed speech with no strain or excess volume.",
    ),
    ExerciseDef(
        name="Gentle vocal rest reminder",
        category="Speaking voice recovery",
        purpose="A brief, low-demand check-in on speaking voice habits during a recovery day.",
        instructions=(
            "Speak a few comfortable sentences at a soft, easy volume, noticing your habitual "
            "pitch and effort level. This is a light awareness exercise, not a workout."
        ),
        duration_seconds=60,
        difficulty="easy",
        contraindications=None,
        target_measurement=None,
        expected_result="Increased awareness of easy, low-effort speaking voice.",
    ),
]

assert {e.category for e in SEED_EXERCISES} == set(CATEGORY_INTENSITY)

# Stage 8: which vepair_audio_engine sample-type label best matches each category, purely for
# the periodicity-measure (jitter/shimmer/HNR) gate inside vepair_audio_engine.measurements —
# see SUSTAINED_PHONATION_SAMPLE_TYPES. None means "no vocal signal to analyze" (Breathing).
# This is a local label for exercise-audio analysis only, unrelated to Recording.sample_type
# and Stage 4's baseline (exercise audio is never fed into the personal baseline — see
# app/exercise_audio.py).
CATEGORY_ANALYSIS_SAMPLE_TYPE: dict[str, str | None] = {
    "Breathing": None,
    "Gentle humming": "hum",
    "Lip trill": "sustained_ah",
    "Tongue trill": "sustained_ah",
    "Resonant voice exercises": "sustained_ah",
    "SOVT": "hum",
    "Straw phonation": "hum",
    "Pitch glides": "glide",
    "Gentle sirens": "glide",
    "Range exploration": "glide",
    "Vocal cooldown": "hum",
    "Speaking voice recovery": "sentence",
}
assert set(CATEGORY_ANALYSIS_SAMPLE_TYPE) == set(CATEGORY_INTENSITY)
