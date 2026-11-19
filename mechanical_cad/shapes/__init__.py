"""Shapes for enclosures: convex polyhedra as solids, shells, frames, panels and flat patterns.

    polyhedra   the Platonic and Archimedean solids, prisms, antiprisms and boxes by their vertices; sizing
    unfold      the flat pattern of a polyhedron, with its fold lines, its cuts and the outline to cut it out along
    forms       solids, shells, frames, panels and flat patterns as shapes of build123d

`polyhedra` and `unfold` are standard-library Python. `forms` imports build123d when one of its functions is
called, so a part's `build.py` can use all three and the first two work where no kernel is installed.
"""
