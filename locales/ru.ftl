## Русский (язык по умолчанию)
lang-name = 🇷🇺 Русский

cmd-start-desc = Начать / справка
cmd-settings-desc = Порог, уведомления, категории, язык
cmd-sources-desc = Источники (чаты)
cmd-add_source-desc = Добавить публичный чат
cmd-stats-desc = Статистика за 7 дней
cmd-export-desc = Выгрузка для улучшения фильтра (CSV)
cmd-test-desc = Проверить текст фильтром
cmd-lang-desc = Сменить язык

start-text =
    👋 Я присылаю объявления о поездках в/из Туркменистана, найденные в ваших публичных чатах.
    
    Под каждым уведомлением: «Открыть сообщение», оценка (полезно / не релевантно / дубликат) и статус контакта.
    Писать автору вы будете сами — вручную.
    
    Команды: /settings, /sources, /add_source, /stats, /export, /test, /lang

btn-profile = 👤 Профиль
btn-message = 💬 Сообщение
btn-useful = 👍 Полезно
btn-irrelevant = 👎 Не релевантно
btn-contact = 📞 Контакт: { $status }
btn-back = ⬅️ Назад
btn-thr-minus = ➖ 5
btn-thr-plus = ➕ 5
btn-lang = 🌐 Язык
mark-selected = ✅ { $label }

cat-carrier_offer = 🧳 Едет и готов взять документы/посылки
cat-sender_request = 📦 Хочет отправить — ищет попутчика
cat-receiver_request = 📥 Хочет получить/забрать посылку
cat-traveler_announce = ✈️ Объявил поездку (про посылки не сказано)
cat-unclear = ❔ Тип неясен

dir-to_tm = в Туркменистан
dir-from_tm = из Туркменистана
dir-within_tm = внутри Туркменистана
dir-unknown = направление неясно

contact-none = не начат
contact-contacted = написал
contact-replied = ответили
contact-agreed = договорились
contact-done = передано
contact-no_answer = нет ответа
contact-declined = отказ

notify-header = 🔔 <b>Новое объявление</b> · { $score }/100
notify-category = { $category }
notify-route = 🧭 <b>Маршрут:</b> { $route } ({ $direction })
notify-date = 📅 <b>Дата:</b> { $date }
notify-chat = 💬 <b>Чат:</b> { $title }
notify-reasons = 🔎 <b>Почему сработало:</b>
notify-text = ✉️ <b>Текст:</b>
notify-no-link = ⚠️ Ссылка недоступна (чат без публичного имени).

reason-geo_strong = назван Туркменистан или туркменский город
reason-geo_weak = слабый признак Туркменистана (сокращение/телефон +993)
reason-route = маршрут из { $count } пунктов
reason-date_exact = указана дата: { $date }
reason-date_day_only = указан день месяца: { $date }
reason-date_relative = срок: { $date }
reason-stale_date = дата уже в прошлом: { $date }
reason-too_long = слишком длинный текст
reason-phone = указан телефон
reason-question = вопросительная форма
reason-no_tm = нет признаков Туркменистана

settings-title =
    ⚙️ <b>Настройки</b>
    Порог уведомления: <b>{ $threshold }</b> из 100
    Уведомления: <b>{ $notifications }</b>
    Язык: { $lang }
on = включены
off = выключены
btn-toggle-notify = 🔔 Уведомления: { $state }
btn-cat = { $state } { $name }

sources-title = 📡 <b>Источники</b> ({ $count } из { $max })
sources-empty = Список пуст. Добавьте чаты в config/chats.yml или командой /add_source @username
source-line = { $state } { $title }{ $note }
source-error = { " " }— ошибка: { $error }
add-source-usage = Использование: /add_source @username (или числовой id чата). Аккаунт юзербота должен состоять в чате.
add-source-bad = Нужен @username публичного чата или числовой id (-100…) чата, в котором состоит аккаунт юзербота.
add-source-limit = Достигнут лимит источников: { $max }.
add-source-ok = ✅ Источник добавлен. Юзербот подключит его в течение минуты.
source-toggled = Готово

stats-text =
    📊 <b>За 7 дней</b>
    Найдено: { $total }
    Уведомлений отправлено: { $notified }
    Дубликатов: { $dups }
    Оценки: 👍 { $useful } · 👎 { $irrelevant }
    Контакты: написал { $contacted }, ответили { $replied }, договорились { $agreed }, передано { $done }

export-caption = Выгрузка находок и оценок (без телефонов отправителей и их идентификаторов в явном виде).
export-empty = Пока нет данных для выгрузки.

test-usage = Использование: /test текст объявления
test-result =
    🧪 <b>Проверка</b>: { $score }/100 (уровень: { $level })
    { $category }
    🧭 { $route } ({ $direction })
    📅 { $date }

fb-saved = Спасибо, оценка сохранена
contact-saved = Статус обновлён
contact-menu = Статус контакта:
lang-choose = 🌐 Выберите язык:
lang-set = Язык переключён
no-match = Запись не найдена
