# Adding a part to a project

How a person or an agent adds a part to a project repository that follows
[the layout](layout-specification.md), and how to tell that it is right. The
commands are the short ones of a project's Makefile ("Short commands in a
project" there); each runs a tool of this repository in a Guix environment.

## 1. Choose a key and a source

A part lives in `designs/parts/<key>/`. The key is lower-case letters, digits
and single hyphens, and no other component of the project has it. The part
has **one source**:

- **A program**: `build.py` with `parameters.json`. `build.py` defines
  `build(parameters)`, which returns the solid and touches no file. Write it
  with build123d, or with FreeCAD's `Part` module. Numbers go into
  `parameters.json`, each with where it comes from; a `name` there is the
  part's display name.
- **A drawing**: `part.FCStd`, a document drawn in FreeCAD (`make open`
  starts FreeCAD; any FreeCAD of the same version does). The part is the one
  object in it that has a solid and that nothing else in the document uses: a
  body, or the last feature of a chain. Leave no second solid lying beside
  it.
- **A file from outside**: a supplier's model, or the model of a circuit
  board from its own repository. It is not built; a command puts it in and
  records where it came from:

  ```sh
  python3 -m mechanical_cad add-supplied . <key> path/to/file.step --name "Monitor arm" \
      --supplier McMaster-Carr --part-number 5537T879 --retrieved 2026-11-16 --publishable yes
  python3 -m mechanical_cad add-supplied . <key> ../board/docs/generated/3d/board-assembled.step --name "The board" \
      --repository https://github.com/OWNER/board --commit b58cd3f --path docs/generated/3d/board-assembled.step \
      --retrieved 2026-11-17 --licence CC-BY-SA-4.0 --publishable yes
  FreeCADCmd tools/step_facts.py --pass . -- --only <key>      # measure it
  ```

  The file is kept as it came, with only its header rewritten. A newer file
  of the same part goes over the old one with `--replace`.

