"""The draft of joints and poses (mechanical_cad/motion.py): the record, what a scene is told, where things are."""
import json
import math

import pytest

from mechanical_cad import flatten, jsonio, layout, motion
from mechanical_cad.cli import main

PAIR_1 = "FIXTURE ROOT:1/PIN PAIR:1"
PAIR_2 = "FIXTURE ROOT:1/PIN PAIR:2"

# The pins of both pairs swing about the upright through the root's origin, and in each pair one pin slides away
# from the other; a spacer turns by itself.
RECORD = """
schema_version = 1

[joints.swing]
assembly = "fixture-root"
kind = "revolute"
origin_mm = [0.0, 0.0, 0.0]
direction = [0.0, 2.0, 0.0]
range_deg = [-90.0, 90.0]
stays = ["BASE PLATE:1"]

[joints.pin]
assembly = "pin-pair"
kind = "prismatic"
origin_mm = [25.0, 0.0, 0.0]
direction = [1.0, 0.0, 0.0]
range_mm = [0.0, 10.0]
moves = ["PIN:2"]
note = "the second pin of a pair, away from the first"

[joints.spacer]
assembly = "fixture-with-spacer"
kind = "revolute"
origin_mm = [-25.0, 8.0, -15.0]
direction = [0.0, 1.0, 0.0]
range_deg = [-180.0, 180.0]
moves = ["SPACER:1"]

[poses.apart]
pin = 10.0

[poses.swung]
swing = 90.0
pin = 10.0
"""


def derived_of(project_dir, text=RECORD, root="fixture-with-spacer"):
    (project_dir / motion.FILE).write_text(text, encoding="utf-8")
    project = layout.load(project_dir)
    data = motion.read(project_dir / motion.FILE)
    assert motion.problems(data, project) == []
    scene = flatten.flatten(project, root)[0]
    return motion.resolve(data, project, scene, root, "0" * 64), scene


def near(a, b, tol=1e-9):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def place(matrix):
    return [matrix[r][3] for r in range(3)]


def test_a_joint_becomes_a_line_in_the_scene_for_every_place_of_its_assembly(project_copy):
    derived, scene = derived_of(project_copy)
    assert sorted(derived["joints"]) == [f"pin@{PAIR_1}", f"pin@{PAIR_2}", "spacer", "swing"]
    # the pair's frame is turned and moved by the root that places it, and its lengths are centimetres; the
    # joint's are millimetres whatever the assembly's unit
    first, second = derived["joints"][f"pin@{PAIR_1}"], derived["joints"][f"pin@{PAIR_2}"]
    assert near(first["origin_mm"], [25.0, 8.0, -15.0]) and near(second["origin_mm"], [25.0, 8.0, 15.0])
    assert near(first["direction"], [1.0, 0.0, 0.0])
    assert (first["kind"], first["lower"], first["upper"], first["unit"]) == ("prismatic", 0.0, 10.0, "mm")
    swing = derived["joints"]["swing"]
    assert near(swing["direction"], [0.0, 1.0, 0.0]) and swing["unit"] == "deg"      # a direction is made a unit long
    assert derived["scene"] == "scene.json" and derived["source"]["file"] == "motion.toml"
    assert {o["id"] for o in scene["occurrences"]} >= set(derived["moved"])


def test_what_moves_is_named_with_its_joints_outermost_first(project_copy):
    derived, scene = derived_of(project_copy)
    assert derived["moved"] == {
        f"{PAIR_1}/PIN:1": ["swing"], f"{PAIR_1}/PIN:2": ["swing", f"pin@{PAIR_1}"],
        f"{PAIR_2}/PIN:1": ["swing"], f"{PAIR_2}/PIN:2": ["swing", f"pin@{PAIR_2}"],
        "SPACER:1": ["spacer"]}
    # a pose says a joint once, and it holds for every place of that joint
    assert derived["poses"] == {"apart": {f"pin@{PAIR_1}": 10.0, f"pin@{PAIR_2}": 10.0},
                                "swung": {f"pin@{PAIR_1}": 10.0, f"pin@{PAIR_2}": 10.0, "swing": 90.0}}


def test_a_joint_of_an_assembly_the_scene_does_not_hold_is_left_out(project_copy):
    derived, _ = derived_of(project_copy, root="fixture-root")
    assert sorted(derived["joints"]) == [f"pin@{PAIR_1.split('/', 1)[1]}", f"pin@{PAIR_2.split('/', 1)[1]}", "swing"]
    assert derived["poses"]["swung"]["swing"] == 90.0


