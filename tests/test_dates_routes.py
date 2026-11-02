import pytest

from app.filter.cities import CityIndex
from app.filter.normalize import skeleton
from tests.conftest import NOW


@pytest.mark.parametrize("text,iso", [
    ("вылет 05.11.2026", "2026-11-05"),
    ("вылет 5.11", "2026-11-05"),
    ("12 ноября лечу", "2026-11-12"),
    ("noyabryň 14 ne gidyan", "2026-11-14"),
    ("dekabr 3 gidyan", "2026-12-03"),
    ("1 января улетаю", "2027-01-01"),
    ("10 11 2026 Moskwa", "2026-11-10"),
    ("30 ne gidip baryan", "2026-10-30"),
    ("завтра лечу", "2026-10-30"),
    ("сегодня вылетаю", "2026-10-29"),
])
def test_dates(engine, text, iso):
    sk = skeleton(text)
    hits = engine.dates.extract(sk, NOW)
    assert hits and hits[0].iso == iso, hits


def test_time_and_weight_are_not_dates(engine):
    assert not engine.dates.extract(skeleton("вылет в 6.00, груз 2.5 кг"), NOW)


def test_phone_not_a_date(engine):
    r = engine.analyze("Лечу Москва-Ашхабад, документы +7 912 345-67-89", now=NOW)
    assert r.date_iso is None


@pytest.mark.parametrize("text,route,direction", [
    ("Moskwadan Ashgabada", ["moscow", "ashgabat"], "to_tm"),
    ("Ашхабад - Москва - Питер", ["ashgabat", "moscow", "spb"], "from_tm"),
    ("из Дашогуза в Москву", ["dashoguz", "moscow"], "from_tm"),
    ("Питер Ургенч Дашогуз", ["spb", "urgench", "dashoguz"], "to_tm"),
    ("Turkmenabatdan Kazana gidyan", ["turkmenabat", "kazan"], "from_tm"),
    ("Aşgabada gidýän barmy", ["ashgabat"], "to_tm"),
])
def test_route_direction(engine, text, route, direction):
    r = engine.analyze(text + " лечу документы могу взять", now=NOW)
    assert r.route == route and r.direction == direction


def test_typo_city_fuzzy(engine):
    r = engine.analyze("Лечу в Ashhabadd завтра, могу взять документы", now=NOW)
    # опечатка → нечёткое совпадение считается слабым признаком, но с намерением проходит
    assert r.gate


def test_weak_alias_needs_intent(engine):
    assert not engine.analyze("dz", now=NOW).gate
    assert engine.analyze("Завтра в дз лечу, могу взять документы", now=NOW).gate
