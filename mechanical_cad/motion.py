"""A draft, not part of the layout: how the things of a project move, as joints and named poses.

Proposed to Peter on 2026-11-19 and not decided (docs/joints-and-poses-draft.md
says what and why). Until he decides, the validator does not read the file, the
flatten step does not write what is derived from it, and
docs/layout-specification.md does not describe it; the commands that use it
say that it is a draft.

`motion.toml`, at the top of a project repository, is one hand-edited file for
the whole project, as `finishes.toml` is, and optional:

    schema_version = 1

    [joints.lever]
    assembly = "lever-unit"             # the assembly whose children it joins
    kind = "revolute"                   # turns about a line; or "prismatic": slides along one
    origin_mm = [-12.7, 78.15, 0.0]     # a point on that line, in the assembly's own frame, in millimetres
    direction = [0.0, 0.0, 1.0]         # along it; a positive turn is right-handed about it
    range_deg = [-15.0, 15.0]           # how far it goes either way from where CAD assembled it, which is 0
    moves = ["LEVER:1", "GEARS:1/DRIVEN GEAR:1"]    # the children that move, by name; a path reaches into a
                                        # sub-assembly. Everything else of the assembly stands still.

    [joints.slide]
    assembly = "lever-unit"
    kind = "prismatic"
    origin_mm = [0.0, 0.0, 0.0]
    direction = [1.0, 0.0, 0.0]
    range_mm = [-6.5, 6.5]
    stays = ["STAGE:1/BASE:1", "PLATE:1"]           # in place of `moves`: everything of the assembly moves but these
    frame = "STAGE:1"                   # optional: origin and direction are in this child's frame, not the assembly's
    note = "the stage's travel by its data sheet"   # optional

    [joints.pinion]                     # a joint that another one drives, as a gear is driven by the gear it meshes with
    assembly = "lever-unit"
    kind = "revolute"
    origin_mm = [-12.7, 43.4, 0.0]
    direction = [0.0, 0.0, 1.0]
    moves = ["GEARS:1/DRIVING GEAR:1"]
    follows = "lever"                   # it has no range of its own: it is where the lever puts it
    ratio = -2.5                        # how far it goes for one degree (or millimetre) of the joint it follows;
                                        # gears that mesh turn against each other, so theirs is negative

    [poses.pressed]                     # a pose names joints and where each is; a joint it leaves out is at 0
    lever = 12.0
    slide = -3.0

A joint is said once, of an assembly, and holds wherever that assembly is
placed. One joint may carry another: the slide above moves the lever with
everything else, and the lever's line moves with it. Which carries which
follows from what each moves (the one that moves more carries the one that
moves less of the same things); two joints that move exactly the same things
need `carried_by = "NAME"` on the one that is carried.

A joint says how things can move and nothing else: nothing here knows of
forces or of what stops a motion, and of gears only the ratio that `follows`
is told. Whether something is in the way is what `tools/sweep_check.py`
measures.

Nothing here needs a CAD kernel. `problems` checks the file against a project;
`resolve` turns it into what a flattened scene needs (`motion.json`, beside
`scene.json`: every joint as a line in the scene's own frame, every occurrence
that moves with the joints that move it, outermost first); `placed` and
`posed` say where everything is at given joint values.
"""
from __future__ import annotations

import math
import re
import tomllib

from . import stepfile
from . import transforms as T

FILE = "motion.toml"
DERIVED = "motion.json"
SCHEMA_VERSION = 1
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP = {"schema_version", "joints", "poses"}
FIELDS = {"assembly", "kind", "origin_mm", "direction", "range_deg", "range_mm", "moves", "stays", "frame",
          "carried_by", "follows", "ratio", "note"}
KINDS = {"revolute": ("range_deg", "deg"), "prismatic": ("range_mm", "mm")}
FULL_TURN_DEG = 360.0
LIMIT_TOL = 1e-9


class MotionError(ValueError):
    pass


def read(path):
    """The file as it is written. Raises MotionError when it is not TOML."""
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise MotionError(str(exc)) from None


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _vec3(v):
    return isinstance(v, list) and len(v) == 3 and all(_number(x) for x in v)


def _names(path):
    return path.split("/")


def _end_of(project, key, path):
    """The component a path of child names leads to from the assembly `key`, or None when it leads nowhere."""
    comp = project.components.get(key)
    for name in _names(path):
        if comp is None or comp.kind != "assembly":
            return None
        child = next((c for c in comp.children if c.name == name), None)
        comp = project.components.get(child.component) if child is not None else None
    return comp


