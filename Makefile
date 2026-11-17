# Short forms of this repository's commands. `make` alone lists them.
#
# A command about a project repository takes it as PROJECT=/path/to/project. A project's own
# Makefile can hand its targets to this one, so that inside the project `make assemblies` is enough;
# docs/layout-specification.md, "Short commands in a project", has the lines.

GUIX      = guix shell --pure -m manifest.scm
GUIX_CAD  = guix shell --pure -m .guix/manifest-cad.scm
GUIX_BOTH = guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm
# With build123d and the OCP bindings as well, from the channel module in this repository. The first use builds
# them; the bindings take about twenty minutes on sixteen cores.
GUIX_B3D  = guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm
# With f3d, the viewer that draws a STEP file to an image without a display.
GUIX_VIEW = guix shell --pure -m manifest.scm -m .guix/manifest-view.scm
# With PrusaSlicer beside build123d, for the file to print a part from.
GUIX_PRINT = guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -m .guix/manifest-print.scm

# The project repository, as an absolute path; a command that needs one stops without it.
project = $(if $(PROJECT),$(abspath $(PROJECT)),$(error name the project repository: make $@ PROJECT=/path/to/project))

.DEFAULT_GOAL := help
.PHONY: help test test-cad test-build123d test-view validate assemblies assembly open picture view part parts facts check fit print

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
	@echo "make view PROJECT=DIR KEY=K      a viewer window on a part or a built assembly; it follows the file when it is built again"
	@echo "make print PROJECT=DIR KEY=K     the mesh to print a part from, checked against the solid and shown to a slicer"
	@echo "Built files go to PROJECT/.cache/assemblies/. README.md has the commands these run."

test:
	$(GUIX) -- python3 -B -m pytest -q tests

test-cad:
	$(GUIX_BOTH) -- python3 -B -m pytest -q tests

test-build123d:
	$(GUIX_B3D) -- python3 -B -m pytest -q tests

test-view:
	$(GUIX_VIEW) -- python3 -B -m pytest -q tests/test_picture.py

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
comma := ,
fit:
	@$(GUIX_CAD) -- FreeCADCmd tools/fit_check.py --pass "$(project)" $(if $(KEY),$(KEY),$(error name the assembly: make fit PROJECT=... KEY=K SUBJECT=NAME)) \
	  $(if $(SUBJECT),$(foreach s,$(subst $(comma), ,$(SUBJECT)),-- --subject "$(s)"),$(error name the children to check: SUBJECT='NAME[,NAME]')) \
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

# Pictures of a part or of a built assembly, made without a window (tools/picture.py).
picture:
	@$(GUIX_VIEW) -- python3 -B tools/picture.py "$(project)" $(if $(KEY),$(KEY),$(error name the component: make picture PROJECT=... KEY=K)) $(if $(VIEWS),--views $(VIEWS)) $(if $(UP),--up $(UP))
