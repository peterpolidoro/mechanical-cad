# Short forms of this repository's commands. `make` alone lists them.
#
# A command about a project repository takes it as PROJECT=/path/to/project. A project's own
# Makefile can hand its targets to this one, so that inside the project `make assemblies` is enough;
# docs/layout-specification.md, "Short commands in a project", has the lines.

GUIX      = guix shell --pure -m manifest.scm
GUIX_CAD  = guix shell --pure -m .guix/manifest-cad.scm
GUIX_BOTH = guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm
# With build123d and the OCP bindings as well, from the channel module in this repository. The first use builds
# them; the bindings are generated and compiled in the build, about thirty-five minutes on sixteen cores.
GUIX_B3D  = guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm
# With f3d, the viewer that draws a STEP file to an image without a display.
GUIX_VIEW = guix shell --pure -m manifest.scm -m .guix/manifest-view.scm
# The viewer with build123d beside it, for pictures that are cut open or coloured by part.
GUIX_VIEW_B3D = guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -m .guix/manifest-view.scm
# With PrusaSlicer beside build123d, for the file to print a part from.
GUIX_PRINT = guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -m .guix/manifest-print.scm

# The project repository, as an absolute path; a command that needs one stops without it. make divides what it
# is given at spaces, so a path that holds one is refused rather than handed on in pieces.
project = $(if $(PROJECT),$(if $(word 2,$(PROJECT)),$(error the path of the project holds a space, which make cannot hand on: $(PROJECT)),$(abspath $(PROJECT))),$(error name the project repository: make $@ PROJECT=/path/to/project))

.DEFAULT_GOAL := help
.PHONY: help test test-cad test-build123d test-view validate assemblies assembly open picture view part parts facts check fit print print-check cut take-apart section motion axes sweep

help:
	@echo "make test                        the tests that need no FreeCAD"
	@echo "make test-cad                    with FreeCAD: the assembly tools; what measures is skipped"
	@echo "make test-build123d              all the tests, with FreeCAD, the OCP bindings and build123d"
	@echo "make test-view                   the tests of the pictures, with the f3d viewer"
	@echo "make validate PROJECT=DIR        check a project repository against the layout"
	@echo "make part PROJECT=DIR KEY=K      build the authored part K from its program or its FreeCAD document"
	@echo "make parts PROJECT=DIR           build every part that has a program or a document, each after its inputs"
	@echo "make facts PROJECT=DIR           measure the parts nothing here builds: the mirrored and the supplied ones"
	@echo "make check PROJECT=DIR           evaluate the checks of every authored part against what was built"
	@echo "make fit PROJECT=DIR KEY=K SUBJECT='NAME[,NAME]'   do those children of the assembly K fit among the rest"
	@echo "make assemblies PROJECT=DIR      list the project's assemblies, and which are built"
	@echo "make assembly PROJECT=DIR        build its top-level assembly as one STEP file and one FreeCAD document"
	@echo "make assembly PROJECT=DIR KEY=K  build the assembly K of that list"
	@echo "make open PROJECT=DIR [KEY=K]    build it if need be, then open it in the FreeCAD window"
	@echo "make picture PROJECT=DIR KEY=K   pictures of a part, or of a built assembly, into PROJECT/.cache/pictures/"
	@echo "                                 [VIEWS=iso,below,+x] [UP=+Y]: where the camera stands, which axis is up"
	@echo "                                 [CUT=+y] [CUT=-x=12.5] [COLOUR=1]: cut open at the middle or at a place; each part in a colour of its own"
	@echo "                                 [FINISH=1]: each part as the project's finishes.toml says, in place of COLOUR"
	@echo "                                 [POSE=NAME] [AT='JOINT=VALUE,JOINT=VALUE']: an assembly with its joints moved (a draft, as the next three)"
	@echo "make motion PROJECT=DIR [KEY=K]  check the project's motion.toml and list its joints and poses in the assembly K"
	@echo "make axes PROJECT=DIR KEY=K [CHILD=NAME] [MIN_RADIUS=MM]   the lines round faces turn about: where a joint could be"
	@echo "make sweep PROJECT=DIR KEY=K JOINT=NAME [STEPS=13] [POSE=NAME]   walk a joint through its range: where is what it moves blocked"
	@echo "make section PROJECT=DIR KEY=K CUT=+y   what a plane cuts, as a drawing in millimetres with every part in its colour (SVG)"
	@echo "                                 [FINISH=1]: every part in the colour of its finish"
	@echo "                                 [MEASURE='across 0,0,0 40,0,12 gap; up 0,0,0 0,0,21']: dimensions between points of the model"
	@echo "                                 [HATCH=1] [BEHIND=1] [ARCS=1]: the cut faces hatched; the edges seen behind the plane, thin; circular edges as arcs"
	@echo "                                 [BEHIND=quick]: those edges found on a mesh, in seconds where the exact surfaces take minutes"
	@echo "make view PROJECT=DIR KEY=K      a viewer window on a part or a built assembly; it follows the file when it is built again"
	@echo "make print PROJECT=DIR KEY=K     the mesh to print a part from, checked against the solid and shown to a slicer"
	@echo "make print-check PROJECT=DIR KEY=K   will the part print as it stands: what is on the plate, overhangs, material that starts in mid-air"
	@echo "                                 [UP=+Z] [ANGLE=45] [STEP=0.5]: the build direction, the flattest overhang allowed, how far apart the slices are"
	@echo "                                 [BRIDGE=8]: a flat ceiling no wider than that, with a wall under both ends, is a bridge and not an overhang"
	@echo "make cut PROJECT=DIR KEY=K       the drawing to cut a plate from sheet, checked against the solid"
	@echo "                                 [KERF=0.2]: allow for a cut that wide: the outline moved outward and the holes inward by half of it"
	@echo "                                 [PATTERN=1] [ROOT=-z]: the flat pattern of a solid with flat faces instead, to cut and fold; the face laid first"
	@echo "                                 [OPEN=+z] [OPEN=+z,-y]: with PATTERN=1, the faces left out: a shell open there, a tray or half of an enclosure"
	@echo "make take-apart FILE=A.step PROJECT=NEW_DIR ORIGIN='--retrieved DAY --publishable yes --description TEXT'"
	@echo "                                 a project from one STEP file of an assembly: its products as parts, its structure as assemblies"
	@echo "Built files go to PROJECT/.cache/assemblies/. README.md has the commands these run."