def _under(a, b):
    """Is the path a the path b, or below it?"""
    return a == b or a.startswith(b + "/")


def problems(data, project):
    """What is wrong with the file, as a list of sentences; empty when nothing is. `project` is a loaded project
    (mechanical_cad/layout.py): the assemblies and their children are what the paths are held against."""
    wrong = []
    extra = sorted(set(data) - TOP)
    if extra:
        wrong.append(f"unknown field(s) {', '.join(extra)}")
    if data.get("schema_version") != SCHEMA_VERSION or isinstance(data.get("schema_version"), bool):
        wrong.append(f"schema_version must be {SCHEMA_VERSION}")
    joints = data.get("joints", {})
    if not isinstance(joints, dict):
        wrong.append("joints must be a table of named joints: [joints.NAME]")
        joints = {}
    ranges = {}
    for name in sorted(joints):
        where = f"joints.{name}"
        spec = joints[name]
        if not NAME.match(name):
            wrong.append(f"{where}: a joint's name is lower-case letters and digits in groups joined by single hyphens")
        if not isinstance(spec, dict):
            wrong.append(f"{where}: expected a table")
            continue
        extra = sorted(set(spec) - FIELDS)
        if extra:
            wrong.append(f"{where}: unknown field(s) {', '.join(extra)}")
        key = spec.get("assembly")
        comp = project.components.get(key) if isinstance(key, str) else None
        if comp is None or comp.kind != "assembly":
            wrong.append(f"{where}: assembly must be the key of an assembly of this project, not {key!r}")
        kind = spec.get("kind")
        if "follows" in spec or "ratio" in spec:
            leader = joints.get(spec.get("follows")) if isinstance(spec.get("follows"), str) else None
            if spec.get("follows") == name or not isinstance(leader, dict) or "follows" in leader:
                wrong.append(f"{where}: follows must name another joint of this file, one that follows nothing itself")
            if not _number(spec.get("ratio")) or spec["ratio"] == 0:
                wrong.append(f"{where}: a joint that follows another says how far it goes for one unit of that "
                             "joint: ratio, a number that is not zero")
            if "range_deg" in spec or "range_mm" in spec:
                wrong.append(f"{where}: a joint that follows another has no range of its own")
            if kind not in KINDS:
                wrong.append(f"{where}: kind must be one of {', '.join(sorted(KINDS))}")
        elif kind not in KINDS:
            wrong.append(f"{where}: kind must be one of {', '.join(sorted(KINDS))}")
        else:
            field, other = KINDS[kind][0], KINDS[next(k for k in KINDS if k != kind)][0]
            span = spec.get(field)
            if other in spec:
                wrong.append(f"{where}: a {kind} joint has {field}, not {other}")
            if not (isinstance(span, list) and len(span) == 2 and all(_number(x) for x in span) and span[0] < span[1]):
                wrong.append(f"{where}: {field} must be [lower, upper], two numbers with the lower one first")
            elif kind == "revolute" and not (-FULL_TURN_DEG <= span[0] and span[1] <= FULL_TURN_DEG):
                wrong.append(f"{where}: range_deg must lie within one turn either way, -360 to 360")
            else:
                ranges[name] = (float(span[0]), float(span[1]))
        if not _vec3(spec.get("origin_mm")):
            wrong.append(f"{where}: origin_mm must be three numbers, a point on the joint's line in millimetres")
        direction = spec.get("direction")
        if not _vec3(direction) or math.sqrt(sum(x * x for x in direction)) < 1e-9:
            wrong.append(f"{where}: direction must be three numbers that are not all zero")
        given = [f for f in ("moves", "stays") if f in spec]
        if len(given) != 1:
            wrong.append(f"{where}: say what moves (moves = [...]) or what stays (stays = [...]), one of the two")
        for field in given:
            paths = spec[field]
            if not (isinstance(paths, list) and paths and all(isinstance(p, str) and p for p in paths)):
                wrong.append(f"{where}: {field} must be a list of children's names, with at least one")
                continue
            for p in sorted(set(paths)):
                if comp is not None and comp.kind == "assembly" and _end_of(project, key, p) is None:
                    wrong.append(f"{where}: {field}: {key} has no child {p!r}")
            for a in sorted(set(paths)):
                if paths.count(a) > 1 or any(a != b and _under(a, b) for b in paths):
                    wrong.append(f"{where}: {field}: {a!r} is named twice, or lies inside another that is named")
        frame = spec.get("frame")
        if "frame" in spec and not (isinstance(frame, str) and frame and comp is not None and comp.kind == "assembly"
                                    and _end_of(project, key, frame) is not None):
            wrong.append(f"{where}: frame must be a child of the joint's assembly, not {frame!r}")
        if "carried_by" in spec and (spec["carried_by"] not in joints or spec["carried_by"] == name):
            wrong.append(f"{where}: carried_by: {spec['carried_by']!r} is not another joint of this file")
        if "note" in spec and not (isinstance(spec["note"], str) and spec["note"]):
            wrong.append(f"{where}: note must be a non-empty string")
    poses = data.get("poses", {})
    if not isinstance(poses, dict):
        wrong.append("poses must be a table of named poses: [poses.NAME] with JOINT = VALUE")
        poses = {}
    for name in sorted(poses):
        where = f"poses.{name}"
        if not NAME.match(name):
            wrong.append(f"{where}: a pose's name is lower-case letters and digits in groups joined by single hyphens")
        if not isinstance(poses[name], dict):
            wrong.append(f"{where}: expected a table of joints and values")
            continue
        for joint in sorted(poses[name]):
            value = poses[name][joint]
            if joint not in joints:
                wrong.append(f"{where}: {joint!r} is not a joint of this file")
            elif isinstance(joints[joint], dict) and "follows" in joints[joint]:
                wrong.append(f"{where}: {joint} follows {joints[joint]['follows']!r}; a pose says where that joint is")
            elif not _number(value):
                wrong.append(f"{where}: {joint} must be a number")
            elif joint in ranges and not ranges[joint][0] - LIMIT_TOL <= value <= ranges[joint][1] + LIMIT_TOL:
                wrong.append(f"{where}: {joint} = {value:g} is outside the joint's range, "
                             f"{ranges[joint][0]:g} to {ranges[joint][1]:g}")
    return wrong


