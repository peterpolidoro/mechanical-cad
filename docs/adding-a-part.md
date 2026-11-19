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
cuts of each part.

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
leaning wall is refused: it is not made in one pass.

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