def test_a_turn_is_right_handed_about_the_line_and_a_slide_goes_along_it():
    turn = {"kind": "revolute", "origin_mm": [1.0, 0.0, 0.0], "direction": [0.0, 0.0, 1.0]}
    quarter = motion.transform(turn, 90.0)
    assert near([sum(quarter[r][c] * v for c, v in enumerate([2.0, 0.0, 5.0, 1.0])) for r in range(3)], [1.0, 1.0, 5.0])
    assert near([sum(quarter[r][c] * v for c, v in enumerate([1.0, 0.0, 7.0, 1.0])) for r in range(3)], [1.0, 0.0, 7.0])
    slide = {"kind": "prismatic", "origin_mm": [9.0, 9.0, 9.0], "direction": [0.0, 0.6, 0.8]}
    assert near(place(motion.transform(slide, 5.0)), [0.0, 3.0, 4.0])
    assert motion.transform(turn, 0.0)[0][:3] == [1.0, 0.0, 0.0]


def test_a_joint_that_is_carried_moves_first_and_is_then_carried(project_copy):
    derived, scene = derived_of(project_copy)
    rest = {o["id"]: o["transform_world"] for o in scene["occurrences"]}
    at = motion.values(derived, "swung")
    where = motion.placed(derived, scene, at)
    for pair in (PAIR_1, PAIR_2):
        x, y, z = place(rest[f"{pair}/PIN:2"])
        assert near(place(where[f"{pair}/PIN:2"]), [z, y, -(x + 10.0)])         # slid 10 along x, then a quarter turn about y
        x, y, z = place(rest[f"{pair}/PIN:1"])
        assert near(place(where[f"{pair}/PIN:1"]), [z, y, -x])
    assert where["FIXTURE ROOT:1/BASE PLATE:1"] == rest["FIXTURE ROOT:1/BASE PLATE:1"]
    assert where["SPACER:1"] == rest["SPACER:1"]
    # at zero nothing has moved, and the posed scene is the scene
    assert motion.placed(derived, scene, motion.values(derived)) == rest
    moved = motion.posed(derived, scene, at)
    assert moved["occurrences"][0].keys() == scene["occurrences"][0].keys() and moved["parts"] is scene["parts"]
    assert [o["transform"] for o in moved["occurrences"]] == [o["transform"] for o in scene["occurrences"]]


def test_a_spacer_turned_half_round_about_its_own_line_stays_where_it_is(project_copy):
    derived, scene = derived_of(project_copy)
    rest = next(o["transform_world"] for o in scene["occurrences"] if o["id"] == "SPACER:1")
    turned = motion.placed(derived, scene, {"spacer": 180.0})["SPACER:1"]
    assert near(place(turned), place(rest))                                    # its origin is on the line
    assert near([turned[r][0] for r in range(3)], [-rest[r][0] for r in range(3)])


def test_where_the_joints_are_is_zero_a_pose_or_what_is_given(project_copy):
    derived, _ = derived_of(project_copy)
    assert set(motion.values(derived).values()) == {0.0}
    assert motion.values(derived, "apart", {"swing": -45})["swing"] == -45.0
    with pytest.raises(motion.MotionError, match="outside its range, 0 to 10"):
        motion.values(derived, given={f"pin@{PAIR_1}": 10.5})
    with pytest.raises(motion.MotionError, match="there is no pose 'open'; the poses: apart, swung"):
        motion.values(derived, "open")
    with pytest.raises(motion.MotionError, match="there is no joint 'lever'; the joints: pin@"):
        motion.values(derived, given={"lever": 1})
    # a joint in several places may be given by its name alone, for all of them
    both = motion.values(derived, given=motion.given("pin=4, swing=-30"))
    assert (both[f"pin@{PAIR_1}"], both[f"pin@{PAIR_2}"], both["swing"], both["spacer"]) == (4.0, 4.0, -30.0, 0.0)
    assert motion.given(f"pin@{PAIR_1}=2.5") == {f"pin@{PAIR_1}": 2.5} and motion.given("") == {}
    with pytest.raises(motion.MotionError, match="expected JOINT=VALUE"):
        motion.given("swing")
    assert motion.steps(derived["joints"]["swing"], 5) == [-90.0, -45.0, 0.0, 45.0, 90.0]


