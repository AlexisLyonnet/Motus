import random
import asyncio
import unicodedata
from js import console, document, fetch, window
from pyodide.ffi import create_proxy

# ---------------- CONFIG ----------------
TAILLE = 7
ESSAIS = 6
VERT = "green"
JAUNE = "yellow"
GRIS = "gray"

# ---------------- DOM ----------------
grid = document.getElementById("grid")
keyboard = document.getElementById("keyboard")
validate_btn = document.getElementById("validate")
back_btn = document.getElementById("backspace")

modal_overlay = document.getElementById("modal-overlay")
modal_title = document.getElementById("modal-title")
modal_text = document.getElementById("modal-text")
modal_btn = document.getElementById("modal-btn")

# ---------------- CREATE GRID ----------------
cells = []
for _ in range(ESSAIS * TAILLE):
    cell = document.createElement("div")
    cell.classList.add("cell")
    grid.appendChild(cell)
    cells.append(cell)

# ---------------- UTILS ----------------
def normalize_text(s: str) -> str:
    # Uppercase + strip accents (Ê -> E, Ç -> C, etc.)
    s = (s or "").upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # remove diacritics
    # keep only A-Z
    s = "".join(ch for ch in s if "A" <= ch <= "Z")
    return s

def current_guess(row: int) -> str:
    return "".join(cells[row * TAILLE + i].textContent for i in range(TAILLE))

def set_letter(row: int, letter: str) -> None:
    for i in range(TAILLE):
        c = cells[row * TAILLE + i]
        if c.textContent == "":
            c.textContent = letter
            c.classList.add("pop")
            # remove pop shortly (CSS animation)
            window.setTimeout(create_proxy(lambda *_: c.classList.remove("pop")), 150)
            return

def remove_letter(row: int) -> None:
    for i in reversed(range(TAILLE)):
        c = cells[row * TAILLE + i]
        if c.textContent != "":
            c.textContent = ""
            return

def clear_row(row: int) -> None:
    for i in range(TAILLE):
        cells[row * TAILLE + i].textContent = ""
        cells[row * TAILLE + i].classList.remove(VERT)
        cells[row * TAILLE + i].classList.remove(JAUNE)
        cells[row * TAILLE + i].classList.remove(GRIS)

def show_modal(title: str, text: str, button_text: str = "OK", on_close=None) -> None:
    modal_title.textContent = title
    modal_text.textContent = text
    modal_btn.textContent = button_text
    modal_overlay.classList.remove("hidden")

    def _close(evt=None):
        modal_overlay.classList.add("hidden")
        if on_close:
            on_close()

    modal_btn.onclick = create_proxy(_close)

# ---------------- GAME LOGIC ----------------
essai = 0
mot = ""
game_over = False
input_enabled = False  # will become True after rules popup is closed

# For keyboard coloring priority: gray < yellow < green
PRIORITY = {GRIS: 0, JAUNE: 1, VERT: 2}
key_best = {}  # letter -> best_color

def find_key_button(letter: str):
    # returns the first <button> whose text is exactly the letter
    for btn in keyboard.querySelectorAll("button"):
        if (btn.textContent or "").strip().upper() == letter:
            return btn
    return None

def paint_key(letter: str, color: str):
    if not letter or letter in ("ENTRER", "⌫"):
        return
    prev = key_best.get(letter)
    if prev is not None and PRIORITY[prev] >= PRIORITY[color]:
        return
    key_best[letter] = color

    btn = find_key_button(letter)
    if not btn:
        return

    # Remove previous colors then apply the best
    btn.classList.remove(VERT)
    btn.classList.remove(JAUNE)
    btn.classList.remove(GRIS)
    btn.classList.add(color)

def color_cells(colors, row: int):
    for i, color in enumerate(colors):
        cells[row * TAILLE + i].classList.add(color)

def check_guess(prop: str, target: str):
    affichage = [""] * TAILLE
    restes = {}
    for c in target:
        restes[c] = restes.get(c, 0) + 1

    # Green letters
    for i in range(TAILLE):
        if prop[i] == target[i]:
            affichage[i] = VERT
            restes[prop[i]] -= 1

    # Yellow / Gray letters
    for i in range(TAILLE):
        if affichage[i] == "":
            lettre = prop[i]
            if lettre in restes and restes[lettre] > 0:
                affichage[i] = JAUNE
                restes[lettre] -= 1
            else:
                affichage[i] = GRIS

    return affichage, (prop == target)

