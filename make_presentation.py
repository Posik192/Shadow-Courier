"""Uztaisa prezentaciju Shadow_Courier_prezentacija.pptx (6 slaidi, 16:9).

Palaišana: python make_presentation.py
Bildes ņem no shots/ un level_1.png (tās jau ir repo).
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# Krāsas tādas pašas kā spēlei
BG = RGBColor(0x14, 0x17, 0x1C)
TEXT = RGBColor(0xE8, 0xE3, 0xD3)
YELLOW = RGBColor(0xE8, 0xB9, 0x3C)
GREY = RGBColor(0x9A, 0xA0, 0xA6)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide(title, subtitle=""):
    """Jauns slaids ar tumšu fonu, dzeltenu virsrakstu un līniju."""
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    box = s.shapes.add_textbox(Inches(0.7), Inches(0.45),
                               Inches(12), Inches(1.1))
    p = box.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = title
    run.font.size = Pt(40)
    run.font.bold = True
    run.font.color.rgb = YELLOW
    run.font.name = "Verdana"
    if subtitle:
        box2 = s.shapes.add_textbox(Inches(0.7), Inches(1.35),
                                    Inches(12), Inches(0.6))
        p2 = box2.text_frame.paragraphs[0]
        r2 = p2.add_run()
        r2.text = subtitle
        r2.font.size = Pt(18)
        r2.font.color.rgb = GREY
        r2.font.name = "Verdana"
    # dzeltena līnija zem virsraksta
    line = s.shapes.add_shape(1, Inches(0.7), Inches(1.28),
                              Inches(3.2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = YELLOW
    line.line.fill.background()
    return s


def bullets(s, items, left=0.7, top=2.0, width=5.6, size=20):
    """Teksta aize ar rindiņām (bez garumzīmēm, vienkārši)."""
    box = s.shapes.add_textbox(Inches(left), Inches(top),
                               Inches(width), Inches(5.0))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(14)
        r = p.add_run()
        r.text = item
        r.font.size = Pt(size)
        r.font.color.rgb = TEXT
        r.font.name = "Verdana"
    return box


def pic(s, path, left, top, width):
    """Bilde ar plānu pelēku rāmīti."""
    p = s.shapes.add_picture(path, Inches(left), Inches(top),
                             width=Inches(width))
    p.line.color.rgb = RGBColor(0x2A, 0x31, 0x38)
    p.line.width = Pt(1.5)
    return p


# --- 1. Titulslaids ---
s = slide("SHADOW COURIER", "2D stealth / puzzle spēle")
bullets(s, [
    "Autors: Roberts Justs, P25-2",
    "",
    "Tu esi slepens kurjers noliktavā. Aiznes paketi līdz izejai -",
    "neviens sargs nedrīkst tevi pamanīt.",
    "",
    "Pygame (spēle) + FastAPI un SQLite (serveris) + Jinja (mājaslapa)",
], top=2.3, width=11.5, size=22)

# --- 2. Kā spēlē ---
s = slide("Kā spēlē", "3 līmeņi ar pieaugošu grūtību")
bullets(s, [
    "W A S D vai bultiņas - kustēties",
    "E - paņemt atslēgu / paketi, atvērt durvis, paslēpties",
    "SPACE - izslēgt tuvāko lampu",
    "P vai ESC - pauze",
    "",
    "Mērķis: atrodi atslēgu, paņem paketi un aiznes līdz izejai.",
    "Monētas dod punktus, trauksmes samazina vērtējumu (S/A/B/C).",
], width=5.4, size=18)
pic(s, "level_1.png", 6.4, 1.9, 6.3)

# --- 3. Mehānika 1 ---
s = slide("1. mehānika: gaismas briesmas", "Gaismā ilgi stāvēt nedrīkst")
bullets(s, [
    "Kartē ir tumša, ceļu apgaismo sienas lampas.",
    "Stāvot lampas gaismā, EXPOSURE josla pieaug.",
    "Ja josla piepildās (0.8 s, grūtākajos līmeņos 0.7 un 0.6 s),",
    "sargi pamana un skrien uz pēdējo redzēto vietu.",
    "Ēnā un slēptuvēs (skapīši) kurjers ir drošs.",
    "",
    "Tātad jādomā maršruts: kur var paiet, kur jāgaida tumsā.",
], width=5.4, size=18)
pic(s, "level_2.png", 6.4, 1.75, 6.3)
pic(s, "shots/hud_warning.png", 6.4, 6.62, 6.3)

# --- 4. Mehānika 2 ---
s = slide("2. mehānika: lampu izslēgšana", "SPACE dod 5 sekundes tumsas")
bullets(s, [
    "Ar SPACE izslēdz tuvāko lampu - tās gaisma pazūd",
    "un kurjers vairs nav redzams tās zonā.",
    "Lampa pati iedegas atpakaļ pēc 5 s,",
    "bet slēdzis uzlādējas 8 s - nevar spamot.",
    "",
    "Tāpēc jāplāno: kuru lampu izslēgt un kad,",
    "lai paspētu paņemt atslēgu vai paketi un aizbēgt.",
], width=5.4, size=18)
pic(s, "level_3.png", 6.4, 1.75, 6.3)
pic(s, "shots/hud_cooldown.png", 6.4, 6.62, 6.3)

# --- 5. Serveris un mājaslapa ---
s = slide("Serveris un mājaslapa", "FastAPI + SQLite + Jinja")
bullets(s, [
    "Spēles beigās rezultats aiziet uz serveri (POST /scores).",
    "Reģistrācija un login: parole glabājas kā hash,",
    "rekordus var sūtīt tikai ar tokenu.",
    "Līmeņu progress saglabājas pie konta - ienākot atpakaļ",
    "atbloķētie līmeņi paliek.",
    "Serveris pats atdod mājaslapu ar līderu tabulu.",
    "Papildus: lapa strādā arī internetā (Render).",
], width=5.4, size=17)
pic(s, "shots/web_online.png", 7.1, 1.85, 5.4)
pic(s, "shots/web_docs_crop.png", 7.1, 5.4, 5.4)

# --- 6. Grūtākais + risinājums ---
s = slide("Grūtākais un kā to atrisināju")
bullets(s, [
    "1. Sargu uzvedība. Vienkārša patruļa bija paredzama.",
    "Tāpēc sargiem ir 5 stāvokļi: patruļa, trauksme, meklēšana,",
    "brīdinājums ar lukturi un dzīšanās. Ceļu atrod ar BFS,",
    "tāpēc neiet caur sienām un neiestrēgst.",
    "",
    "2. Gaisma nedrīkst spīdēt caur sienām.",
    "Katru lampu piestiprināju sienai ar savu virzienu,",
    "gaisma ir sektors + redzeslīnijas pārbaude.",
    "Vienam un tam pašam aprēķinam ir gan zīmējums, gan EXPOSURE,",
    "tāpēc tas, ko redzi, ir tieši tas, kas tevi noķer.",
], top=1.8, width=11.8, size=19)
bullets(s, [
    "github.com/Posik192/Shadow-Courier   |   shadow-courier.onrender.com",
], top=6.8, width=11.8, size=15)

prs.save("Shadow_Courier_prezentacija.pptx")
print("Saglabāts: Shadow_Courier_prezentacija.pptx (6 slaidi)")