# ------------------------------------------------------------------ in a scene

def _apply(m, p):
    return [m[r][0] * p[0] + m[r][1] * p[1] + m[r][2] * p[2] + m[r][3] for r in range(3)]


def _turn(m, v):
    return [m[r][0] * v[0] + m[r][1] * v[1] + m[r][2] * v[2] for r in range(3)]


def _nodes(project, scene, top_key):
    """{the id of every assembly the scene places, and "root": (the assembly's key, where its frame is in the
    scene)}. A scene names an assembly by its document, not by its key, so the keys are found by walking the
    project along the names."""
    out = {"root": (top_key, T.identity())}
    for record in scene["assemblies"]:              # a parent comes before its children
        if record["id"] == "root":
            continue
        parent_key, parent_world = out[record["parent_id"]]
        name = record["id"] if record["parent_id"] == "root" else record["id"][len(record["parent_id"]) + 1:]
        child = next(c for c in project.components[parent_key].children if c.name == name)
        out[record["id"]] = (child.component, T.multiply(parent_world, record["transform"]))
    return out


def _below(node, path):
    return path if node == "root" else f"{node}/{path}"


def resolve(data, project, scene, top_key, source_sha256):
    """What whoever moves the scene is told: `motion.json`, beside `scene.json`.

    `data` is the file, already found right by `problems`; `scene` the flattened scene of the assembly
    `top_key`. Every joint becomes a line in the scene's own frame (the frame `transform_world` is in), at the
    position the scene is flattened in, which is every joint's zero. A joint of an assembly that the scene
    places several times is there once for each place, named NAME@WHERE with the id of that place; a joint
    of an assembly the scene does not hold is left out. `moved` names every occurrence that moves with the
    joints that move it, outermost first. A joint that follows another says which, and how far it goes for
    one unit of it; its limits are what that joint's limits make of it. Raises MotionError when two joints
    move the same occurrence and neither carries the other, and when a joint follows one that the scene does
    not hold beside it.
    """
    nodes = _nodes(project, scene, top_key)
    occurrences = {o["id"]: o for o in scene["occurrences"]}
    joints, moves, record_of, node_of = {}, {}, {}, {}
    for name in sorted(data.get("joints", {})):
        spec = data["joints"][name]
        places = sorted(node for node, (key, _) in nodes.items() if key == spec["assembly"])
        for node in places:
            scene_name = name if len(places) == 1 else f"{name}@{node}"
            world = nodes[node][1]
            if "frame" in spec:
                at = _below(node, spec["frame"])
                if at in occurrences:
                    world = occurrences[at]["transform_world"]
                elif at in nodes:
                    world = nodes[at][1]
                else:
                    raise MotionError(f"joints.{name}: its frame {spec['frame']!r} is not in the scene (suppressed?)")
            direction = _turn(world, [float(x) for x in spec["direction"]])
            length = math.sqrt(sum(x * x for x in direction))
            field, unit = KINDS[spec["kind"]]
            joints[scene_name] = {"kind": spec["kind"], "origin_mm": _apply(world, [float(x) for x in spec["origin_mm"]]),
                                  "direction": [x / length for x in direction], "unit": unit}
            if "follows" not in spec:
                joints[scene_name].update(lower=float(spec[field][0]), upper=float(spec[field][1]))
            inside = [i for i in occurrences if node == "root" or i.startswith(node + "/")]
            if "moves" in spec:
                named = [_below(node, p) for p in spec["moves"]]
                moves[scene_name] = {i for i in inside if any(_under(i, p) for p in named)}
            else:
                named = [_below(node, p) for p in spec["stays"]]
                moves[scene_name] = {i for i in inside if not any(_under(i, p) for p in named)}
            record_of[scene_name], node_of[scene_name] = name, node

    def carries(a, b):
        """Does the joint a carry the joint b?"""
        if moves[a] != moves[b]:
            return moves[a] > moves[b]
        if node_of[a] != node_of[b]:        # the same things, said of two assemblies: the outer assembly's carries
            return node_of[a] == "root" or node_of[b].startswith(node_of[a] + "/")
        return data["joints"][record_of[b]].get("carried_by") == record_of[a]

    for name in sorted(joints):                     # a follower, once what it follows is there to be found
        spec = data["joints"][record_of[name]]
        if "follows" not in spec:
            continue
        led = [j for j in joints if record_of[j] == spec["follows"]]
        leader = next((j for j in led if node_of[j] == node_of[name]), led[0] if len(led) == 1 else None)
        if leader is None:
            raise MotionError(f"joints.{record_of[name]}: it follows {spec['follows']}, which the scene holds "
                              + ("in several places and none of them is this joint's own" if led else "nowhere"))
        ends = sorted(float(spec["ratio"]) * joints[leader][end] for end in ("lower", "upper"))
        joints[name].update(lower=ends[0], upper=ends[1], follows={"joint": leader, "ratio": float(spec["ratio"])})

    moved = {}
    for i in sorted(occurrences):
        mine = [j for j in sorted(joints) if i in moves[j]]
        if not mine:
            continue
        above = {j: sum(carries(k, j) for k in mine) for j in mine}
        if sorted(above.values()) != list(range(len(mine))):
            pair = next((a, b) for a in mine for b in mine if a < b and not carries(a, b) and not carries(b, a))
            raise MotionError(f"the joints {pair[0]} and {pair[1]} both move {i}, and neither moves everything the "
                              "other does: one joint has to carry the other (carried_by says which, where they move "
                              "the same things)")
        moved[i] = sorted(mine, key=above.get)
    poses = {}
    for pose in sorted(data.get("poses", {})):      # of the joints that are led; a follower is where its leader puts it
        poses[pose] = {j: float(value) for j in sorted(joints) for joint, value in data["poses"][pose].items()
                       if record_of[j] == joint}
    return {"schema_version": SCHEMA_VERSION, "scene": "scene.json",
            "source": {"kind": "mechanical-cad-motion", "file": FILE, "sha256": source_sha256},
            "joints": joints, "moved": moved, "poses": poses}


