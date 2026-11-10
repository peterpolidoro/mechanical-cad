import json

import pytest

from mechanical_cad import jsonio


def test_matrix_rows_stay_on_one_line():
    text = jsonio.dumps({"transform": [[1.0, 0.0, 0.0, 2.5], [0.0, 1.0, 0.0, 0.0]], "name": "PIN:1", "tags": []})
    assert "[1.0, 0.0, 0.0, 2.5]" in text
    assert text.endswith("}\n")
    assert json.loads(text)["transform"][0][3] == 2.5


def test_floats_round_trip_exactly():
    v = [0.1 + 0.2, 1e-17, -1.000000000000014, 6.529532470267441e-11]
    assert json.loads(jsonio.dumps({"v": v}))["v"] == v


def test_refuses_what_json_cannot_say():
    with pytest.raises(jsonio.JsonError):
        jsonio.dumps({"v": float("nan")})
    with pytest.raises(jsonio.JsonError):
        jsonio.dumps({1: "x"})
    with pytest.raises(jsonio.JsonError):
        jsonio.dumps({"v": object()})


def test_byte_order_mark_is_an_error_unless_allowed(tmp_path):
    p = tmp_path / "x.json"
    p.write_bytes(b"\xef\xbb\xbf{\"a\": 1}")
    with pytest.raises(jsonio.JsonError, match="byte-order mark"):
        jsonio.load(p)
    assert jsonio.load(p, allow_bom=True) == {"a": 1}


def test_nan_in_a_file_is_rejected(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"a": NaN}')
    with pytest.raises(jsonio.JsonError):
        jsonio.load(p)


def test_write_is_atomic_and_unicode_is_kept(tmp_path):
    p = tmp_path / "x.json"
    jsonio.write(p, {"name": "Ø10 × 30"})
    assert not (tmp_path / "x.json.tmp").exists()
    assert "Ø10 × 30" in p.read_text(encoding="utf-8")
