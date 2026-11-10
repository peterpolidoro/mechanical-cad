(use-modules (guix profiles))
;; CAD role: FreeCAD (OpenCASCADE) for the kernel-backed tools under tools/
;; (step_facts.py, build_part.py) and for regenerating the layout fixture.
(specifications->manifest '("python" "git" "freecad"))
