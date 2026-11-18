(use-modules (guix profiles))
;; Base role: the mechanical_cad package (validator, flatten, checks) and the
;; pure-Python test suite. `make` is here for the tests that look at what the
;; Makefile's targets would run (tests/test_makefile.py); they run none of it. The FreeCAD-run scripts under tools/ use
;; .guix/manifest-cad.scm.
(specifications->manifest '("python" "python-pytest" "git" "make"))
