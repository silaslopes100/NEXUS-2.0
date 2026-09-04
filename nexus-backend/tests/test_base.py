"""Testes das funcoes de normalizacao do legado (base.py)."""
from datetime import datetime

from batch.legacy_sync.mappers.base import BaseMapper


def test_as_int():
    assert BaseMapper.as_int(5) == 5
    assert BaseMapper.as_int("12") == 12
    assert BaseMapper.as_int("3.7") == 3
    assert BaseMapper.as_int("") is None
    assert BaseMapper.as_int(None) is None
    assert BaseMapper.as_int("abc") is None


def test_as_float():
    assert BaseMapper.as_float("10.5") == 10.5
    assert BaseMapper.as_float("10,5") == 10.5
    assert BaseMapper.as_float(None) is None
    assert BaseMapper.as_float("nao") is None


def test_parse_ts_unix():
    ts = BaseMapper.parse_ts(1700000000)
    assert ts is not None and ts.year == 2023


def test_parse_ts_strings():
    assert BaseMapper.parse_ts("2024-01-15 10:30:00") == datetime(2024, 1, 15, 10, 30)
    assert BaseMapper.parse_ts("2024-01-15") == datetime(2024, 1, 15)
    assert BaseMapper.parse_ts("15/01/2024") == datetime(2024, 1, 15)
    assert BaseMapper.parse_ts(None) is None
    assert BaseMapper.parse_ts("") is None


def test_parse_date():
    d = BaseMapper.parse_date("2024-02-29")
    assert d is not None and d.day == 29


def test_str_clean():
    assert BaseMapper.str_clean("  teste  ") == "teste"
    assert BaseMapper.str_clean(None) is None
    assert BaseMapper.str_clean("") is None
    assert BaseMapper.str_clean("NULL") is None
    assert BaseMapper.str_clean("0000-00-00 00:00:00") is None
    assert BaseMapper.str_clean("abcdef", 3) == "abc"