def of_scene(project, scene, top_key, path=None):
    """`motion.json` for a scene, from the project's motion.toml (or the file at `path`), for a tool that moves
    what it has flattened. Raises MotionError with everything that is wrong with the file."""
    path = project.dir / FILE if path is None else path
    if not path.is_file():
        raise MotionError(f"{path} is not there: a pose or a joint needs the project's {FILE}")
    data = read(path)
    wrong = problems(data, project)
    if wrong:
        raise MotionError(f"{path.name}: " + "; ".join(wrong))
    return resolve(data, project, scene, top_key, stepfile.sha256_file(path))


def given(text):
    """What `JOINT=VALUE,JOINT=VALUE` on a command line says, as {joint: value}."""
    out = {}
    for item in filter(None, (t.strip() for t in (text or "").split(","))):
        name, _, value = item.rpartition("=")
        try:
            out[name.strip()] = float(value)
        except ValueError:
            raise MotionError(f"{item!r}: expected JOINT=VALUE with a number") from None
        if not name.strip():
            raise MotionError(f"{item!r}: expected JOINT=VALUE with a number")
    return out


def transform(joint, value):
    """What a joint of `motion.json` does to what it moves, at `value` (degrees or millimetres), as a 4x4 in
    the scene's frame: a turn about its line, right-handed, or a shift along it."""
    d = joint["direction"]
    if joint["kind"] == "prismatic":
        out = T.identity()
        for r in range(3):
            out[r][3] = d[r] * value
        return out
    angle = math.radians(value)
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = d
    rot = [[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
           [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
           [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]]
    o = joint["origin_mm"]
    out = T.identity()
    for r in range(3):
        out[r][:3] = rot[r]
        out[r][3] = o[r] - sum(rot[r][k] * o[k] for k in range(3))      # the line itself stays where it is
    return out


def values(derived, pose=None, given=None):
    """Where every joint is: 0, or what the named pose says, or what `given` ({joint: value}) says over both;
    and a joint that follows another is its ratio times where that one is, whatever else is said.
    A joint that the scene holds in several places (NAME@WHERE) may be given by its name alone, for all of them.
    Raises MotionError for a pose or a joint that is not there, for a value given to a joint that follows
    another, and for a value outside a joint's range."""
    joints = derived["joints"]
    out = {name: 0.0 for name in joints}
    if pose is not None:
        if pose not in derived["poses"]:
            raise MotionError(f"there is no pose {pose!r}; the poses: {', '.join(sorted(derived['poses'])) or 'none'}")
        out.update(derived["poses"][pose])
    for name, value in (given or {}).items():
        meant = [name] if name in joints else [j for j in joints if j.split("@", 1)[0] == name]
        if not meant:
            raise MotionError(f"there is no joint {name!r}; the joints: {', '.join(sorted(joints)) or 'none'}")
        led = [j for j in meant if "follows" in joints[j]]
        if led:
            raise MotionError(f"{led[0]} follows {joints[led[0]]['follows']['joint']}: say where that joint is")
        out.update({j: float(value) for j in meant})
    for name, joint in joints.items():
        if "follows" in joint:
            out[name] = joint["follows"]["ratio"] * out[joint["follows"]["joint"]] + 0.0     # 0, not -0
    for name, value in out.items():
        low, high = joints[name]["lower"], joints[name]["upper"]
        if not low - LIMIT_TOL <= value <= high + LIMIT_TOL and value != 0.0:
            raise MotionError(f"{name} = {value:g} {joints[name]['unit']} is outside its range, {low:g} to {high:g}")
    return out


def placed(derived, scene, at):
    """{occurrence id: where it is in the scene's frame} with the joints at `at` ({joint: value}; a joint that is
    not named is at 0): for an occurrence that joints move, what each does, outermost first, before the place
    the scene gives it; for the others that place."""
    turns = {name: transform(derived["joints"][name], value) for name, value in at.items() if value}
    out = {}
    for occurrence in scene["occurrences"]:
        world = occurrence["transform_world"]
        for name in reversed(derived["moved"].get(occurrence["id"], ())):
            if name in turns:
                world = T.multiply(turns[name], world)
        out[occurrence["id"]] = world
    return out


def posed(derived, scene, at):
    """The scene with every occurrence where the joints at `at` put it. `transform_world` alone is moved: the
    occurrences' own `transform`, their place in their parent, stays that of the assembled position."""
    where = placed(derived, scene, at)
    return dict(scene, occurrences=[dict(o, transform_world=where[o["id"]]) for o in scene["occurrences"]])


def steps(joint, count):
    """`count` values of a joint from its lower limit to its upper, both among them, evenly apart."""
    if count < 2:
        raise MotionError("a range is walked in at least two steps")
    low, high = joint["lower"], joint["upper"]
    return [low + (high - low) * n / (count - 1) for n in range(count)]


def table(derived):
    """The joints and poses of a scene as lines to print."""
    lines = []
    for name in sorted(derived["joints"]):
        j = derived["joints"][name]
        count = sum(name in chain for chain in derived["moved"].values())
        carried = sorted({chain[chain.index(name) - 1] for chain in derived["moved"].values()
                          if name in chain and chain.index(name)})
        lines.append(f"{name}: {j['kind']}, {j['lower']:g} to {j['upper']:g} {j['unit']}, moves {count} occurrence(s)"
                     + (f", carried by {', '.join(carried)}" if carried else "")
                     + (f", follows {j['follows']['joint']} at {j['follows']['ratio']:g} to one" if "follows" in j else "")
                     + "; its line through [" + ", ".join(f"{x:.3f}" for x in j["origin_mm"]) + "] mm along ["
                     + ", ".join(f"{x:.4f}" for x in j["direction"]) + "]")
    for name in sorted(derived["poses"]):
        said = derived["poses"][name]
        lines.append(f"pose {name}: " + (", ".join(f"{j} = {said[j]:g}" for j in sorted(said)) or "every joint at 0"))
    return lines
