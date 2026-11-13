;;; Copyright © 2026 Howard Hughes Medical Institute
;;;
;;; This file is free software; you can redistribute it and/or modify it
;;; under the terms of the GNU General Public License as published by
;;; the Free Software Foundation; either version 3 of the License, or (at
;;; your option) any later version.
;;;
;;; It is distributed in the hope that it will be useful, but
;;; WITHOUT ANY WARRANTY; without even the implied warranty of
;;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;;; GNU General Public License for more details.

;;; Packages for writing CAD parts as programs: the OCP bindings of
;;; OpenCASCADE, build123d, and what build123d needs that Guix does not have.
;;; They are written the way Guix's own package modules are, so that they can
;;; be submitted there.
;;;
;;; Without the channel:  guix build -L .guix/modules python-build123d
;;;                       guix shell -L .guix/modules python python-build123d

(define-module (orb-weaver mechanical-cad packages)
  #:use-module (guix build-system cmake)
  #:use-module (guix build-system copy)
  #:use-module (guix build-system pyproject)
  #:use-module (guix download)
  #:use-module (guix gexp)
  #:use-module (guix git-download)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (guix packages)
  #:use-module (guix utils)
  #:use-module (gnu packages check)
  #:use-module (gnu packages compression)
  #:use-module (gnu packages engineering)
  #:use-module (gnu packages fontutils)
  #:use-module (gnu packages gl)
  #:use-module (gnu packages image-processing)
  #:use-module (gnu packages machine-learning)
  #:use-module (gnu packages maths)
  #:use-module (gnu packages mpi)
  #:use-module (gnu packages pretty-print)
  #:use-module (gnu packages python)
  #:use-module (gnu packages python-build)
  #:use-module (gnu packages python-science)
  #:use-module (gnu packages python-web)
  #:use-module (gnu packages python-xyz)
  #:use-module (gnu packages web)
  #:use-module (gnu packages xorg))

;; What the check phase runs: a box, its volume, a STEP file written and read
;; back.  It fails when the bindings do not fit the OpenCASCADE they are
;; linked with (a symbol that is not there shows at import).
(define %python-ocp-check
  "\
import os, tempfile
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.STEPControl import STEPControl_Reader, STEPControl_StepModelType, STEPControl_Writer

def volume(shape):
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, properties)
    return properties.Mass()

box = BRepPrimAPI_MakeBox(1.0, 2.0, 3.0).Shape()
assert abs(volume(box) - 6.0) < 1e-9, volume(box)
path = os.path.join(tempfile.mkdtemp(), 'box.step')
writer = STEPControl_Writer()
writer.Transfer(box, STEPControl_StepModelType.STEPControl_AsIs)
assert writer.Write(path) == IFSelect_ReturnStatus.IFSelect_RetDone
reader = STEPControl_Reader()
assert reader.ReadFile(path) == IFSelect_ReturnStatus.IFSelect_RetDone
reader.TransferRoots()
assert abs(volume(reader.OneShape()) - 6.0) < 1e-6, volume(reader.OneShape())
print('OCP: a box of volume 6 went through a STEP file')
")

(define-public python-ocp
  (package
    (name "python-ocp")
    ;; The first three numbers are the OpenCASCADE release the bindings were
    ;; generated for; it has to be the one of 'opencascade-occt'.
    (version "7.9.3.1")
    (source
     (origin
       (method url-fetch)
       ;; The bindings as upstream's pywrap generated them, and the type
       ;; stubs.  TODO: generate them in the build, from OCP's Git repository
       ;; and the headers of 'opencascade-occt' (pywrap needs libclang).
       (uri (string-append "https://github.com/CadQuery/OCP/releases/download/"
                           version "/OCP_src_stubs_Linux.zip"))
       (file-name (string-append name "-" version "-generated-sources.zip"))
       (sha256
        (base32 "03n0kbbgi29zahdlcdrw0s27hdmr2kfliwgv4k09cjnp3fwcspic"))))
    (build-system cmake-build-system)
    (arguments
     (list
      #:configure-flags
      #~(list (string-append "-DPYTHON_SP_DIR=" #$output "/lib/python"
                             #$(version-major+minor
                                (package-version (this-package-input "python")))
                             "/site-packages"))
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'find-mpi
            ;; Guix's VTK is built with MPI.  Its imported target VTK::mpi
            ;; names MPI::MPI_C, and CMake refuses to generate when that
            ;; target does not exist, whether or not it is linked.
            (lambda _
              (substitute* "CMakeLists.txt"
                (("find_package\\( VTK REQUIRED" all)
                 (string-append "find_package( MPI REQUIRED COMPONENTS C )\n"
                                all)))))
          (delete 'check)
          (add-after 'install 'install-stubs
            (lambda _
              (let ((site (string-append
                           #$output "/lib/python"
                           #$(version-major+minor
                              (package-version (this-package-input "python")))
                           "/site-packages")))
                (copy-recursively "../OCP_src_stubs_Linux/OCP-stubs"
                                  (string-append site "/OCP-stubs"))
                ;; The name and version under which PyPI has these bindings,
                ;; for packages that declare them as a requirement.
                (let ((dist-info (string-append site "/cadquery_ocp-"
                                                #$version ".dist-info")))
                  (mkdir-p dist-info)
                  (call-with-output-file (string-append dist-info "/METADATA")
                    (lambda (port)
                      (format port "Metadata-Version: 2.1~%Name: cadquery-ocp~%Version: ~a~%"
                              #$version)))))))
          (add-after 'install-stubs 'check
            (lambda* (#:key tests? #:allow-other-keys)
              (when tests?
                (setenv "PYTHONPATH"
                        (string-append
                         #$output "/lib/python"
                         #$(version-major+minor
                            (package-version (this-package-input "python")))
                         "/site-packages"))
                (invoke "python3" "-c" #$%python-ocp-check)))))))
    (native-inputs (list unzip))
    (inputs
     (list fmt
           ;; VTK's CMake files look for these when its rendering and
           ;; FreeType modules are asked for.
           freetype
           glew
           libx11
           mesa
           openmpi
           opencascade-occt
           pybind11-2
           python
           rapidjson           ;OpenCASCADE's glTF headers include it
           vtk
           zlib))
    (home-page "https://github.com/CadQuery/OCP")
    (synopsis "Python bindings of the OpenCASCADE geometry kernel")
    (description
     "OCP is a Python module that wraps the C++ classes of OpenCASCADE
Technology with pybind11: boundary-representation solids and surfaces, the
modelling algorithms, and the reading and writing of STEP, IGES, BREP and glTF
files.  The bindings are generated from the kernel's headers.  CadQuery and
build123d are built on them.")
    ;; The bindings are under ASL 2.0; the generated sources carry text of
    ;; OpenCASCADE's headers, LGPL 2.1 with its exception for header files.
    (license (list license:asl2.0 license:lgpl2.1))))


;;;
;;; What build123d needs.
;;;

(define-public python-trianglesolver
  (package
    (name "python-trianglesolver")
    (version "1.2")
    (source
     (origin
       (method url-fetch)
       (uri (pypi-uri "trianglesolver" version))
       (sha256
        (base32 "1skalxcqa9p3b7ccqqlp64kgyv7hx9dfdcw98gbc1mbrwnnqmwaa"))))
    (build-system pyproject-build-system)
    (arguments (list #:tests? #f))      ;the release has no tests
    (native-inputs (list python-setuptools))
    (home-page "https://pypi.org/project/trianglesolver/")
    (synopsis "Find all the sides and angles of a triangle")
    (description
     "This module finds the sides and angles of a triangle from any three of
them that determine it, with the law of sines and the law of cosines.")
    (license license:expat)))

(define-public python-svgpathtools
  (package
    (name "python-svgpathtools")
    (version "1.8.0")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/mathandy/svgpathtools")
             (commit (string-append "v" version))))
       (file-name (git-file-name name version))
       (sha256
        (base32 "01zc9qs92dxcbq4xcpwx2qizffbb5wsg9d5sn4j0bml5aifj7swv"))))
    (build-system pyproject-build-system)
    (native-inputs (list python-pytest python-setuptools))
    (propagated-inputs (list python-numpy python-scipy python-svgwrite))
    (home-page "https://github.com/mathandy/svgpathtools")
    (synopsis "Manipulate and analyze SVG path objects and Bezier curves")
    (description
     "This package reads, writes and displays SVG files, and computes with
their paths: lines, arcs and Bezier curves with their tangents, curvature,
lengths, intersections, offsets and bounding boxes.")
    (license license:expat)))

(define-public python-ocpsvg
  (package
    (name "python-ocpsvg")
    (version "0.6.0")              ;the last release for OCP 7.9
    (source
     (origin
       (method url-fetch)
       (uri (pypi-uri "ocpsvg" version))
       (sha256
        (base32 "0fa0nlhw7a83pf0jcspxmaw6mm26azd9npirclsws3n9ghsa93gh"))))
    (build-system pyproject-build-system)
    (arguments
     (list
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'name-the-bindings
            ;; PyPI has the bindings under several names.
            (lambda _
              (substitute* "pyproject.toml"
                (("cadquery[-_]ocp[-_](proxy|novtk)") "cadquery-ocp")))))))
    (native-inputs (list python-pytest python-setuptools python-setuptools-scm))
    (propagated-inputs (list python-ocp python-svgelements))
    (home-page "https://github.com/snoyer/ocpsvg")
    (synopsis "Convert between SVG paths and OpenCASCADE wires and faces")
    (description
     "This package turns the paths and shapes of an SVG document into edges,
wires and faces of OpenCASCADE through the OCP bindings, and back.")
    (license license:asl2.0)))

(define-public python-ocp-gordon
  (package
    (name "python-ocp-gordon")
    (version "0.2.2")              ;the last release for OCP 7.9
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/gongfan99/ocp_gordon")
             (commit (string-append "v" version))))
       (file-name (git-file-name name version))
       (sha256
        (base32 "1vq120gf0m08yjbi54x5h89zibs59hnvhy8inkdvdx1qn3zm1i0m"))))
    (build-system pyproject-build-system)
    (arguments
     (list
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'name-the-bindings
            (lambda _
              (substitute* "pyproject.toml"
                (("cadquery[-_]ocp[-_](proxy|novtk)") "cadquery-ocp")))))))
    (native-inputs (list python-pytest python-setuptools python-setuptools-scm))
    (propagated-inputs (list python-numpy python-ocp python-scipy))
    (home-page "https://github.com/gongfan99/ocp_gordon")
    (synopsis "Gordon surfaces through a network of B-spline curves")
    (description
     "This package interpolates a surface through a network of profile and
guide curves, a Gordon surface, with OpenCASCADE through the OCP bindings.")
    (license license:asl2.0)))

(define-public python-dataclasses-json
  (package
    (name "python-dataclasses-json")
    (version "0.6.7")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/lidatong/dataclasses-json")
             (commit (string-append "v" version))))
       (file-name (git-file-name name version))
       (sha256
        (base32 "18yyfxm87vi1kpdinki68yfl3w5kmbxfsylc6r87n25zjvmd6zq0"))))
    (build-system pyproject-build-system)
    ;; TODO: the tests need mypy and hypothesis.
    (arguments (list #:tests? #f))
    (native-inputs
     (list python-poetry-core python-poetry-dynamic-versioning))
    (propagated-inputs (list python-marshmallow-3 python-typing-inspect))
    (home-page "https://github.com/lidatong/dataclasses-json")
    (synopsis "Encode and decode dataclasses to and from JSON")
    (description
     "This package gives a dataclass methods that write it as JSON and read
it back, with nested dataclasses, collections, optional fields and enums.")
    (license license:expat)))

(define-public python-pygltflib
  (package
    (name "python-pygltflib")
    (version "1.16.5")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://gitlab.com/dodgyville/pygltflib")
             (commit (string-append "v" version))))
       (file-name (git-file-name name version))
       (sha256
        (base32 "1pm2qbbrwn15l01a1qprs30c449w7zkgmxgy2q62plm5pyacwxyx"))))
    (build-system pyproject-build-system)
    ;; The tests read the Khronos sample models, which are not in the
    ;; repository.
    (arguments (list #:tests? #f))
    (native-inputs (list python-setuptools))
    (propagated-inputs (list python-dataclasses-json python-deprecated))
    (home-page "https://gitlab.com/dodgyville/pygltflib")
    (synopsis "Read and write glTF 2.0 files")
    (description
     "This package reads, writes and converts 3D scenes in the glTF 2.0
format, as JSON with separate buffers and as binary GLB.")
    (license license:expat)))

(define-public python-threejs-materials
  (package
    (name "python-threejs-materials")
    (version "1.2.5")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/bernhard-42/threejs-materials")
             (commit (string-append "v" version))))
       (file-name (git-file-name name version))
       (sha256
        (base32 "1prbv8ai608wnqv444r82ra6s1wjjygaww506p0462fvhh9v6lpk"))))
    (build-system pyproject-build-system)
    (arguments
     (list
      ;; This file tests the conversion from MaterialX, an optional
      ;; dependency that Guix does not have.
      #:test-flags #~(list "--ignore=tests/test_convert.py")
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'relax-requirements
            (lambda _
              (substitute* "pyproject.toml"
                (("platformdirs >= 4\\.9\\.6") "platformdirs >= 4.3"))))
          (add-before 'check 'set-home
            (lambda _ (setenv "HOME" "/tmp"))))))
    (native-inputs (list python-pytest python-setuptools))
    (propagated-inputs
     (list python-numpy python-pillow python-platformdirs python-pygltflib
           python-requests))
    (home-page "https://github.com/bernhard-42/threejs-materials")
    (synopsis "Physically based materials as three.js material definitions")
    (description
     "This package converts physically based material descriptions from
several sources into the JSON of a three.js @code{MeshPhysicalMaterial}, and
puts such materials into glTF files.")
    (license license:asl2.0)))

(define-public python-bd-materials
  (package
    (name "python-bd-materials")
    (version "0.2.6")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/bernhard-42/bd_materials")
             (commit (string-append "v" version))))
       (file-name (git-file-name name version))
       (sha256
        (base32 "1jp30c1kk964akmjv9hqbs6rk84x7d6bhc0swscyx14qsrjldq77"))))
    (build-system pyproject-build-system)
    (arguments
     (list
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'relax-requirements
            (lambda _
              (substitute* "pyproject.toml"
                (("webcolors~=24\\.8\\.0") "webcolors>=24.8.0")
                (("pytest==[0-9.]+") "pytest"))))
          (add-before 'check 'set-home
            (lambda _ (setenv "HOME" "/tmp"))))))
    (native-inputs (list python-pytest python-setuptools))
    (propagated-inputs (list python-threejs-materials python-webcolors))
    (home-page "https://github.com/bernhard-42/bd_materials")
    (synopsis "Engineering materials with physical and visual properties")
    (description
     "This package is a catalogue of engineering materials for CAD models:
density and other physical properties, and the appearance of each finish as a
physically based material.")
    (license license:asl2.0)))

