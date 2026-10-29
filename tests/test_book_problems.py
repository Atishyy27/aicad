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
    # d3 is left out on purpose: the lesson takes the pin head as 1.5 x the ROD (60 mm on a 55 mm
    # pin, a 2.5 mm lip), Bhandari eq 4.26o takes it as 1.5 x the PIN; the tool follows Bhandari.
    lesson = {"D": 40, "t": 50, "t1": 30, "t2": 20, "taper_d": 10}
    assert d.dims["d3"] >= 1.5 * d.dims["d"] - 1e-9
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


# ------------------------------------------------- Unwin 1899, page 179, gib and cotter

def test_gib_and_cotter_breadth_split_matches_unwin_figure_130():
    """One gib: the breadth divides 5/8 cotter and 3/8 gib, and the thickness is 0.25 b."""
    d = REGISTRY["gib_and_cotter"].design(load_n=50_000, gibs=1)
    b = d.dims["b"]
    assert d.dims["cotter_b"] == pytest.approx(0.625 * b)
    assert d.dims["gib_b"] == pytest.approx(0.375 * b)
    assert d.dims["cotter_b"] + d.dims["gib_b"] == pytest.approx(b)
    assert d.dims["t"] == pytest.approx(0.25 * b, abs=1)      # rounded up to whole mm


def test_gib_and_cotter_breadth_split_matches_unwin_figure_131():
    """Two gibs: 5/16 + 3/8 + 5/16, which is the whole breadth again."""
    d = REGISTRY["gib_and_cotter"].design(load_n=50_000, gibs=2)
    b = d.dims["b"]
    assert d.dims["cotter_b"] == pytest.approx(0.375 * b)
    assert d.dims["gib_b"] == pytest.approx(0.3125 * b)
    assert d.dims["cotter_b"] + 2 * d.dims["gib_b"] == pytest.approx(b)


def test_gib_and_cotter_taper_is_in_unwins_range():
    """Unwin gives 1 in 24 to 1 in 48 for a plain cotter, 1 in 8 to 1 in 16 with a screw."""
    d = REGISTRY["gib_and_cotter"].design(load_n=50_000)
    assert 8 <= d.dims["taper_one_in"] <= 48


def test_gib_and_cotter_shear_lengths_are_really_in_the_metal():
    """The two shear checks assume metal beyond the slot. This asserts the geometry
    actually has it: the rod end reaches a past the slot, and the strap has c before it."""
    j = REGISTRY["gib_and_cotter"]
    d = j.design(load_n=50_000)
    slot_start = d.dims["xs"] - d.dims["b"] / 2
    slot_end = d.dims["xs"] + d.dims["b"] / 2
    assert slot_start == pytest.approx(d.dims["c"])                       # strap metal first
    assert d.dims["rod_end_len"] - slot_end == pytest.approx(d.dims["a"])  # rod metal after
    assert d.dims["L"] > d.dims["rod_end_len"]                            # strap closes over the tip


def test_gib_and_cotter_checks_mirror_the_socket_and_spigot_set():
    """Every check is the cotter joint's check on a square section, so the names line up."""
    g = {c.name for c in REGISTRY["gib_and_cotter"].design(load_n=50_000).checks}
    assert g == {"rod tension", "rod end tension", "strap tension", "gib and cotter shear",
                 "rod end crushing", "strap crushing", "rod end shear", "strap end shear"}


# ------------------- Leutwiler 1917: a second, independent book on the same joints

def test_cotter_checks_match_leutwilers_ten_failure_modes():
    """Leutwiler article 98 lists ten ways a cotter joint fails. Ours are the same ten.

    (a) rod tension            (b) rod across the slot     (c) socket across the slot
    (d) cotter double shear    (e) rod end shear           (f) socket end shear
    (g) socket crushing        (h) ROD OR COTTER CRUSHING  (i) collar shear
    (j) collar crushing
    """
    d = REGISTRY["cotter"].design(load_n=50_000)
    assert len(d.checks) == 10
    # (h) is the one the NPTEL lesson omits; two books have it, so we keep it
    crush = next(c for c in d.checks if c.name == "spigot crushing")
    assert crush.formula == "P / (d1 t)"          # Leutwiler eq. (117): P = t d1 Sb


