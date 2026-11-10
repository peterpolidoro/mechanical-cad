(use-modules (guix profiles))
;; Base role: the mechanical_cad package (validator, flatten, checks) and the
;; pure-Python test suite. The FreeCAD-run scripts under tools/ use
;; .guix/manifest-cad.scm.
(specifications->manifest '("python" "python-pytest" "git"))