(define-public python-lib3mf
  (package
    (name "python-lib3mf")
    (version (package-version lib3mf))
    (source (package-source lib3mf))
    (build-system copy-build-system)
    (arguments
     (list
      #:install-plan
      #~'(("Autogenerated/Bindings/Python/Lib3MF.py"
           #$(string-append "lib/python"
                            (version-major+minor (package-version python))
                            "/site-packages/lib3mf/")))
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'fix-binding
            ;; The generated binding of this release names an enumeration
            ;; value None, which Python 3 refuses.  Later releases name it
            ;; as below.
            (lambda _
              (substitute* "Autogenerated/Bindings/Python/Lib3MF.py"
                (("^\tNone = 0") "\tBeamLatticeBallModeNone = 0"))))
          (add-after 'install 'install-package
            ;; The layout of PyPI's "lib3mf": the generated binding, the
            ;; library beside it, where the binding's users look for it, and
            ;; a function that loads it.
            (lambda* (#:key inputs #:allow-other-keys)
              (let* ((site (string-append
                            #$output "/lib/python"
                            #$(version-major+minor (package-version python))
                            "/site-packages"))
                     (dist-info (string-append site "/lib3mf-" #$version
                                               ".dist-info")))
                (symlink (search-input-file inputs "lib/lib3mf.so")
                         (string-append site "/lib3mf/lib3mf.so"))
                (call-with-output-file (string-append site "/lib3mf/__init__.py")
                  (lambda (port)
                    (display "\
import os

from .Lib3MF import *


def get_library_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib3mf.so')


def get_wrapper():
    return Wrapper(get_library_path()[:-len('.so')])
" port)))
                (mkdir-p dist-info)
                (call-with-output-file (string-append dist-info "/METADATA")
                  (lambda (port)
                    (format port "Metadata-Version: 2.1~%Name: lib3mf~%Version: ~a~%"
                            #$version)))))))))
    (inputs (list lib3mf))
    (home-page (package-home-page lib3mf))
    (synopsis "Python binding of lib3mf")
    (description
     "This package is the Python binding of lib3mf, the library that reads
and writes files in the 3D Manufacturing Format, laid out as the package
@code{lib3mf} of PyPI is: the module @code{lib3mf.Lib3MF} and the function
@code{lib3mf.get_wrapper}.")
    (license (package-license lib3mf))))

;;;
;;; build123d.
;;;

(define-public python-build123d
  (package
    (name "python-build123d")
    ;; The last release for OpenCASCADE 7.9; 0.13.0 needs 8.0.
    (version "0.12.0")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/gumyr/build123d")
             (commit (string-append "v" version))))
       (file-name (git-file-name name version))
       (sha256
        (base32 "0855dkn0zdbr892g093hqlgkf5ssv07rs0ny9hfq1xxzmnhv3dv3"))))
    (build-system pyproject-build-system)
    (arguments
     (list
      #:test-flags
      #~(list "--ignore=tests/test_benchmarks.py"
              ;; The set-up of these tests downloads a model.
              "--deselect=tests/test_importers.py::ImportSTEP"
              ;; This one wants lib3mf 2.3.1; Guix has 2.2.0.
              "--deselect=tests/test_mesher.py::TestProperties::test_version")
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'relax-requirements
            (lambda _
              (substitute* "pyproject.toml"
                ;; Guix has one build of the bindings, with VTK.
                (("cadquery-ocp-novtk") "cadquery-ocp")
                ;; Guix's python-anytree 2.13.0 gives its version as 0.0.0.
                (("anytree >= 2\\.8\\.0, < 3") "anytree")
                (("typing_extensions >= 4\\.16\\.0") "typing_extensions >= 4.15")
                (("webcolors ~= 24\\.8\\.0") "webcolors >= 24.8.0")
                ;; The binding of Guix's lib3mf, whatever the platform.
                (("\"lib3mf >= 2\\.4\\.1;[^\"]*\"") "\"lib3mf\"")
                ((".*py-lib3mf.*") ""))))
          (add-after 'unpack 'name-the-data-files
            ;; Upstream's wheels take the font and the script from the files
            ;; Git tracks; a checkout without its repository has to name
            ;; them.
            (lambda _
              (let ((port (open-file "pyproject.toml" "a")))
                (display "
[tool.setuptools.package-data]
build123d = [\"*.js\", \"data/fonts/*/*\"]
" port)
                (close-port port))))
          (add-after 'unpack 'use-sentinel-of-typing-extensions-4.15
            ;; typing_extensions 4.16 has this class as "sentinel"; Guix has
            ;; 4.15, where it is "Sentinel".
            (lambda _
              (substitute* "src/build123d/exporters.py"
                (("from typing_extensions import Self, sentinel")
                 "from typing_extensions import Self, Sentinel as sentinel"))))
          (add-before 'check 'set-home
            (lambda _ (setenv "HOME" "/tmp"))))))
    (native-inputs
     (list python-pytest python-setuptools python-setuptools-scm))
    (propagated-inputs
     (list python-anytree
           python-bd-materials
           python-ezdxf
           python-fonttools
           python-ipython
           python-lib3mf
           python-numpy
           python-ocp
           python-ocp-gordon
           python-ocpsvg
           python-requests
           python-scikit-learn
           python-scipy
           python-svgpathtools
           python-sympy
           python-threejs-materials
           python-trianglesolver
           python-typing-extensions
           python-webcolors))
    (home-page "https://github.com/gumyr/build123d")
    (synopsis "Write parametric CAD models as Python programs")
    (description
     "build123d is a framework for boundary-representation CAD in Python,
built on the OpenCASCADE kernel through the OCP bindings.  Lines, sketches and
solids are ordinary Python objects that are combined with operators or inside
builder contexts, selected with filters and sorts, and written as STEP, BREP,
STL, 3MF, glTF, DXF and SVG files.")
    (license license:asl2.0)))
