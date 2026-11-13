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

# The project repository, as an absolute path; a command that needs one stops without it.
project = $(if $(PROJECT),$(abspath $(PROJECT)),$(error name the project repository: make $@ PROJECT=/path/to/project))

.DEFAULT_GOAL := help
.PHONY: help test test-cad test-build123d validate assemblies assembly open

help:
	@echo "make test                        the tests that need no FreeCAD"
	@echo "make test-cad                    with FreeCAD: the assembly tools; what measures is skipped"
	@echo "make test-build123d              all the tests, with FreeCAD, the OCP bindings and build123d"
	@echo "make validate PROJECT=DIR        check a project repository against the layout"
	@echo "make assemblies PROJECT=DIR      list the project's assemblies, and which are built"
	@echo "make assembly PROJECT=DIR        build its top-level assembly as one STEP file and one FreeCAD document"
	@echo "make assembly PROJECT=DIR KEY=K  build the assembly K of that list"
	@echo "make open PROJECT=DIR [KEY=K]    build it if need be, then open it in the FreeCAD window"
	@echo "Built files go to PROJECT/.cache/assemblies/. README.md has the commands these run."

test:
	$(GUIX) -- python3 -B -m pytest -q tests

test-cad:
	$(GUIX_BOTH) -- python3 -B -m pytest -q tests

test-build123d:
	$(GUIX_B3D) -- python3 -B -m pytest -q tests

validate:
	@$(GUIX) -- python3 -B -m mechanical_cad validate "$(project)"

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
