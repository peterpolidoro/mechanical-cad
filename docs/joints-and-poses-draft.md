# Joints and poses: a draft

**Status (2026-11-19): proposed to Peter, not decided.** It is built far
enough to be tried: a record, a module that checks it, three tools that use
it, and one real assembly described with it. It is kept outside the layout
until he decides. The validator does not read the record, the flatten step
does not write what is derived from it, and
[the specification](layout-specification.md) does not mention it. "What a
yes would change" at the end says what would follow from his word, and what
a no would remove.

## What this is for

A project in this layout records where every part sits, once: the position
CAD assembled it in. That is enough to build the assembly, to draw it and to
check that nothing overlaps as it stands.

It is not enough for three things the plan asks for
([direction](direction.md), stage 7):

- a picture of a thing in another position than the assembled one, open and
  closed, pressed and released;
- a video of something moving the way it moves;
- knowing whether a part that moves runs into something on its way, which
  is what the monitor's arm in the first project needs before it is bought.

None of these can be worked out from the placements. CAD knows how its
parts are constrained, but a STEP file carries none of it and the exporter
does not write it. So it has to be said somewhere, and this draft is a
place to say it.

## The three words

**A joint** says that some children of an assembly move together against
the rest, in one of two ways: they turn about a line (a hinge, a shaft, a
pivot), or they slide along a line (a stage, a drawer). It gives the line,
and how far the motion goes either way from the assembled position, which
counts as zero. That is all a joint is. It knows nothing of forces, of what
drives the motion, or of what stops it.

**A pose** is a name for one position: `open`, `pressed`. It lists joints
and where each is. A joint it does not list is at zero.

**A view** would be a name for one picture: where the camera stands, which
pose the thing is in, whether it is cut open. Views are not built and not
proposed yet. Nothing needs them today: a picture is asked for with its
options on the command line, and a manual's views are described in the
manual's own files. They are worth a record when the same picture has to
be made again by name, in a README or a manual, and that can wait until
one does.

## The record

One hand-edited file for the whole project, `motion.toml` at its top, as
`finishes.toml` is:

```toml
schema_version = 1

[joints.lever]
assembly = "lever-unit"             # the assembly whose children it joins
kind = "revolute"                   # turns about a line; "prismatic" slides along one
origin_mm = [-12.7, 78.146, 0.0]    # a point on the line, in the assembly's own frame, in millimetres
direction = [0.0, 0.0, 1.0]         # along it; a positive turn is right-handed about it
range_deg = [-15.0, 15.0]           # how far either way from the assembled position, which is 0
moves = ["LEVER:1", "GEARS:1/DRIVEN GEAR:1"]    # the children that move, by name; a path reaches into a sub-assembly

[joints.slide]
assembly = "lever-unit"
kind = "prismatic"
origin_mm = [0.0, 0.0, 0.0]
direction = [0.0, 0.0, 1.0]
range_mm = [-6.5, 6.5]
stays = ["STAGE:1/BASE:1", "PLATE:1"]           # in place of moves: everything of the assembly moves but these

[joints.pinion]                     # a joint that another one drives
assembly = "lever-unit"
kind = "revolute"
origin_mm = [-12.7, 43.4, 0.0]
direction = [0.0, 0.0, 1.0]
moves = ["GEARS:1/DRIVING GEAR:1"]
follows = "lever"                   # it has no range of its own
ratio = -1.0                        # its turn for one degree of the lever's; meshing gears turn against each other

[poses.pressed]
lever = 12.0
slide = -3.0
```

What the fields mean, and the choices in them:

- **A joint is said of an assembly, once**, and holds wherever that assembly
  is placed. An assembly placed twice gives two joints in a scene, named
  `lever@WHERE` with the place.
- **The line is numbers**, in the frame of the joint's assembly, or with
  `frame = "CHILD"` in the frame of one of its children: a child's own
  numbers survive when the child is placed somewhere else. The numbers
  are found with `make axes` (below), not by hand.