def end_game(win: bool):
    global game_over, input_enabled
    game_over = True
    input_enabled = False
    if win:
        show_modal("Bravo ! 🎉", "Tu as trouvé le mot !", "Rejouer", on_close=lambda: window.location.reload())
    else:
        show_modal("Game Over 😭", f"Le mot était : {mot}", "Rejouer", on_close=lambda: window.location.reload())

def on_validate(event=None):
    global essai, game_over

    if game_over or not input_enabled:
        return

    guess = normalize_text(current_guess(essai))
    # If user typed accents, normalize and rewrite the row
    if guess != current_guess(essai):
        clear_row(essai)
        for ch in guess:
            set_letter(essai, ch)

    if len(guess) != TAILLE:
        # small feedback
        console.log("Mot incomplet")
        return

    colors, win = check_guess(guess, mot)
    color_cells(colors, essai)

    # paint keyboard
    for ch, col in zip(guess, colors):
        paint_key(ch, col)

    if win:
        end_game(True)
        return

    essai += 1
    if essai >= ESSAIS:
        end_game(False)

def on_button_click(event):
    # Handles on-screen keyboard
    global game_over

    if game_over or not input_enabled:
        return

    key = (event.target.textContent or "").strip()

    # Enter / Backspace must not occupy a cell
    if key.upper() in ("ENTRER", "ENTER"):
        on_validate(None)
        return

    if key in ("⌫", "BACKSPACE"):
        remove_letter(essai)
        return

    letter = normalize_text(key)
    if len(letter) != 1:
        return

    set_letter(essai, letter)

def on_physical_keydown(event):
    # Handles physical keyboard
    global game_over

    if game_over or not input_enabled:
        return

    k = event.key

    if k == "Enter":
        event.preventDefault()
        on_validate(None)
        return

    if k == "Backspace":
        event.preventDefault()
        remove_letter(essai)
        return

    # Accept letters + accents (é, ê, etc.)
    if len(k) == 1:
        letter = normalize_text(k)
        if len(letter) == 1:
            set_letter(essai, letter)

# ---------------- WIRE EVENTS ----------------
for btn in keyboard.querySelectorAll("button"):
    btn.addEventListener("click", create_proxy(on_button_click))

document.addEventListener("keydown", create_proxy(on_physical_keydown))

# ---------------- DICTIONARY LOADING ----------------
async def start_game():
    global mot, input_enabled, essai, game_over, key_best

    # reset
    essai = 0
    game_over = False
    key_best = {}

    # clear grid
    for r in range(ESSAIS):
        clear_row(r)

    # clear keyboard colors
    for btn in keyboard.querySelectorAll("button"):
        btn.classList.remove(VERT)
        btn.classList.remove(JAUNE)
        btn.classList.remove(GRIS)

    # load words
    try:
        response = await fetch("dictionnaire_motus.txt")
        text = await response.text()
        raw = [w.strip() for w in text.split("\n")]
        mots = []
        for w in raw:
            w2 = normalize_text(w)
            if len(w2) == TAILLE:
                mots.append(w2)
        if not mots:
            raise Exception("Dictionary empty after filtering")
    except Exception as e:
        console.log("Warning: dictionnaire_motus.txt not found or invalid. Using fallback words.", e)
        mots = ["PYTHON", "EXEMPLE", "ANAGRAM", "MYSTERE", "RAPPORT"]

    mot = random.choice(mots)
    console.log("Mot secret:", mot)

    # show rules popup, then enable input
    def enable_input():
        global input_enabled
        input_enabled = True

    show_modal(
        "Règles du Motus",
        "• Trouve le mot de 7 lettres en 7 essais.\n"
        "• Vert : bonne lettre, bonne place.\n"
        "• Jaune : bonne lettre, mauvaise place.\n"
        "• Gris : lettre absente.\n"
        "• Les accents sont ignorés (Ê = E).",
        "Jouer",
        on_close=enable_input,
    )

# Run async start_game() in PyScript
asyncio.ensure_future(start_game())