@pytest.mark.parametrize("old, new, words", [
    ("schema_version = 1", "schema_version = 2", "schema_version must be 1"),
    ('assembly = "pin-pair"', 'assembly = "pin"', "assembly must be the key of an assembly of this project, not 'pin'"),
    ('kind = "prismatic"', 'kind = "screw"', "kind must be one of prismatic, revolute"),
    ("range_mm = [0.0, 10.0]", "range_deg = [0.0, 10.0]", "range_mm must be [lower, upper]"),
    ("range_mm = [0.0, 10.0]", "range_mm = [10.0, 0.0]", "two numbers with the lower one first"),
    ("range_deg = [-90.0, 90.0]", "range_deg = [-90.0, 400.0]", "within one turn either way"),
    ("direction = [0.0, 2.0, 0.0]", "direction = [0.0, 0.0, 0.0]", "direction must be three numbers that are not all zero"),
    ("origin_mm = [25.0, 0.0, 0.0]", 'origin_mm = [25.0, 0.0]', "origin_mm must be three numbers"),
    ('moves = ["PIN:2"]', 'moves = ["PIN:3"]', "moves: pin-pair has no child 'PIN:3'"),
    ('moves = ["PIN:2"]', 'moves = ["PIN:2"]\nstays = ["PIN:1"]', "say what moves (moves = [...]) or what stays"),
    ('moves = ["PIN:2"]', "", "say what moves (moves = [...]) or what stays"),
    ('stays = ["BASE PLATE:1"]', 'stays = ["PIN PAIR:1", "PIN PAIR:1/PIN:2"]', "lies inside another that is named"),
    ('stays = ["BASE PLATE:1"]', 'stays = ["BASE PLATE:1"]\nframe = "PIN PAIR:9"', "frame must be a child of the joint's assembly"),
    ('moves = ["PIN:2"]', 'moves = ["PIN:2"]\ncarried_by = "lever"', "carried_by: 'lever' is not another joint"),
    ('moves = ["PIN:2"]', 'moves = ["PIN:2"]\nspeed = 3', "joints.pin: unknown field(s) speed"),
    ("[joints.spacer]", "[joints.Spacer]", "a joint's name is lower-case letters and digits"),
    ("pin = 10.0\n\n[poses.swung]", "pin = 12.0\n\n[poses.swung]", "poses.apart: pin = 12 is outside the joint's range, 0 to 10"),
    ("swing = 90.0", "sway = 90.0", "poses.swung: 'sway' is not a joint of this file"),
    ("swing = 90.0", 'swing = "far"', "poses.swung: swing must be a number"),
])
def test_what_is_wrong_with_the_record_is_said(project_copy, old, new, words):
    assert RECORD.count(old) == 1
    (project_copy / motion.FILE).write_text(RECORD.replace(old, new), encoding="utf-8")
    wrong = motion.problems(motion.read(project_copy / motion.FILE), layout.load(project_copy))
    assert any(words in line for line in wrong), wrong


def test_a_path_reaches_into_a_sub_assembly_and_a_frame_can_be_a_child(project_copy):
    text = RECORD.replace('stays = ["BASE PLATE:1"]', 'moves = ["PIN PAIR:1/PIN:1", "PIN PAIR:2"]\nframe = "PIN PAIR:2"')
    derived, _ = derived_of(project_copy, text.replace("swing = 90.0\n", ""))
    assert sorted(i for i, chain in derived["moved"].items() if "swing" in chain) == [
        f"{PAIR_1}/PIN:1", f"{PAIR_2}/PIN:1", f"{PAIR_2}/PIN:2"]
    # the second pair's frame: its own y is the root's -z, and it stands 8 up and 15 along z
    assert near(derived["joints"]["swing"]["origin_mm"], [0.0, 8.0, 15.0])
    assert near(derived["joints"]["swing"]["direction"], [0.0, 0.0, -1.0])


