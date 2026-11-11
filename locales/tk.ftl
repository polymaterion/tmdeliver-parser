## Türkmen dili
lang-name = 🇹🇲 Türkmençe

cmd-start-desc = Başla / kömek
cmd-settings-desc = Çäk, habarnamalar, kategoriýalar, dil
cmd-sources-desc = Çeşmeler (çatlar)
cmd-add_source-desc = Açyk çat goşmak
cmd-stats-desc = 7 günlük statistika
cmd-export-desc = Süzgüjini gowulaşdyrmak üçin CSV
cmd-test-desc = Tekste süzgüç bilen barlag
cmd-lang-desc = Dili çalyşmak

start-text =
    👋 Men açyk çatlaryňyzda tapylan Türkmenistana/Türkmenistandan ýolagçylyk bilen baglanyşykly bildirişleri iberýärin.
    
    Her habarnamanyň aşagynda: «Habary aç», baha (peýdaly / ýerliksiz / gaýtalanma) we habarlaşma ýagdaýy bar.
    Awtora özüňiz, el bilen ýazarsyňyz.
    
    Buýruklar: /settings, /sources, /add_source, /stats, /export, /test, /lang

btn-profile = 👤 Profil
btn-message = 💬 Habar
btn-useful = 👍 Peýdaly
btn-irrelevant = 👎 Ýerliksiz
btn-contact = 📞 Habarlaşma: { $status }
btn-back = ⬅️ Yza
btn-thr-minus = ➖ 5
btn-thr-plus = ➕ 5
btn-lang = 🌐 Dil
mark-selected = ✅ { $label }

cat-carrier_offer = 🧳 Gidýär we resminama/poçta alyp bilýär
cat-sender_request = 📦 Ibermek isleýär — ýoldaş gözleýär
cat-receiver_request = 📥 Poçta/paket almak isleýär
cat-traveler_announce = ✈️ Ýolagçylygy habar berdi (poçta barada aýdylmady)
cat-unclear = ❔ Görnüşi düşnüksiz

dir-to_tm = Türkmenistana
dir-from_tm = Türkmenistandan
dir-within_tm = Türkmenistanyň içinde
dir-unknown = ugry düşnüksiz

contact-none = başlanmady
contact-contacted = ýazdym
contact-replied = jogap berdi
contact-agreed = ylalaşdyk
contact-done = tabşyryldy
contact-no_answer = jogap ýok
contact-declined = ret etdi

notify-header = 🔔 <b>Täze bildiriş</b> · { $score }/100
notify-category = { $category }
notify-route = 🧭 <b>Ugur:</b> { $route } ({ $direction })
notify-date = 📅 <b>Sene:</b> { $date }
notify-chat = 💬 <b>Çat:</b> { $title }
notify-reasons = 🔎 <b>Näme üçin saýlandy:</b>
notify-text = ✉️ <b>Tekst:</b>
notify-no-link = ⚠️ Salgy elýeterli däl (çatyň açyk ady ýok).

reason-geo_strong = Türkmenistan ýa-da türkmen şäheri agzalýar
reason-geo_weak = Türkmenistanyň gowşak alamaty (gysgaltma/+993 telefon)
reason-route = { $count } nokatly ugur
reason-date_exact = sene görkezilen: { $date }
reason-date_day_only = aýyň güni görkezilen: { $date }
reason-date_relative = möhleti: { $date }
reason-stale_date = sene geçip gidipdir: { $date }
reason-too_long = tekst gaty uzyn
reason-phone = telefon görkezilen
reason-question = sorag görnüşi
reason-no_tm = Türkmenistanyň alamaty ýok

settings-title =
    ⚙️ <b>Sazlamalar</b>
    Habarnama çägi: <b>{ $threshold }</b> / 100
    Habarnamalar: <b>{ $notifications }</b>
    Dil: { $lang }
on = açyk
off = ýapyk
btn-toggle-notify = 🔔 Habarnamalar: { $state }
btn-cat = { $state } { $name }

sources-title = 📡 <b>Çeşmeler</b> ({ $count } / { $max })
sources-empty = Sanaw boş. config/chats.yml faýlyna ýa-da /add_source @username buýrugy bilen goşuň
source-line = { $state } { $title }{ $note }
source-error = { " " }— ýalňyşlyk: { $error }
add-source-usage = Ulanylyşy: /add_source @username (ýa-da çatyň sanly id-si). Userbot hasaby çatda bolmaly.
add-source-bad = Açyk çatyň @username-i ýa-da userbot hasaby agza bolan çatyň sanly id-si (-100…) gerek.
add-source-limit = Çeşmeleriň çägine ýetildi: { $max }.
add-source-ok = ✅ Çeşme goşuldy. Userbot ony bir minutyň içinde birikdirer.
source-toggled = Taýýar

stats-text =
    📊 <b>7 günde</b>
    Tapyldy: { $total }
    Iberilen habarnama: { $notified }
    Gaýtalanma: { $dups }
    Baha: 👍 { $useful } · 👎 { $irrelevant }
    Habarlaşma: ýazdym { $contacted }, jogap berdi { $replied }, ylalaşdyk { $agreed }, tabşyryldy { $done }

export-caption = Tapyndylar we bahalar (iberijileriň telefonlarysyz we kesgitleýjilerisiz).
export-empty = Häzirlikçe maglumat ýok.

test-usage = Ulanylyşy: /test bildirişiň teksti
test-result =
    🧪 <b>Barlag</b>: { $score }/100 (derejesi: { $level })
    { $category }
    🧭 { $route } ({ $direction })
    📅 { $date }

fb-saved = Sagbolun, baha ýazga alyndy
contact-saved = Ýagdaý täzelendi
contact-menu = Habarlaşma ýagdaýy:
lang-choose = 🌐 Dili saýlaň:
lang-set = Dil çalşyldy
no-match = Ýazgy tapylmady
