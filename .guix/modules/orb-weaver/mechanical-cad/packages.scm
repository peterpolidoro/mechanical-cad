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
;;; OpenCASCADE, build123d, what build123d needs that Guix does not have, and
;;; bd_warehouse, the fasteners and other standard parts written with it.
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
  #:use-module (gnu packages cpp)
  #:use-module (gnu packages engineering)
  #:use-module (gnu packages fontutils)
  #:use-module (gnu packages gl)
  #:use-module (gnu packages image-processing)
  #:use-module (gnu packages llvm)
  #:use-module (gnu packages machine-learning)
  #:use-module (gnu packages maths)
  #:use-module (gnu packages mpi)
  #:use-module (gnu packages pretty-print)
  #:use-module (gnu packages python)
  #:use-module (gnu packages python-build)
  #:use-module (gnu packages python-science)
  #:use-module (gnu packages python-web)
  #:use-module (gnu packages python-xyz)
  #:use-module (gnu packages web))

;;;
;;; What generates the bindings.
;;;

;; 'clang-python-bindings' enters "bindings/python", where the tarball of
;; Clang 13 has the bindings; the source of the later releases is the whole of
;; LLVM, and Guix defines the bindings of Clang 13 only.  To be offered to
;; Guix as a change of that procedure and a definition beside
;; 'python-clang-13'.
(define-public python-clang-21
  (let ((base (clang-python-bindings clang-21)))
    (package
      (inherit base)
      (arguments
       (substitute-keyword-arguments (package-arguments base)
         ((#:phases phases)
          #~(modify-phases #$phases
              (replace 'change-directory
                (lambda _
                  (chdir "clang/bindings/python"))))))))))