def test_two_joints_that_move_the_same_thing_need_one_to_carry_the_other(project_copy):
    twice = RECORD + """
[joints.tilt]
assembly = "pin-pair"
kind = "revolute"
origin_mm = [25.0, 0.0, 0.0]
direction = [0.0, 1.0, 0.0]
range_deg = [-10.0, 10.0]
moves = ["PIN:2"]
"""
    (project_copy / motion.FILE).write_text(twice, encoding="utf-8")
    project = layout.load(project_copy)
    scene = flatten.flatten(project, "fixture-with-spacer")[0]
    data = motion.read(project_copy / motion.FILE)
    assert motion.problems(data, project) == []
    with pytest.raises(motion.MotionError, match="neither moves everything the other does"):
        motion.resolve(data, project, scene, "fixture-with-spacer", "0" * 64)
    derived, _ = derived_of(project_copy, twice + 'carried_by = "pin"\n')
    assert derived["moved"][f"{PAIR_1}/PIN:2"] == ["swing", f"pin@{PAIR_1}", f"tilt@{PAIR_1}"]
    # joints that overlap without one holding the other cannot be ordered at all
    crossed = RECORD.replace('moves = ["PIN:2"]', 'moves = ["PIN:1"]').replace(
        'stays = ["BASE PLATE:1"]', 'moves = ["PIN PAIR:1/PIN:2", "PIN PAIR:2/PIN:2"]') + """
[joints.both]
assembly = "pin-pair"
kind = "prismatic"
origin_mm = [0.0, 0.0, 0.0]
direction = [0.0, 1.0, 0.0]
range_mm = [0.0, 1.0]
stays = ["PIN:1"]
"""
    derived, _ = derived_of(project_copy, crossed)          # here swing and both move the second pins alike: the
    assert derived["moved"][f"{PAIR_1}/PIN:2"] == ["swing", f"both@{PAIR_1}"]      # outer assembly's joint carries


FOLLOWER = """
[joints.other-pin]
assembly = "pin-pair"
kind = "prismatic"
origin_mm = [-25.0, 0.0, 0.0]
direction = [1.0, 0.0, 0.0]
moves = ["PIN:1"]
follows = "pin"
ratio = -0.5
"""


def test_a_joint_that_follows_another_is_where_that_one_puts_it(project_copy):
    derived, scene = derived_of(project_copy, RECORD + FOLLOWER)
    follower = derived["joints"][f"other-pin@{PAIR_2}"]
    assert follower["follows"] == {"joint": f"pin@{PAIR_2}", "ratio": -0.5}        # the one in its own place
    assert (follower["lower"], follower["upper"]) == (-5.0, 0.0)                    # what the pin's 0 to 10 makes of it
    assert "follows" not in derived["joints"]["swing"]
    assert "other-pin" not in " ".join(derived["poses"]["apart"])                  # a pose says the joints that lead
    at = motion.values(derived, "apart")
    assert at[f"other-pin@{PAIR_1}"] == -5.0 and at[f"other-pin@{PAIR_2}"] == -5.0
    assert motion.values(derived, given={f"pin@{PAIR_1}": 4})[f"other-pin@{PAIR_1}"] == -2.0
    assert str(motion.values(derived)[f"other-pin@{PAIR_1}"]) == "0.0"              # a negative ratio leaves no -0.0
    rest = {o["id"]: o["transform_world"] for o in scene["occurrences"]}
    where = motion.placed(derived, scene, at)
    assert near(place(where[f"{PAIR_1}/PIN:1"]), [place(rest[f"{PAIR_1}/PIN:1"])[0] - 5.0, *place(rest[f"{PAIR_1}/PIN:1"])[1:]])
    with pytest.raises(motion.MotionError, match="follows pin@.*: say where that joint is"):
        motion.values(derived, given={"other-pin": 1})
    assert any("other-pin@" in line and "follows pin@" in line and "at -0.5 to one" in line for line in motion.table(derived))


@pytest.mark.parametrize("old, new, words", [
    ('follows = "pin"', 'follows = "other-pin"', "follows must name another joint of this file"),
    ('follows = "pin"', 'follows = "gear"', "follows must name another joint of this file"),
    ("ratio = -0.5", "ratio = 0", "ratio, a number that is not zero"),
    ("ratio = -0.5", "", "ratio, a number that is not zero"),
    ("ratio = -0.5", "ratio = -0.5\nrange_mm = [0.0, 1.0]", "has no range of its own"),
    ("ratio = -0.5", "ratio = -0.5\n\n[poses.both]\nother-pin = 1.0", "other-pin follows 'pin'; a pose says where that joint is"),
])
def test_what_is_wrong_with_a_joint_that_follows_is_said(project_copy, old, new, words):
    text = RECORD + FOLLOWER
    assert text.count(old) == 1
    (project_copy / motion.FILE).write_text(text.replace(old, new), encoding="utf-8")
    wrong = motion.problems(motion.read(project_copy / motion.FILE), layout.load(project_copy))
    assert any(words in line for line in wrong), wrong


def test_a_joint_cannot_follow_a_follower(project_copy):
    text = RECORD + FOLLOWER + FOLLOWER.replace("other-pin", "third").replace('follows = "pin"', 'follows = "other-pin"')
    (project_copy / motion.FILE).write_text(text, encoding="utf-8")
    wrong = motion.problems(motion.read(project_copy / motion.FILE), layout.load(project_copy))
    assert wrong == ["joints.third: follows must name another joint of this file, one that follows nothing itself"]


