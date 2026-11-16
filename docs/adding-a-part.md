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

## 3. Build it, and look at it

```sh
make part KEY=<key>                 # writes part.step, receipt.json, facts.json; fails when a check fails
make picture KEY=<key> UP=+Z        # images in .cache/pictures/; VIEWS=iso,below,+x says where the camera stands
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
make open KEY=with-my-part                        # the FreeCAD window, for a person
```

`make fit` reports a contact without judging it: parts that are bolted
together touch. An interference is a fault.

## 5. Commit

The source, `README.md`, `checks.json` and the three built files go in
together. What is under `.cache/` is derived and ignored.