**A part built against another.** A program may take other parts of the
project as inputs: name them in `parameters.json`,
`"inputs": {"board": "<key of the board>"}`, and write
`build(parameters, inputs)`. `inputs["board"].build123d()` (or `.shape()` for
FreeCAD's Part module) is that part's solid, `.interface` what it states of
itself, `.facts` its measurements. Cut the board out of a block, put a
standoff under each of its holes. Build the input first; when it changes, the
validator says which parts are to be built again.

Add a `README.md` that says what the part is for and where its numbers come
from.

## 2. Say what it must satisfy

`checks.json` beside the source:

```json
{"schema_version": 1, "checks": [
  {"id": "one-solid", "fact": "solids", "equals": 1},
  {"id": "outer-size", "fact": "extent_mm", "equals": [30.0, 20.0, 5.0], "tolerance": 0.001},
  {"id": "hole", "point": [15.0, 10.0, 2.5], "is": "empty"},
  {"id": "plate-beside-the-hole", "point": [22.0, 10.0, 2.5], "is": "material"}
]}
```

A check names a fact of the whole part (count of solids, volume, extent,
bounding box) or a point of it, in the part's own frame and in millimetres,
that has to be `material` or `empty`. Points are how an interface is stated:
a hole where a pattern has one, a face at a given depth (material just under
it, empty just above). Keep a point clear of every surface.

What other parts are designed to goes into `interface.json`: the holes, the
faces, the ports and the volumes to keep clear, each with a name
([the layout](layout-specification.md), "The interface of a part"). A part
built against this one reads it, and the build holds it to the solid: a hole
stated where there is material fails.

## 3. Build it, and look at it

```sh
make part KEY=<key>                 # writes part.step, receipt.json, facts.json; fails when a check fails
make picture KEY=<key> UP=+Z        # images in .cache/pictures/; VIEWS=iso,below,+x says where the camera stands
make picture KEY=<key> CUT=+y VIEWS=+y   # cut open at the middle, seen from the side that was taken away
make check                          # every authored part's checks, without a kernel
make validate                       # the whole project against the layout
```

**Look at the pictures.** A shape can pass every check and be wrong in a way
only a picture shows. The three files the build writes are never edited.
After any change to the source, build again: a drawing saved again counts as
changed even when nothing in it did.

## 4. Place it and see whether it fits

An authored assembly, `designs/assemblies/<key>/assembly.json`, places
components of the project, mirrored and authored alike, each with a name and
a 4 x 4 transform in the assembly's frame and unit:

```json
{"schema_version": 1, "key": "with-my-part", "name": "The machine with my part", "length_unit": "mm",
 "frame": {"handedness": "right", "up_axis": "+Y"},
 "children": [
   {"name": "MACHINE:1", "component": "<key of the mirrored root assembly>", "kind": "assembly",
    "transform": [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]},
   {"name": "MY PART:1", "component": "<key>", "kind": "part",
    "transform": [[1,0,0,100.0],[0,1,0,250.0],[0,0,1,-40.0],[0,0,0,1]]}]}
```

```sh
make fit KEY=with-my-part SUBJECT='MY PART:1'     # what interferes, what touches, what is closer than 5 mm
make assembly KEY=with-my-part                    # one STEP file and one FreeCAD document of it
make picture KEY=with-my-part                     # pictures of that file
make picture KEY=with-my-part COLOUR=1 CUT=-x=12.5   # every part in a colour of its own, cut open at X = 12.5
make open KEY=with-my-part                        # the FreeCAD window, for a person
```

`make fit` reports a contact without judging it: parts that are bolted
together touch. An interference is a fault.

```sh
make section KEY=with-my-part CUT=+y              # what the plane cuts, as a drawing to scale (SVG), with a legend
```

A section is a drawing in millimetres of what lies in one plane, every part
in its colour: the thing to send to someone who has to judge a shape, and to
measure in or add dimensions to. Its record beside it has the area the plane
cuts of each part. It carries how wide and how high all that is cut is; any
other dimension is asked for between two points of the model:

```sh
make section KEY=with-my-part CUT=+y MEASURE='across 0,0,0 40,0,12 gap; up 0,0,0 0,0,21 depth'
```

`across` is how far apart the two points are from left to right on the
sheet, `up` from bottom to top, and two points alone the straight distance;
the words after them are written beside the number.

```sh
make section KEY=with-my-part CUT=+y HATCH=1 BEHIND=1   # the cut faces hatched, and the edges seen behind the plane
```

`HATCH=1` hatches the cut faces, parts side by side differently, so that
the drawing reads without its colours. `BEHIND=1` adds in thin lines what
is seen behind the plane. For a part that takes no time; for an assembly of
many parts give `BEHIND=quick`, which finds the edges on a mesh in seconds
where the exact surfaces take minutes or do not end. `ARCS=1` writes
circular edges as arcs, for a drawing program.

A picture that is cut or coloured is put together from the parts' files and
the placements, so the assembly need not be built for it; it needs
build123d beside the viewer, which `make picture` sees to. `CUT=+y` takes
away what lies beyond the middle towards +Y, `CUT=-x=12.5` what is below
X = 12.5. In grey, parts that touch cannot be told apart; in colour, and cut
open, what sits in what shows at once.

**What the part looks like** is said in one file for the whole project,
`finishes.toml` at its top: a finish with a name, a colour and, where it
matters, how much of a metal, how rough and how see-through it is, and under
`[parts]` the line `<key> = "<finish>"`
([the specification](layout-specification.md#finishes) has the fields).
Then:

```sh
make picture KEY=with-my-part FINISH=1            # every part as its finish says; one without is drawn plain
make section KEY=with-my-part CUT=+y FINISH=1     # the section filled in the finishes' colours
```

`COLOUR=1` tells parts apart; `FINISH=1` shows what the thing looks like. A
new part without a row in the file takes the file's `default`, or is pointed
out by `make validate` when there is none.

**When something moves** (a draft; the layout does not know it yet, and
[joints-and-poses-draft.md](joints-and-poses-draft.md) says what it is):
the project's `motion.toml` says which children of an assembly turn about a
line or slide along one, how far, and names positions.

```sh
make axes KEY=with-my-part CHILD='MY PART:1'      # the lines its round faces turn about: the numbers for a joint
make motion KEY=with-my-part                      # check motion.toml and list its joints and poses
make sweep KEY=with-my-part JOINT=hinge           # walk the joint through its range: where is what it moves blocked
make picture KEY=with-my-part POSE=open COLOUR=1  # pictures with the joints where the pose puts them
```

`make sweep` is `make fit` at every step of a joint's range. What already
overlaps as the assembly stands (a thread in its hole) is measured first and
not held against the motion.

## 5. The file to make it from

A part is made from a file that is derived from its STEP file and checked
against it. Both go to the project's ignored `.cache/`:

```sh
make print KEY=<key>      # a printed part: .cache/print/<key>.stl, closed, the solid's volume, shown to a slicer
make cut KEY=<key>        # a plate cut from sheet: .cache/cut/<key>.dxf, closed loops, the area of the solid's face
```

`make cut` takes a part that is a plate cut square through, two flat faces
and nothing between them but what stands square to them, and writes the
outline of one face with its holes, in millimetres and in the part's own X
and Y where the plate lies in them. A part with a pocket, a chamfer or a
leaning wall is refused: it is not made in one pass. Round corners and the
round ends of slots are arcs in the file; an ellipse or a spline in the
outline is refused.

```sh
make cut KEY=<key> KERF=0.2       # the same, allowing for a cut 0.2 mm wide
```

A cut takes away a strip as wide as the beam or the tool. With `KERF` the
outline is moved outward and every hole inward by half that width, so that
the part comes out at its size; the drawing is held to the solid's face
moved by as much, and the record says the allowance. A hole or a slot that
is not wider than the cut closes, and the drawing is refused. A sharp
corner that points into the material comes out round with half the width;
the record counts those.

```sh
make cut KEY=<key> PATTERN=1      # a solid with flat faces, unfolded: .cache/cut/<key>.pattern.dxf, cut and fold lines
```

With `PATTERN=1` the part is a convex solid with flat faces, a polyhedron
of the library, a box or a prism, and the drawing is its flat pattern: the
outline to cut on one layer and the fold lines on another, with every
fold's angle in the record. `ROOT=+x` names the face that is laid first.
Nothing is allowed for the sheet's thickness or a bend's radius, and there
are no tabs.

```sh
make cut KEY=<key> PATTERN=1 OPEN=+z      # the same solid without the face towards +z: a shell open there
```

Folded sheet makes a shell, not a solid. `OPEN` names the faces to leave
out by the axes they face squarely (`OPEN=+z,-y` for two): a box without
its top is the pattern of a tray, and the solid that half of an enclosure
fills, without the face in which the halves meet, is the pattern of that
half (`Polyhedron.clipped` cuts a solid of the library at a plane). The
part stays the closed solid. The edges round an opening are cut once and
are its rim; a shell open below needs another face laid first
(`OPEN=-z ROOT=+z`). The pattern is still that of a surface: the sheet's
thickness, the radius of a bend, flanges and tabs are not in it.

**A tool is a part built against the part it makes.** A forming plug, a
drilling jig or a fixture names the part as its input and takes its shape
from that part's solid, so no dimension is typed twice and the tool is
reported stale when the part changes. For a formed part the tool is the
space inside it (a block less the part, the piece on the axis), enlarged by
what the material shrinks. Hold each step to a volume worked out another way.
One thing to know there: build123d's `scale` enlarges a shape about the
origin it had before it was moved, so enlarge first and move afterwards.

## 6. Commit

The source, `README.md`, `checks.json` and the three built files go in
together. What is under `.cache/` is derived and ignored.