def test_the_layout_does_not_read_the_draft(project_copy):
    before = layout.load(project_copy).report()
    (project_copy / motion.FILE).write_text("schema_version = 7\n[joints]\nbroken = 1\n", encoding="utf-8")
    assert layout.load(project_copy).report() == before
    out = project_copy.parent / "scene"
    flatten.write(layout.load(project_copy), out, "fixture-with-spacer")
    assert not (out / motion.DERIVED).exists()


def test_the_command_checks_the_record_and_writes_beside_a_flattened_scene(project_copy, tmp_path, capsys):
    (project_copy / motion.FILE).write_text(RECORD, encoding="utf-8")
    assert main(["motion", str(project_copy), "--root", "fixture-with-spacer"]) == 0
    said = capsys.readouterr().out
    assert "swing: revolute, -90 to 90 deg, moves 4 occurrence(s); its line through [0.000, 0.000, 0.000] mm" in said
    assert f"pin@{PAIR_1}: prismatic, 0 to 10 mm, moves 1 occurrence(s), carried by swing" in said
    assert "pose apart:" in said and "a draft, not part of the layout" in said
    assert "4 joint(s) and 2 pose(s) in fixture-with-spacer; 5 of 6 occurrence(s) move" in said

    out = tmp_path / "scene"
    flatten.write(layout.load(project_copy), out, "fixture-with-spacer")
    assert main(["motion", str(project_copy), "--root", "fixture-with-spacer", "--out", str(out)]) == 0
    capsys.readouterr()
    written = json.loads((out / motion.DERIVED).read_text(encoding="utf-8"))
    assert written["schema_version"] == 1 and len(written["source"]["sha256"]) == 64
    assert written == json.loads(jsonio.dumps(derived_of(project_copy)[0]).replace("0" * 64, written["source"]["sha256"]))
    first = (out / motion.DERIVED).read_bytes()
    assert main(["motion", str(project_copy), "--root", "fixture-with-spacer", "--out", str(out)]) == 0
    assert (out / motion.DERIVED).read_bytes() == first             # the same record gives the same bytes
    capsys.readouterr()

    # a scene of another assembly, or of the project as it was, is refused
    other = tmp_path / "other"
    flatten.write(layout.load(project_copy), other, "fixture-root")
    assert main(["motion", str(project_copy), "--root", "fixture-with-spacer", "--out", str(other)]) == 1
    assert "is not the scene of fixture-with-spacer as the project stands" in capsys.readouterr().out
    assert not (other / motion.DERIVED).exists()

    (project_copy / motion.FILE).write_text(RECORD.replace("pin = 10.0\n\n", "pin = 11.0\n\n"), encoding="utf-8")
    assert main(["motion", str(project_copy), "--root", "fixture-with-spacer"]) == 1
    assert "ERROR   motion.toml: poses.apart: pin = 11 is outside the joint's range" in capsys.readouterr().out
    (project_copy / motion.FILE).unlink()
    assert main(["motion", str(project_copy)]) == 1                 # there is no file


def test_a_tool_gets_the_scene_s_motion_or_everything_that_is_wrong(project_copy):
    project = layout.load(project_copy)
    scene = flatten.flatten(project, "fixture-with-spacer")[0]
    with pytest.raises(motion.MotionError, match="a pose or a joint needs the project's motion.toml"):
        motion.of_scene(project, scene, "fixture-with-spacer")
    (project_copy / motion.FILE).write_text(RECORD.replace("swing = 90.0", "swing = 95.0").replace(
        'kind = "prismatic"', 'kind = "helical"'), encoding="utf-8")
    with pytest.raises(motion.MotionError, match="motion.toml: joints.pin: kind must be one of .*; poses.swung: swing = 95"):
        motion.of_scene(project, scene, "fixture-with-spacer")
    (project_copy / motion.FILE).write_text(RECORD, encoding="utf-8")
    derived = motion.of_scene(project, scene, "fixture-with-spacer")
    assert len(derived["source"]["sha256"]) == 64 and derived["moved"] == derived_of(project_copy)[0]["moved"]


def test_a_turn_is_rigid(project_copy):
    derived, scene = derived_of(project_copy)
    from mechanical_cad import transforms as T
    for world in motion.placed(derived, scene, {"swing": 37.0, f"pin@{PAIR_2}": 4.0, "spacer": -120.0}).values():
        T.check_matrix(world)
    assert math.isclose(sum(x * x for x in derived["joints"]["swing"]["direction"]), 1.0)