test:
	$(GUIX) -- python3 -B -m pytest -q tests

test-cad:
	$(GUIX_BOTH) -- python3 -B -m pytest -q tests

test-build123d:
	$(GUIX_B3D) -- python3 -B -m pytest -q tests

test-view:
	$(GUIX_VIEW_B3D) -- python3 -B -m pytest -q tests/test_picture.py

validate:
	@$(GUIX) -- python3 -B -m mechanical_cad validate "$(project)"

# An authored part from its source (build.py with parameters.json, or part.FCStd): part.step, receipt.json, facts.json.
part:
	@$(GUIX_B3D) -- FreeCADCmd tools/build_part.py --pass "$(project)/designs/parts/$(if $(KEY),$(KEY),$(error name the part: make part PROJECT=... KEY=K))"

# Every part that is built, in the order of what each is built against (python3 -m mechanical_cad build-order).
parts:
	@for key in $$($(GUIX) -- python3 -B -m mechanical_cad build-order "$(project)" $(KEY)) ; do \
	  $(GUIX_B3D) -- FreeCADCmd tools/build_part.py --pass "$(project)/designs/parts/$$key" || exit 1; \
	done

# What nothing here builds is measured: the parts mirrored from Vault and the supplied parts.
facts:
	@$(GUIX_B3D) -- FreeCADCmd tools/step_facts.py --pass "$(project)" $(if $(KEY),-- --only $(KEY))

check:
	@$(GUIX) -- python3 -B -m mechanical_cad check "$(project)"

# Interference, contact and clearance of some children of an assembly against everything else in it.
# SUBJECT goes on whole: a child's name may hold spaces ("TANK SUPPORT FRAME:1"), and the tool divides at the commas.
fit:
	@$(GUIX_CAD) -- FreeCADCmd tools/fit_check.py --pass "$(project)" $(if $(KEY),$(KEY),$(error name the assembly: make fit PROJECT=... KEY=K SUBJECT=NAME)) \
	  $(if $(SUBJECT),-- --subjects "$(SUBJECT)",$(error name the children to check: SUBJECT='NAME[,NAME]')) \
	  $(if $(CLEARANCE),-- --clearance $(CLEARANCE))

assemblies:
	@$(GUIX) -- python3 -B -m mechanical_cad assemblies "$(project)"

# One STEP file and one FreeCAD document of an assembly; nothing is built again when they are current.
assembly:
	$(GUIX_CAD) -- FreeCADCmd tools/assembly_step.py --pass "$(project)" $(KEY)

# Build the assembly if its files are not current, then open its FreeCAD document in the FreeCAD
# window. FreeCAD stays in the foreground: the command returns when the window is closed.
# This guix shell is not --pure: the window needs the desktop's environment.
open: assembly
	@doc="$$($(GUIX) -- python3 -B -m mechanical_cad built "$(project)" $(KEY))" || exit 1; \
	echo "opening $$doc in FreeCAD"; \
	guix shell -m .guix/manifest-cad.scm -- FreeCAD "$$doc"

# A viewer window that follows the file: build the part or the assembly again and the window shows the new one.
# Not --pure, like open: the window needs the desktop's environment. The command returns when the window is closed.
view:
	@file="$$($(GUIX) -- python3 -B tools/picture.py "$(project)" $(if $(KEY),$(KEY),$(error name the component: make view PROJECT=... KEY=K)) --where)" || { echo "$$file"; exit 1; }; \
	echo "viewing $$file; it is read again whenever it changes"; \
	guix shell -m .guix/manifest-view.scm -- f3d --watch $(if $(UP),--up=$(UP),--up=+Z) "$$file"

