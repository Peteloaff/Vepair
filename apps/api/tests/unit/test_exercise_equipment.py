from app.exercise_library import SEED_EXERCISES


def test_every_straw_exercise_lists_a_straw() -> None:
    straw_exercises = [e for e in SEED_EXERCISES if "straw" in e.name.lower()]
    assert straw_exercises
    for exercise in straw_exercises:
        assert any("straw" in item.name.lower() for item in exercise.equipment), exercise.name


def test_straw_in_water_exercises_also_list_water() -> None:
    water_exercises = [e for e in SEED_EXERCISES if "water" in e.name.lower()]
    assert water_exercises
    for exercise in water_exercises:
        assert any("water" in item.name.lower() for item in exercise.equipment), exercise.name


def test_every_equipment_item_explains_what_it_is_and_how_to_use_it() -> None:
    for exercise in SEED_EXERCISES:
        for item in exercise.equipment:
            assert item.name.strip(), exercise.name
            assert item.description.strip(), f"{exercise.name}: {item.name}"
            assert item.how_to_use.strip(), f"{exercise.name}: {item.name}"


def test_equipment_free_exercises_stay_equipment_free() -> None:
    by_name = {e.name: e for e in SEED_EXERCISES}
    assert by_name["Diaphragmatic breathing"].equipment == ()
    assert by_name["Gentle hum on a comfortable pitch"].equipment == ()
