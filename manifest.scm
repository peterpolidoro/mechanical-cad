(use-modules (guix profiles))
;; Base role: specification, validator and the pure-Python test suite.
;; Add a separate .guix/manifest-cad.scm with "freecad" when the first
;; FreeCAD-backed tool lands, as mechanical-docs does.
(specifications->manifest '("python" "python-pytest" "git"))
