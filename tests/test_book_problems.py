"""The tool against worked problems with published answers.

Source: NPTEL, IIT Kharagpur, Design of Machine Elements I, Module 4 Lesson 2,
"Cotter and knuckle joint", problems Q.1 and Q.2. The PDF is in reference/.
"""
import pytest

from aicad.joints import REGISTRY


def test_knuckle_100kn_matches_the_lesson():
    """Q.2: 100 kN, 100 MPa tension, 65 shear, 150 crushing."""
    d = REGISTRY["knuckle"].design(load_n=100_000, tension_mpa=100, shear_mpa=65,
                                   crushing_mpa=150, design_factor=1.0)
    lesson = {"D": 40, "d3": 60, "t": 50, "t1": 30, "t2": 20, "taper_d": 10}
    for key, want in lesson.items():
        assert d.dims[key] == pytest.approx(want), f"{key}: ours {d.dims[key]}, lesson {want}"
    # the lesson gives d2 = 2D = 80, but it checks the eye against the original 40 mm pin.
    # With the raised pin actually in the hole its own eye-shear check fails (80 MPa > 65),
    # so the tool grows the eye instead and says so.
    assert d.dims["d2"] >= 80
    # the lesson finds the pin fails in bending at 40 mm and raises it; so does the tool
    assert d.raw["pin_bending"] == pytest.approx(48.6, abs=0.5)
    assert d.dims["d"] >= d.raw["pin_bending"]      # the lesson picks 55, we pick the next preferred size
    assert d.all_passed, [c.name for c in d.checks if not c.passed]


def test_knuckle_pin_bending_formula_matches_the_lesson_number():
    """The lesson says a 55 mm pin gives 69 MPa for Q.2."""
    d = REGISTRY["knuckle"].design(load_n=100_000, tension_mpa=100, shear_mpa=65, crushing_mpa=150,
                                   design_factor=1.0, bending_mode="check_only")
    t, t1 = d.dims["t"], d.dims["t1"]
    import math
    sigma_at_55 = 16 * 100_000 * (t1 / 3 + t / 4) / (math.pi * 55**3)
    assert sigma_at_55 == pytest.approx(69, abs=1)


def test_knuckle_check_list_matches_the_lesson():
    d = REGISTRY["knuckle"].design(load_n=100_000, tension_mpa=100, shear_mpa=65, crushing_mpa=150)
    names = {c.name for c in d.checks}
    # the lesson lists nine: rod tension, pin shear, pin bending, eye shear/crushing/tension,
    # fork shear/tension/crushing
    assert names == {"rod tension", "pin double shear", "pin bending", "eye tension", "eye shear",
                     "eye crushing", "fork tension", "fork shear", "fork crushing"}


def test_cotter_50kn_is_in_the_same_family_as_the_lesson():
    """Q.1: 50 kN, 150 MPa tension, 110 shear, 110 crushing.

    Names differ: the lesson calls the socket collar d3 and the spigot collar d4; the tool
    calls them d4 and d3. Fed the lesson's own 25 mm rod, every dimension lands in the same
    family, but heavier, because of the extra check the next test pins down.
    """
    d = REGISTRY["cotter"].design(load_n=50_000, rod_diameter_mm=25, tension_mpa=150,
                                  shear_mpa=110, crushing_mpa=110, design_factor=1.0)
    assert d.dims["d1"] == pytest.approx(30, abs=4)      # lesson: 30
    assert d.dims["d2"] == pytest.approx(40, abs=5)      # lesson: 40
    assert d.dims["d3"] == pytest.approx(40, abs=4)      # lesson d4: 40, spigot collar
    assert d.dims["b"] >= 27                             # lesson: 27
    assert d.dims["t"] >= 10                             # lesson: 10, ours is thicker
    assert d.all_passed


def test_cotter_picks_its_own_rod_from_the_same_size_table():
    """Rod from tension is 20.6 mm. The lesson reads 20 and then picks 25 by hand; the tool
    takes the next size in the lesson's own table, 22, and every check still passes."""
    d = REGISTRY["cotter"].design(load_n=50_000, tension_mpa=150, shear_mpa=110,
                                  crushing_mpa=110, design_factor=1.0)
    assert d.dims["d"] == 22
    assert d.all_passed


def test_the_lessons_own_cotter_fails_the_spigot_crushing_check():
    """The lesson checks crushing of the socket, (d3 - d1) t, but not crushing between the
    cotter and the spigot, d1 t, which Khurmi does check. At the lesson's own final answer
    (d1 = 30, t = 10) that check reads 167 MPa against 110 allowed, so the tool sizes the
    cotter thicker on purpose rather than reproducing the lesson number."""
    lesson = 50_000 / (30 * 10)
    assert lesson == pytest.approx(166.7, abs=0.1)
    assert lesson > 110
    d = REGISTRY["cotter"].design(load_n=50_000, rod_diameter_mm=25, tension_mpa=150,
                                  shear_mpa=110, crushing_mpa=110, design_factor=1.0)
    crush = next(c for c in d.checks if c.name == "spigot crushing")
    assert crush.passed


def test_cotter_check_list_matches_the_lesson():
    d = REGISTRY["cotter"].design(load_n=50_000, tension_mpa=150, shear_mpa=110, crushing_mpa=110)
    names = {c.name for c in d.checks}
    assert names == {"rod tension", "spigot tension", "socket tension", "cotter shear",
                     "spigot crushing", "socket crushing", "spigot end shear", "socket end shear",
                     "spigot collar crushing", "spigot collar shear"}


@pytest.mark.parametrize("joint", ["knuckle", "cotter"])
def test_data_files_now_name_their_source(joint):
    data = REGISTRY[joint].DATA
    assert data["verified_against_book"] is True
    assert "NPTEL" in data["verified_against"] and "IIT Kharagpur" in data["verified_against"]
