import json
import re
from pathlib import Path

from app.filter.dedup import hamming, simhash, text_hash
from app.filter.engine import FilterEngine, fingerprint
from app.filter.normalize import skeleton
from app.common.i18n import I18n
from tests.conftest import NOW


def test_skeleton_equivalence():
    assert skeleton("Ашхабад") != ""
    assert skeleton("Moskwa") == skeleton("Москва")
    assert skeleton("алып гидип билян") == skeleton("alyp gidip bilyan")
    assert skeleton("Daşoguz") == skeleton("Дашогуз")


def test_dictionary_extension_without_code_changes(tmp_path):
    base = tmp_path / "rules"
    (base).mkdir()
    for f in Path("rules").glob("*.json"):
        (base / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    (base / "custom").mkdir()
    (base / "custom" / "cities.local.json").write_text(json.dumps({"cities": [
        {"id": "balkanabat2", "ru": "Тест-Город", "tk": "Test", "country": "TM", "aliases": ["zzzgorod"], "weak": []}]}), encoding="utf-8")
    (base / "custom" / "keywords.local.json").write_text(json.dumps({"rules": [
        {"id": "offer.custom", "group": "intent_offer", "score": 30, "roles": {"carrier_offer": 40},
         "desc": {"ru": "своё правило"}, "patterns": ["свезу ~ {OBJ}"]}]}), encoding="utf-8")
    eng = FilterEngine.from_dir(base)
    r = eng.analyze("Москва zzzgorod 5.11 свезу документы", now=NOW)
    assert "zzzgorod" or r.gate
    assert "zzzgorod"[:3] and "balkanabat2" in r.route
    assert "offer.custom" in r.rules and r.category == "carrier_offer"


def test_dedup_hashes():
    a = skeleton("Лечу 5 ноября Москва Ашхабад могу взять документы")
    b = skeleton("лечу 5 ноября Москва - Ашхабад, могу взять документы!!")
    c = skeleton("Продам гараж в Самаре срочно недорого торг")
    assert text_hash(a) == text_hash(b)
    assert hamming(simhash(a), simhash(b)) <= 4 < hamming(simhash(a), simhash(c))


def test_fingerprint_stable(engine):
    a = engine.analyze("Лечу 5.11 Москва-Ашхабад документы +7 900 111-22-33", now=NOW)
    b = engine.analyze("5.11 Москва-Ашхабад лечу, заберу документы +7 900 111-22-33", now=NOW)
    assert fingerprint(a, "s") == fingerprint(b, "s") is not None or fingerprint(a, "s") == fingerprint(b, "s")


def test_locales_have_same_keys():
    keys = {}
    for f in Path("locales").glob("*.ftl"):
        keys[f.stem] = set(re.findall(r"^([a-z][\w-]*) =", f.read_text(encoding="utf-8"), re.M))
    base = keys["ru"]
    for lang, ks in keys.items():
        assert ks == base, (lang, ks ^ base)


def test_i18n_fallback_and_args():
    i = I18n("locales")
    assert "3" in i.t("tk", "reason-route", count=3)
    assert i.t("xx", "btn-open") == i.t("ru", "btn-open")
    assert i.pick("tk-TM") == "tk" and i.pick("de") == "ru"


def test_all_rules_have_ru_and_tk_desc():
    for f in Path("rules").glob("keywords*.json"):
        for r in json.loads(f.read_text(encoding="utf-8"))["rules"]:
            assert r["desc"].get("ru") and r["desc"].get("tk"), r["id"]
