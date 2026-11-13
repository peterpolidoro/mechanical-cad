;; Measuring and authoring role: FreeCAD as in manifest-cad.scm, and build123d
;; with the OCP bindings. What is recorded of a shape (facts.json, a receipt)
;; is measured through the bindings, and a part's build.py can be written
;; with build123d. The packages come from this repository's channel module:
;;
;;   guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm
(use-modules (guix profiles))
(specifications->manifest '("python" "git" "freecad" "python-build123d"))
