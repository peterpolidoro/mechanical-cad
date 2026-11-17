;; Printing role: PrusaSlicer, for tools/print_file.py to show a mesh to a
;; slicer. Used beside the build123d manifest, which writes the mesh:
;;
;;   guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -m .guix/manifest-print.scm -- python3 -B tools/print_file.py PROJECT KEY
(use-modules (guix profiles))
(specifications->manifest '("prusa-slicer"))
