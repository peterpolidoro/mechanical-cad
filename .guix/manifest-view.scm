;; Viewing role: f3d, a viewer built on VTK and OpenCASCADE that reads a STEP
;; file and renders it to an image through EGL, without a display. For
;; tools/picture.py:
;;
;;   guix shell --pure -m manifest.scm -m .guix/manifest-view.scm -- python3 -B tools/picture.py PROJECT KEY
(use-modules (guix profiles))
(specifications->manifest '("python" "git" "f3d"))