# The file to print a part from, into PROJECT/.cache/print/ (tools/print_file.py).
print:
	@$(GUIX_PRINT) -- python3 -B tools/print_file.py "$(project)" $(if $(KEY),$(KEY),$(error name the part: make print PROJECT=... KEY=K)) \
	  $(if $(DEFLECTION),--deflection $(DEFLECTION))

# Whether a part prints as it lies in its own frame: the plate, overhangs and islands, into PROJECT/.cache/print/
# (tools/print_check.py). FreeCAD alone.
print-check:
	@$(GUIX_CAD) -- FreeCADCmd tools/print_check.py --pass "$(project)" $(if $(KEY),$(KEY),$(error name the part: make print-check PROJECT=... KEY=K)) \
	  $(if $(UP),-- --up $(UP)) $(if $(ANGLE),-- --angle $(ANGLE)) $(if $(STEP),-- --step $(STEP)) $(if $(BRIDGE),-- --bridge $(BRIDGE))

# A project from one STEP file of an assembly (tools/take_apart.py): every product with geometry a supplied
# part, every product made of others an assembly. PROJECT is a new directory; ORIGIN holds the options that
# say where the file came from, as for add-supplied.
take-apart:
	@$(GUIX_B3D) -- python3 -B tools/take_apart.py "$(abspath $(if $(FILE),$(FILE),$(error name the file: make take-apart FILE=A.step PROJECT=NEW_DIR ORIGIN='...')))" "$(project)" $(ORIGIN)

# The file to cut a plate from sheet, into PROJECT/.cache/cut/ (tools/cut_file.py). With PATTERN=1, the flat
# pattern of a part that is a convex solid with flat faces: its outline to cut and its fold lines. KERF is the
# width of the cut to allow for round a plate; OPEN names the faces a pattern leaves out.
cut:
	@$(GUIX_B3D) -- python3 -B tools/cut_file.py "$(project)" $(if $(KEY),$(KEY),$(error name the part: make cut PROJECT=... KEY=K)) \
	  $(if $(PATTERN),--pattern) $(if $(ROOT),--root $(ROOT)) $(if $(OPEN),--open $(OPEN)) $(if $(KERF),--kerf $(KERF))

# What a plane cuts of a part or an assembly, as a drawing to scale, into PROJECT/.cache/pictures/ (tools/section.py).
section:
	@$(GUIX_B3D) -- python3 -B tools/section.py "$(project)" $(if $(KEY),$(KEY),$(error name the component: make section PROJECT=... KEY=K CUT=+y)) \
	  $(if $(CUT),--cut $(CUT),$(error name the plane: CUT=+y for the middle seen from +Y, CUT=-x=12.5 for X = 12.5 seen from -X)) $(if $(UP),--up $(UP)) \
	  $(if $(FINISH),--finish) $(if $(MEASURE),--measure "$(MEASURE)") $(if $(HATCH),--hatch) $(if $(BEHIND),--behind$(if $(filter quick,$(BEHIND)), --quick)) $(if $(ARCS),--arcs)

# Pictures of a part or of a built assembly, made without a window (tools/picture.py).
picture:
	@$(if $(CUT)$(COLOUR)$(FINISH)$(POSE)$(AT),$(GUIX_VIEW_B3D),$(GUIX_VIEW)) -- python3 -B tools/picture.py "$(project)" $(if $(KEY),$(KEY),$(error name the component: make picture PROJECT=... KEY=K)) \
	  $(if $(VIEWS),--views $(VIEWS)) $(if $(UP),--up $(UP)) $(if $(CUT),--cut $(CUT)) $(if $(COLOUR),--colour) $(if $(FINISH),--finish) \
	  $(if $(POSE),--pose $(POSE)) $(if $(AT),--at "$(AT)")

# A draft that the layout does not know yet (mechanical_cad/motion.py): the joints and poses of PROJECT/motion.toml.
# `motion` checks the file and lists what it says of an assembly; `axes` lists the lines round faces turn about,
# where a joint could be; `sweep` walks a joint through its range and says where what it moves is blocked.
# CHILD and JOINT go on whole: a name may hold spaces.
motion:
	@$(GUIX) -- python3 -B -m mechanical_cad motion "$(project)" $(if $(KEY),--root $(KEY))

axes:
	@$(GUIX_CAD) -- FreeCADCmd tools/axes.py --pass "$(project)" $(if $(KEY),$(KEY),$(error name the assembly or the part: make axes PROJECT=... KEY=K)) \
	  $(if $(CHILD),-- --child "$(CHILD)") $(if $(MIN_RADIUS),-- --min-radius $(MIN_RADIUS)) $(if $(TOP),-- --top $(TOP))

sweep:
	@$(GUIX_CAD) -- FreeCADCmd tools/sweep_check.py --pass "$(project)" $(if $(KEY),$(KEY),$(error name the assembly: make sweep PROJECT=... KEY=K JOINT=NAME)) \
	  $(if $(JOINT),-- --joint "$(JOINT)",$(error name the joint to walk: JOINT=NAME)) \
	  $(if $(STEPS),-- --steps $(STEPS)) $(if $(POSE),-- --pose $(POSE)) $(if $(AT),-- --at "$(AT)") $(if $(CLEARANCE),-- --clearance $(CLEARANCE))
