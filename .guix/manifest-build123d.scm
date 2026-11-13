;; Authoring role: FreeCAD as in manifest-cad.scm, and build123d with the OCP
;; bindings, so that a part's build.py can be written with either. The
;; packages come from this repository's channel module:
;;
;;   guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm
(use-modules (guix profiles))
(specifications->manifest '("python" "git" "freecad" "python-build123d"))