- **Lengths are millimetres** whatever unit the assembly's manifest is in,
  and the field names say so.
- **One joint may carry another.** The slide above moves the lever with
  everything else, and the lever's line goes with it. Which carries which is
  worked out from what each moves: the joint that moves more carries the one
  that moves less of the same things. Two joints that move exactly the same
  things (a pan and a tilt) need `carried_by = "NAME"` on the inner one.
- **A joint that follows another** stands for a pair of gears, a rack, a
  belt: it has no range of its own and is always its ratio times the joint
  it follows.
- **Not there**: a joint with two freedoms as one record (a ball, a
  cylinder that turns and slides; each is two joints here), a screw whose
  turn and travel are tied, anything that closes a loop of joints, and
  flexible parts.

`mechanical_cad/motion.py` reads the file and says everything that is wrong
with it against the project: an assembly that is not one, a child that is
not there, a pose outside a joint's range. It needs no CAD kernel.

## What a scene is told

For a flattened scene the module writes `motion.json` beside `scene.json`,
as `finishes.json` is written: every joint as a line in the scene's own
frame, every occurrence that moves with the joints that move it, outermost
first, and the poses. Whoever draws the scene needs nothing else, and no
knowledge of assemblies. An occurrence is then at

    T(joint 1, value 1) · T(joint 2, value 2) · … · transform_world

with T the turn about the joint's line or the shift along it.
`mechanical-docs` reads this file: its `motion.py` writes a video of one
joint going through its range (`joint NAME`) and of the way from one pose
to another (`pose A B`), and its `docs/input-contract.md` has the file's
fields.

## The commands

In a project, with this repository's Makefile:

```sh
make axes KEY=lever-unit MIN_RADIUS=2            # the lines round faces turn about: where a joint could be
make axes KEY=lever-unit CHILD='LEVER:1'         # those of one child
make motion KEY=machine                          # check motion.toml; list its joints and poses in that assembly
make sweep KEY=machine JOINT=lever               # walk the joint through its range: where is what it moves blocked
make picture KEY=machine POSE=pressed FINISH=1   # pictures with the joints where a pose puts them
make picture KEY=machine AT='lever=12,slide=-3'  # or at values given here
python3 -m mechanical_cad motion PROJECT --root machine --out SCENE_DIR    # motion.json beside a flattened scene
```

`make axes` (`tools/axes.py`) lists every line that cylindrical and conical
faces share, with their radii and what they belong to. A joint's line is
nearly always one of them, and its numbers are copied from that list.

`make sweep` (`tools/sweep_check.py`) is the fit check over a range. It sets
the joint to thirteen values from one limit to the other, moves what the
joint moves, and compares every solid that moved with every solid that did
not, as `make fit` compares a part with its neighbours. Parts of an assembly
often overlap a little where they stand (a thread in its hole), so the
assembled position is measured first and only what is new, or has grown,
counts against a step. It then prints the stretch around zero that is free
and what blocks it at either end, found to a thirty-second of a step by
halving.

## What it found on a real assembly

The mechanical example is one STEP file of an assembly, taken apart into a
project in this checkout's ignored `tmp/dual-lever-from-step/`: two lever
units on a base plate, 37 parts, 108 occurrences. Its `motion.toml` there
was written from the geometry and the parts' names alone, by an agent.
Nobody who knows the instrument has said which parts move together.

`make axes` on one lever unit gave its three lines at once: the shaft that
carries the torque sensor, the brake, a gear, a hub and the lever; the
motor's shaft with the other gear; and the shoulder screw the whole unit
turns on. The record has four joints for the first unit: the unit turning
on the base plate, everything above the linear stage sliding with it, the
lever turning on its shaft, and the motor's gear following the lever's.
Both gears have 70 teeth, counted on a slice of each, so the ratio is -1.

Walking each joint found things nobody had written down:

| Joint | Free, from the assembled position | What ends it |
| --- | --- | --- |
| the unit on the base plate | 11.6° one way, 27.5° the other | the screw of the clamping knob reaches the end of the arc slot in the unit's plate, at both ends |
| the second unit on the base plate | 28.7° one way, 10.6° the other | the same, mirrored |
| the lever on its shaft | 10.0° one way; the other way nothing in 120°, as far as was walked | the lever's gear meets a post that stands on the motor's plate |
| the stage | 6.5 mm one way (as far as was asked), nothing the other | the stage's two halves meet at once: the micrometer's tip is one solid with the half that carries it |

So the slot allows 39.1° in all, and the unit is assembled about 8° off the
middle of it. The lever has a stop on one side and none that the solids
show on the other; the switch that may be its other end is a model of
surfaces, which the walk does not see. The stage is modelled at the end of
its travel, with a micrometer that cannot retract.

Two overlaps are there as the assembly stands and were not held against
any motion: the two gears share 4.4 mm³ where their teeth mesh, and the hub
shares 0.8 mm³ with the brake.

Whether the post is a stop, as the record has it, or rides on the gear is a
reading of the model: it is seated in the motor's plate, so it stands
still here. A child wrongly left out of a joint's `moves` would show the
same way, as something met at once.

Walking the lever takes much longer than the rest, sixteen to twenty
minutes against one to five, because its gear and the motor's are compared
with each other at every step.

Pictures of the assembly as it stands and with the unit turned to the end
of its slot and the lever against its stop are in that project's ignored
`.cache/pictures/poses/`; a video of the lever going through its range,
drawn by `mechanical-docs`, is beside them. The walks' records are in its
`.cache/sweep/`.

## What it does not do, and what is not known

- It samples. Something thinner than a step's motion can be passed through
  unseen; more steps cost more time. Walking the unit's turn, 72 solids
  against 80 at 24 positions, took four and a half minutes.
- A part without a solid is not compared. The example's switch is a model
  of surfaces, so the walk cannot say when the lever reaches it.
- What moves together is said by hand. A child left out of `moves` is seen
  as something in the way, which is how a wrong record shows itself; a child
  wrongly put in is not seen at all.
- Zero is wherever CAD left the assembly. The example's unit stands eight
  degrees off the middle of its slot, and a record written against it means
  something else after the next export if that changes.
- Nothing has been compared with the instrument itself.
- `mechanical-docs` draws a joint's video; a still at a pose through its
  renderer is not built there (this repository's `make picture` draws one).

## What a yes would change

If joints and poses become records of the layout:

1. `docs/layout-specification.md` and `docs/layout-proposal.md` get a
   section, as finishes have.
2. `python3 -m mechanical_cad validate` reads `motion.toml` and reports
   what is wrong with it, and the fixture gets one.
3. `python3 -m mechanical_cad flatten` writes `motion.json` beside the
   scene whenever the project has the record, and the separate command
   goes.
4. The word "draft" comes out of the module and the tools.

If not, `mechanical_cad/motion.py`, `tools/axes.py`,
`tools/sweep_check.py`, their tests, the options `--pose` and `--at` of
`tools/picture.py`, three Makefile targets and this document go, and
`mechanical-docs` loses `joints.py` and two kinds of video. `tools/axes.py`
is useful without the rest.

## For Peter to decide

1. **Whether joints and poses belong in the layout at all.** Recommended:
   yes, once he has tried `make sweep` on something he knows.
2. **One file for the project, or one beside each assembly.** Built as one
   file, because he chose that for finishes and the reasons are the same:
   one place to look, one file to edit. Against it: a joint belongs to one
   assembly, and if the exporter ever writes Inventor's own joints, that
   would be a machine-written file beside each `assembly.json`.
3. **The line as numbers, or as a feature.** Built as numbers that
   `make axes` finds. Naming a feature instead ("the bore of PIN:1") would
   follow a part when it changes, and costs a way to name a face that
   survives an export.
4. **Views.** Recommended: not yet.
