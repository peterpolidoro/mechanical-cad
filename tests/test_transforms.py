import pytest

from mechanical_cad import transforms as T


def test_identity_is_rigid():
    assert T.check_matrix(T.identity()) == T.identity()


@pytest.mark.parametrize("bad, word", [
    ([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]], "4x4"),
    ([[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "orthonormal"),
    ([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]], "reflection"),
    ([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 2]], "last row"),
    ([[1, 0, 0, "x"], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "non-numeric"),
    ([[1, 0, 0, float("nan")], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "non-finite"),
    ([[True, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "non-numeric"),
])
def test_rejects_what_is_not_rigid(bad, word):
    with pytest.raises(T.TransformError, match=word):
        T.check_matrix(bad)


def test_multiply_composes_parent_then_child():
    parent = [[0.0, -1.0, 0.0, 10.0], [1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]   # 90 deg about Z, +10 X
    child = [[1.0, 0.0, 0.0, 5.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    assert T.translation(T.multiply(parent, child)) == [10.0, 5.0, 0.0]


def test_units():
    assert T.unit_factor("cm", "mm") == 10.0
    assert T.unit_factor("in", "mm") == 25.4
    assert T.scaled_translation([[1, 0, 0, 2.5], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], 10.0)[0][3] == 25.0
    with pytest.raises(T.TransformError):
        T.unit_factor("furlong", "mm")


def test_basis_maps_native_up_to_z():
    m = T.basis_to_z_up("+Y")
    assert [sum(m[r][c] * v for c, v in enumerate([0, 1, 0])) for r in range(3)] == [0, 0, 1]
    assert T.check_matrix(m) == m
    assert T.basis_to_z_up("+Z") == T.identity()
    with pytest.raises(T.TransformError):
        T.basis_to_z_up("-X")


def test_deviation_separates_rotation_from_translation():
    a = T.identity()
    b = T.identity()
    b[0][3] = 0.5
    b[1][0] = 1e-3
    assert T.deviation(a, b) == (1e-3, 0.5)