def test_coupling_bolt_formulas_match_leutwilers_equations():
    """Leutwiler (413): a = sqrt(8T / (pi n e Ss)).  (414): a f = 2T / (n e Sb).
    Rearranged for stress, those are exactly what this tool computes."""
    import math
    d = REGISTRY["flange_coupling"].design(torque_nm=500)
    T, dims = d.dims["torque_nmm"], d.dims
    a, n, e, f = dims["d_bolt"], dims["n_bolts"], dims["Dp"], dims["tf"]
    shear = next(c for c in d.checks if c.name == "bolt shear")
    crush = next(c for c in d.checks if c.name == "bolt crushing")
    assert shear.stress_mpa == pytest.approx(8 * T / (math.pi * a**2 * n * e))
    assert crush.stress_mpa == pytest.approx(2 * T / (n * a * f * e))


def test_coupling_proportions_are_still_not_claimed_as_verified():
    """Leutwiler says plainly that no standard flange coupling proportions existed and that
    published tables are manufacturers' practice. So the flag must stay false even though
    every check is now verified twice."""
    d = REGISTRY["flange_coupling"].design(torque_nm=500)
    assert d.verified_against_book is False


def test_sleeve_joint_uses_eight_of_leutwilers_ten_and_correctly_drops_the_collar():
    """The proportions have no book behind them, but the checks do: eight of Leutwiler's ten,
    with the socket reading as the sleeve. His (i) and (j) are collar failures and this joint
    has no collar, so they must be absent rather than merely forgotten."""
    d = REGISTRY["sleeve_and_cotter"].design(load_n=50_000)
    names = {c.name for c in d.checks}
    assert names == {"rod tension", "rod end tension", "sleeve tension", "cotter shear",
                     "rod end crushing", "sleeve crushing", "rod end shear", "sleeve end shear"}
    assert not any("collar" in n for n in names)
    # the crushing check NPTEL omits is present here too, as (h) P = t d1 Sb
    assert next(c for c in d.checks if c.name == "rod end crushing").formula == "P / (d2 t)"
    assert d.verified_against_book is False      # proportions still unverified, and they say so


def test_knuckle_matches_bhandari_example_4_5_exactly():
    """Bhandari, Design of Machine Elements, Ex 4.5 (pp 100-101): 50 kN, 30C8, Syt 400, FoS 5,
    so 80 MPa tension, crushing and bending and 40 MPa shear. Every adopted size is checked."""
    d = REGISTRY["knuckle"].design(load_n=50_000, tension_mpa=80, shear_mpa=40, crushing_mpa=80, design_factor=1.0)
    assert d.raw["rod_tension"] == pytest.approx(28.21, abs=0.01)
    assert d.raw["pin_shear"] == pytest.approx(28.21, abs=0.01)
    assert d.raw["pin_bending"] == pytest.approx(38.79, abs=0.01)
    book = {"D": 30, "D1": 35, "t": 40, "t1": 25, "d": 40, "d2": 80, "d3": 60}
    assert {k: d.dims[k] for k in book} == book
    stress = {c.name: round(c.stress_mpa, 2) for c in d.checks}
    for name in ("eye tension", "eye shear", "eye crushing"):
        assert stress[name] == 31.25
    for name in ("fork tension", "fork shear", "fork crushing"):
        assert stress[name] == 25.0


def test_knuckle_matches_bhandari_exercise_4_1():
    """Bhandari exercise 4.1 (p 138): 25 kN, 45C8, Syt 380, FoS 2.5, Ssy = 57.7% Syt.
    Printed answers: rod 14.47 mm, pin 13.47 mm."""
    d = REGISTRY["knuckle"].design(load_n=25_000, tension_mpa=380 / 2.5, shear_mpa=0.577 * 380 / 2.5,
                                   crushing_mpa=380 / 2.5, design_factor=1.0)
    assert d.raw["rod_tension"] == pytest.approx(14.47, abs=0.01)
    assert d.raw["pin_shear"] == pytest.approx(13.47, abs=0.01)


def test_cotter_matches_bhandari_example_4_2_except_the_cotter_width():
    """Bhandari Ex 4.2 (p 91): 50 kN, 30C8, FoS 6 for rods, so 66.67 tension, 33.33 shear,
    133.33 crushing. The book uses FoS 4 for the cotter alone, which is the only size that differs."""
    d = REGISTRY["cotter"].design(load_n=50_000, tension_mpa=66.67, shear_mpa=33.33, crushing_mpa=133.33,
                                  design_factor=1.0)
    assert d.raw["spigot_tension"] == pytest.approx(37.91, abs=0.02)
    assert d.raw["socket_tension"] == pytest.approx(52.04, abs=0.02)
    book = {"d": 32, "t": 10, "d1": 40, "d2": 55, "d3": 48, "d4": 80, "a": 24, "c": 24, "t1": 15}
    assert {k: d.dims[k] for k in book} == book
    assert d.all_passed
