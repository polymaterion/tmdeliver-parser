"""Синтетические положительные примеры (НЕ взяты из массива, на котором строились словари)."""
import pytest

from tests.conftest import NOW

# (текст, ожидаемая категория, ожидаемое направление)
CASES = [
    # --- едет и берёт
    ("Салам! 3 ноября Москва-Ашгабат учýан, документ ве кичи почта алып билерин. Ватсап +79001112233", "carrier_offer", "to_tm"),
    ("Всем привет, 5.11 лечу Санкт-Петербург - Ашхабад, могу взять небольшие посылки и документы", "carrier_offer", "to_tm"),
    ("Hemma salam 7 noyabr Mary-Ashgabat-Moskwa gidip barýan, dokument alyp gidip bilyan", "carrier_offer", "from_tm"),
    ("Завтра улетаю Ашхабад - Москва, заберу документы, пишите в лс", "carrier_offer", "from_tm"),
    ("Выезжаю 2 ноября из Казани в Туркменабад, если есть документы или лёгкая почта, пишите", "carrier_offer", "to_tm"),
    ("Salam 12.11 Piter-Dasoguz baryan yenil pocta alyp gidyan, habarlasyn", "carrier_offer", "to_tm"),
    ("Приём посылок и документов: Москва-Ашхабад-Дашогуз, вылет 10 ноября", "carrier_offer", "to_tm"),
    ("Лебап-Санкт-Петербург 8 ноября лечу, возьму документы и мелкие вещи", "carrier_offer", "from_tm"),
    # --- хочет отправить / ищет попутчика
    ("Салам, на днях кто-нибудь летит из Питера в Ашхабад? Нужно передать документы", "sender_request", "to_tm"),
    ("Kim bu hepde Moskwadan Ashgabada gidyan? Dokument ugratmaly", "sender_request", "to_tm"),
    ("Есть ли кто едет Казань - Туркменабад на этой неделе? Хочу передать справку", "sender_request", "to_tm"),
    ("Ertir Asgabatdan Moskwa gidyan barmy? Pocta bar", "sender_request", "from_tm"),
    ("Ищу попутчика Санкт-Петербург - Дашогуз, нужно отправить документы срочно", "sender_request", "to_tm"),
    ("Dashoguz-Piter gaytyan bolsa habarlasayyn, dokument ugratjaktym", "sender_request", "from_tm"),
    # --- хочет получить
    ("Здравствуйте, нужно срочно забрать документы, кто летит из Ашхабада в Москву?", "receiver_request", "from_tm"),
    # --- просто поездка с маршрутом и датой
    ("Лечу Москва - Ашхабад 4 ноября", None, "to_tm"),
]


@pytest.mark.parametrize("text,cat,direction", CASES)
def test_positive(engine, text, cat, direction):
    r = engine.analyze(text, now=NOW)
    assert r.score >= engine.thresholds["notify"], (r.score, [x.code for x in r.reasons])
    if cat:
        assert r.category == cat, (r.category, r.votes)
    assert r.direction == direction, (r.direction, r.route)


def test_traveler_announce_without_parcels(engine):
    r = engine.analyze("Лечу Москва - Ашхабад 4 ноября", now=NOW)
    assert r.category == "traveler_announce"


def test_high_level_for_full_offer(engine):
    r = engine.analyze("5.11 вылетаю Москва-Ашхабад, могу взять документы и посылки. +79001112233", now=NOW)
    assert r.level == "high" and r.date_iso == "2026-11-05"
