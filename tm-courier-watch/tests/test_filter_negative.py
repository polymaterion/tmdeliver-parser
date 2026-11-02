import pytest

from tests.conftest import NOW

NEGATIVE = [
    "Продам iPhone 14, самовывоз Москва",
    "Куплю билеты Москва - Ашхабад дешево, авиабилеты со скидкой",
    "Вакансия: требуется продавец в магазин, Санкт-Петербург, зарплата от 80000",
    "Ищу работу в Ашхабаде, опыт 3 года",
    "Сдам квартиру в Санкт-Петербурге, недорого",
    "Кто летит Москва - Сочи в пятницу? Хочу передать документы",          # нет Туркменистана
    "Лечу 5 ноября Казань - Самара, могу забрать посылки",                  # нет Туркменистана
    "Привет всем, как дела?",
    "Доброе утро, друзья! Хорошего дня",
    "Казино онлайн, ставки на спорт, заработок без вложений, Ашхабад",
    "Такси Ашхабад - Дашогуз, выезд каждый день, трансфер",
    "Оформление визы и РВП, юридические услуги, регистрация, Москва",
    "Карго Москва - Ашхабад, тариф 5 $ за кг, склад в Москве, контейнеры",
    "Mary adamlar, nahar taýýar, sargyt ediň",                              # просто упоминание Mary без поездки
    "Maria приезжает завтра, встречаем в аэропорту",                        # имя Мария ≠ Мары
    "Погода в Москве сегодня +5, ожидается дождь",
]


@pytest.mark.parametrize("text", NEGATIVE)
def test_negative(engine, text):
    r = engine.analyze(text, now=NOW)
    assert r.score < engine.thresholds["notify"], (r.score, [x.code for x in r.reasons])


def test_no_tm_gate_returns_zero(engine):
    r = engine.analyze("Кто летит Москва - Сочи? Хочу передать документы", now=NOW)
    assert r.score == 0 and not r.gate


def test_hard_exclusion(engine):
    r = engine.analyze("Казино, ставки на спорт Ашхабад Москва лечу", now=NOW)
    assert r.excluded and r.score == 0


def test_stale_date_penalty(engine):
    fresh = engine.analyze("Лечу 5.11 Москва-Ашхабад, могу взять документы", now=NOW).score
    stale = engine.analyze("Лечу 5.09.2026 Москва-Ашхабад, могу взять документы", now=NOW).score
    assert stale < fresh