(define-public python-pywrap
  ;; There is no release.  This is the commit that OCP 7.9.3.1 has as its
  ;; submodule.
  (let ((commit "92519409a57f9ec3f2c005b8057006fdb4752c23")
        (revision "0"))
    (package
      (name "python-pywrap")
      (version (git-version "0.1" revision commit))
      (source
       (origin
         (method git-fetch)
         (uri (git-reference
               (url "https://github.com/CadQuery/pywrap")
               (commit commit)))
         (file-name (git-file-name name version))
         (sha256
          (base32 "06xj38kgla5szkms6nvgvzsmbb4sgsy5ilhv2bfywlj0mgwbmqi9"))
         (modules '((guix build utils)))
         (snippet
          ;; The headers of an old OpenCASCADE and the symbols of its
          ;; libraries, which the generator does not need.
          #~(begin
              (delete-file-recursively "opencascade")
              (for-each delete-file
                        (find-files "." "^symbols_mangled_.*\\.dat$"))))))
      (build-system pyproject-build-system)
      (arguments (list #:tests? #f))    ;there are none
      (native-inputs (list python-setuptools))
      (propagated-inputs
       (list pybind11-2
             python-clang-21
             python-click
             python-jinja2
             python-joblib
             python-logzero
             python-pandas
             python-path
             python-pyparsing
             python-schema
             python-toml
             python-toposort
             python-tqdm))
      (home-page "https://github.com/CadQuery/pywrap")
      (synopsis "Generate pybind11 bindings of a C++ library from its headers")
      (description
       "pywrap parses the headers of a C++ library with libclang and writes
the C++ sources of a Python module that wraps its classes, functions and
enumerations with pybind11.  A TOML file says which headers make which
submodule and what to leave out or to add.  It was written for OCP, the
bindings of OpenCASCADE.")
      (license license:asl2.0))))

(define-public python-pybind11-stubgen-for-ocp
  ;; CadQuery's fork of pybind11-stubgen 0.3, which has no release.  This is
  ;; its last commit before OCP 7.9.3.1 was released.
  (let ((commit "32e111a5292e9bb9708edd3e3ede6e9d75fcbbf0")
        (revision "0"))
    (package
      (name "python-pybind11-stubgen-for-ocp")
      (version (git-version "0.3.1" revision commit))
      (source
       (origin
         (method git-fetch)
         (uri (git-reference
               (url "https://github.com/CadQuery/pybind11-stubgen")
               (commit commit)))
         (file-name (git-file-name name version))
         (sha256
          (base32 "1inj4zf8x7gbq4121sxcnjn5rzmr2fqkb6fpghdm2a2yrqfygz21"))))
      (build-system pyproject-build-system)
      (arguments (list #:tests? #f))    ;they need a module compiled for them
      (native-inputs (list python-setuptools))
      (propagated-inputs (list python-pyparsing))
      (home-page "https://github.com/CadQuery/pybind11-stubgen")
      (synopsis "Write type stubs for the Python modules that pybind11 makes")
      (description
       "This package imports a Python module made with pybind11 and writes
type stubs for it, from the signatures in its docstrings.  It is the fork of
pybind11-stubgen that the OCP bindings of OpenCASCADE are released with.")
      (license license:bsd-3))))

;;;
;;; The bindings.
;;;

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
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/CadQuery/OCP")
             (commit version)))
       (file-name (git-file-name name version))
       (sha256
        (base32 "0hd5d1km11j5in30mvcjw3x2rrwx7i3rvnqjcgppwcxk1gkp3cqz"))
       (modules '((guix build utils)))
       (snippet
        ;; A copy of OpenCASCADE's headers, in whose place the build takes
        ;; those of 'opencascade-occt', and what fetches Microsoft's
        ;; compiler to generate the bindings for Windows.
        #~(begin
            (delete-file-recursively "opencascade")
            (delete-file-recursively "extern")))))
    (build-system cmake-build-system)
    (arguments
     (list
      #:modules '((guix build cmake-build-system)
                  (guix build utils)
                  (ice-9 popen)
                  (ice-9 rdelim)
                  (srfi srfi-1))
      #:configure-flags
      #~(list (string-append "-DPYTHON_SP_DIR=" #$output "/lib/python"
                             #$(version-major+minor
                                (package-version (this-package-input "python")))
                             "/site-packages")
              ;; Without debugging symbols, which the 'strip' phase would
              ;; remove from the one file this installs.  The build type has
              ;; to stay RelWithDebInfo: the CMake files of
              ;; 'opencascade-occt' give the definitions it was compiled
              ;; with (HAVE_RAPIDJSON, OCC_CONVERT_SIGNALS and others) to
              ;; that configuration only.
              "-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O2 -DNDEBUG")
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'find-mpi
            ;; Guix's VTK is built with MPI.  Its imported target VTK::mpi
            ;; names MPI::MPI_C, and CMake refuses to generate when that
            ;; target does not exist, whether or not it is linked.
            (lambda _
              (substitute* "templates/CMakeLists.j2"
                (("find_package\\( VTK REQUIRED" all)
                 (string-append "find_package( MPI REQUIRED COMPONENTS C )\n"
                                all)))))
          (add-after 'find-mpi 'generate
            ;; What the CMakeLists.txt at the top of the repository does,
            ;; without what it does for other systems.
            (lambda* (#:key inputs native-inputs parallel-build?
                      #:allow-other-keys)
              (define (implicit-include-directories)
                ;; Where the C++ compiler looks when it is told nothing: the
                ;; headers of the inputs, of the C++ library and of the C
                ;; library.
                (let* ((port (open-pipe "c++ -E -x c++ -v /dev/null 2>&1"
                                        OPEN_READ))
                       (lines (let loop ((lines '()))
                                (let ((line (read-line port)))
                                  (if (eof-object? line)
                                      (reverse lines)
                                      (loop (cons line lines)))))))
                  (close-pipe port)
                  (map string-trim
                       (take-while
                        (lambda (line)
                          (not (string-prefix? "End of search list" line)))
                        (cdr (find-tail
                              (lambda (line)
                                (string-prefix? "#include <...>" line))
                              lines))))))

              (let ((occt #$(this-package-input "opencascade-occt")))
                ;; The headers of the library that the bindings are linked
                ;; with.
                (substitute* "ocp.toml"
                  (("\\./opencascade")
                   (string-append occt "/include/opencascade")))
                ;; The symbols that its libraries export: the generator
                ;; leaves out what the headers declare and the libraries do
                ;; not have.
                (invoke "python3" "dump_symbols.py"
                        (string-join
                         (find-files (string-append occt "/lib")
                                     "^libTK.*\\.so$")
                         ";")))
              (apply invoke "python3" "-m" "bindgen"
                     "-n" (number->string (if parallel-build?
                                              (parallel-job-count)
                                              1))
                     "-l" (search-input-file (or native-inputs inputs)
                                             "lib/libclang.so")
                     "-p" "."
                     (append
                      (append-map
                       (lambda (directory)
                         (list "-i" directory))
                       (cons* (search-input-directory
                               inputs
                               #$(string-append
                                  "include/vtk-"
                                  (version-major+minor
                                   (package-version
                                    (this-package-input "vtk")))))
                              ;; Clang's own headers, before those of GCC.
                              (search-input-directory
                               (or native-inputs inputs)
                               #$(string-append
                                  "lib/clang/"
                                  (version-major
                                   (package-version
                                    (this-package-native-input "clang")))
                                  "/include"))
                              (implicit-include-directories)))
                      (list "all" "ocp.toml" "Linux")))
              ;; What was generated is what the phases after this one build.
              (chdir "OCP")))
          (delete 'check)
          (add-after 'install 'install-stubs
            (lambda _
              (let ((site (string-append
                           #$output "/lib/python"
                           #$(version-major+minor
                              (package-version (this-package-input "python")))
                           "/site-packages")))
                ;; The type stubs, from the signatures in the docstrings
                ;; of the module that was installed.  The order of their
                ;; import statements is that of a set of strings.
                (setenv "PYTHONHASHSEED" "0")
                (setenv "PYTHONPATH" site)
                (invoke "python3" "-m" "pybind11_stubgen" "-o" site "OCP")
                (for-each (lambda (file)
                            (delete-file
                             (string-append site "/OCP-stubs/" file)))
                          '("MANIFEST.in" "setup.py"))
                ;; The address of an object in the process that wrote them.
                (substitute* (string-append site
                                            "/OCP-stubs/Aspect/__init__.pyi")
                  (("object at 0x[0-9a-f]+") "object at 0x0"))
                ;; The name and version under which PyPI has these bindings,
                ;; for packages that declare them as a requirement.
                (let ((dist-info (string-append site "/cadquery_ocp-"
                                                #$version ".dist-info")))
                  (mkdir-p dist-info)
                  (call-with-output-file (string-append dist-info "/METADATA")
                    (lambda (port)
                      (format port
                              "Metadata-Version: 2.1~%Name: cadquery-ocp~%Version: ~a~%"
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
    (native-inputs
     (list clang-21
           pybind11-2
           python-lief                  ;for dump_symbols.py
           python-pybind11-stubgen-for-ocp
           python-pywrap))
    (inputs
     (list fmt
           freetype    ;VTK's CMake files look for it with its FreeType module
           mesa        ;OpenCASCADE's OpenGl headers include <GL/gl.h>
           openmpi     ;see the 'find-mpi' phase
           opencascade-occt
           python
           rapidjson   ;OpenCASCADE's glTF headers include it
           vtk))
    (home-page "https://github.com/CadQuery/OCP")
    (synopsis "Python bindings of the OpenCASCADE geometry kernel")
    (description
     "OCP is a Python module that wraps the C++ classes of OpenCASCADE
Technology with pybind11: boundary-representation solids and surfaces, the
modelling algorithms, and the reading and writing of STEP, IGES, BREP and glTF
files.  The bindings are generated from the kernel's headers.  CadQuery and
build123d are built on them.")
    ;; The bindings are under ASL 2.0; what is generated carries text of
    ;; OpenCASCADE's headers, LGPL 2.1 with its exception for header files.
    (license (list license:asl2.0 license:lgpl2.1))))


;;;
;;; What build123d needs.
;;;

;; To be offered to Guix as a change of 'python-anytree' itself: the phase
;; below, added to its phases.  It is not exported, so that the name
;; "python-anytree" goes on meaning one package.
(define python-anytree-with-version
  (package
    (inherit python-anytree)
    (arguments
     (substitute-keyword-arguments (package-arguments python-anytree)
       ((#:phases phases)
        #~(modify-phases #$phases
            (add-before 'build 'set-version-for-pdm-backend
              ;; pdm-backend takes the version from the tags of the Git
              ;; repository, which a checkout does not have, and falls back
              ;; on the 0.0.0 that pyproject.toml gives for that case; what
              ;; requires a version of anytree then finds it too old.  The
              ;; 'set-version' phase of the build system hands the version
              ;; to setuptools-scm, hatch-vcs, pbr, versioneer and
              ;; poetry-dynamic-versioning, and not yet to this backend.
              (lambda _
                (setenv "PDM_BUILD_SCM_VERSION"
                        #$(package-version python-anytree))))))))))

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
    (arguments
     (list
      ;; This file imports mypy for its one test, which upstream skips.
      #:test-flags #~(list "--ignore=tests/test_annotations.py")))
    (native-inputs
     (list python-hypothesis
           python-poetry-core
           python-poetry-dynamic-versioning
           python-pytest))
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
    (arguments
     (list
      #:test-flags
      ;; These read the sample models of the Khronos Group, which upstream
      ;; clones beside the tests: an archived repository of 1.9 GiB, each
      ;; model under a licence of its own.
      #~(cons "test_pygltflib.py"
              (map (lambda (test)
                     (string-append "--deselect=test_pygltflib.py::" test))
                   '("TestBufferConversions::test_buffer_conversions_binfile"
                     "TestBufferConversions::test_buffer_conversions_realworld"
                     "TestBuffers"
                     "TestConversion"
                     "TestConvertImages::test_export_image_to_file_bufferview_zero"
                     "TestConvertImages::test_from_binaryblob_to_datauri"
                     "TestExtensions::test_load_mesh_primitive_extensions"
                     "TestExtensions::test_save_mesh_primitive_extensions"
                     "TestExtensions::test_save_mesh_primitive_extensions_glb"
                     "TestIO"
                     "TestOutput::test_animated_triangle"
                     "TestOutput::test_avocado"
                     "TestOutput::test_box"
                     "TestValidator")))))
    (native-inputs (list python-pytest python-setuptools))
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

;; To be offered to Guix as an update of 'lib3mf' itself.
(define-public lib3mf-2.5
  (package
    (inherit lib3mf)
    (version "2.5.0")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/3MFConsortium/lib3mf")
             (commit (string-append "v" version))))
       (file-name (git-file-name "lib3mf" version))
       (sha256
        (base32 "0xxwc5nz168if8amw28nsx7n743s7dx59pr98wysfsyy9gd3sbzi"))
       (modules '((guix build utils)))
       (snippet
        #~(begin
            ;; Delete pre-compiled ACT.
            (for-each delete-file
                      (find-files "AutomaticComponentToolkit" "^act\\."))

            ;; Remove bundled software.  Preserve cpp-base64 as it has been
            ;; modified and cannot easily be unbundled.
            (for-each delete-file-recursively
                      '("Libraries/fast_float"
                        "Libraries/googletest"
                        "Libraries/libressl"
                        "Libraries/libzip"
                        "Libraries/zlib"))

            ;; Link the tests with the system's googletest instead of
            ;; compiling the bundled one into them.
            (substitute* "Tests/CPP_Bindings/CMakeLists.txt"
              (("\\$\\{PROJECT_NAME\\} \\$\\{OPENSSL_LIBRARIES\\}" all)
               (string-append all " gtest")))))))
    (arguments
     (list
      #:configure-flags
      #~(list "-DUSE_INCLUDED_ZLIB=0"
              "-DUSE_INCLUDED_LIBZIP=0"
              "-DUSE_INCLUDED_SSL=0"
              "-DUSE_INCLUDED_FASTFLOAT=0")))
    ;; This release comes with the sources that ACT generated, a later ACT
    ;; than Guix has, and does not run ACT in the build.  TODO: generate
    ;; them; ACT 1.6.0 writes other sources from the same description.
    (native-inputs
     (modify-inputs (package-native-inputs lib3mf)
       (delete "automatic-component-toolkit")))
    ;; The library makes its identifiers itself unless it is asked to use
    ;; libuuid, in this release and in the one before.
    (inputs
     (modify-inputs (package-inputs lib3mf)
       (delete "util-linux")
       (append fast-float)))))

(define-public python-lib3mf
  (package
    (name "python-lib3mf")
    (version (package-version lib3mf-2.5))
    (source (package-source lib3mf-2.5))
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
    (inputs (list lib3mf-2.5))
    (home-page (package-home-page lib3mf-2.5))
    (synopsis "Python binding of lib3mf")
    (description
     "This package is the Python binding of lib3mf, the library that reads
and writes files in the 3D Manufacturing Format, laid out as the package
@code{lib3mf} of PyPI is: the module @code{lib3mf.Lib3MF} and the function
@code{lib3mf.get_wrapper}.")
    (license (package-license lib3mf-2.5))))

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
              "--deselect=tests/test_importers.py::ImportSTEP")
      #:phases
      #~(modify-phases %standard-phases
          (add-after 'unpack 'relax-requirements
            (lambda _
              (substitute* "pyproject.toml"
                ;; Guix has one build of the bindings, with VTK.
                (("cadquery-ocp-novtk") "cadquery-ocp")
                (("typing_extensions >= 4\\.16\\.0") "typing_extensions >= 4.15")
                (("webcolors ~= 24\\.8\\.0") "webcolors >= 24.8.0")
                ;; The binding of Guix's lib3mf, whatever the platform.
                (("\"(lib3mf >= 2\\.4\\.1);[^\"]*\"" _ requirement)
                 (string-append "\"" requirement "\""))
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
     (list python-anytree-with-version
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

;;;
;;; Parts written with build123d.
;;;

(define-public python-bd-warehouse
  (package
    (name "python-bd-warehouse")
    ;; The newest release; it asks for build123d from 0.12.0 and below 0.14.0.
    (version "0.4.0")
    (source
     (origin
       (method git-fetch)
       (uri (git-reference
             (url "https://github.com/gumyr/bd_warehouse")
             (commit (string-append "v" version))))
       (file-name (git-file-name name version))
       (sha256
        (base32 "1rsr2vxycqhvbcvjj39a9a7c9n12lnkscp33l3gfxddwjqzjz8yk"))))
    (build-system pyproject-build-system)
    ;; The tests take about six minutes, more than half of that for the
    ;; threads that tests/test_thread.py models.
    (native-inputs
     (list python-pytest python-setuptools python-setuptools-scm))
    (propagated-inputs
     (list python-bd-materials python-build123d python-typing-extensions))
    (home-page "https://github.com/gumyr/bd_warehouse")
    (synopsis "Parametric fasteners, threads, bearings and gears for build123d")
    (description
     "This package is a collection of parametric parts for build123d: metric
and imperial screws, nuts, washers and heat-set inserts with the clearance,
tap, threaded and insert holes that take them, threads, bearings with their
press-fit holes, gears, sprockets, pipes and flanges, O-rings, retaining
rings, shaft keys and the rails and hardware of OpenBuilds.  The sizes are
read from tables of the standards and of suppliers that come with the
package.")
    (license license:asl2.0)))
