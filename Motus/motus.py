import random
import asyncio
import unicodedata
from js import document, console, fetch
from pyodide.ffi import create_proxy

# -----------------------
# Difficulty definitions
# -----------------------
DIFFICULTIES = {
    "easy":   {"name": "Facile",    "len": 5, "tries": 6},
    "medium": {"name": "Moyen",     "len": 6, "tries": 6},
    "hard":   {"name": "Difficile", "len": 7, "tries": 6},
}

# Colors (CSS classes)
GREEN = "green"
YELLOW = "yellow"
GRAY = "gray"

# Keyboard layout (AZERTY)
KEYBOARD_ROWS = [
    ["A","Z","E","R","T","Y","U","I","O","P"],
    ["Q","S","D","F","G","H","J","K","L","M"],
    ["ENTER","W","X","C","V","B","N","BACKSPACE"],
]

# -----------------------
# DOM Elements
# -----------------------
grid_el = document.getElementById("grid")
kb_el = document.getElementById("keyboard")
rules_el = document.getElementById("rules")
toast_el = document.getElementById("toast")
diff_el = document.getElementById("difficulty")
diff_desc_el = document.getElementById("diff-desc")
modal_el = document.getElementById("modal")
modal_title_el = document.getElementById("modal-title")
modal_text_el = document.getElementById("modal-text")
restart_btn = document.getElementById("restart")

# -----------------------
# State
# -----------------------
dictionary_by_len = {}   # {length: [words]}
dictionary_set_by_len = {}  # {length: set(words)}
difficulty = "hard"
WORD_LEN = 7
TRIES = 6

secret = ""
row = 0
col = 0
cells = []          # 2D: cells[r][c] -> element
grid_letters = []   # 2D: stored letters (strings)
game_over = False

# key colors: letter -> class ("green"/"yellow"/"gray")
key_state = {}

toast_task = None


# -----------------------
# Helpers
# -----------------------
def normalize_text(s: str) -> str:
    """Remove accents, keep letters, uppercase."""
    if s is None:
        return ""
    s = s.strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.upper()
    return s

def normalize_char(ch: str) -> str:
    ch = normalize_text(ch)
    if len(ch) >= 1:
        return ch[0]
    return ""

def show_toast(msg: str, ms: int = 1400):
    global toast_task
    toast_el.textContent = msg
    toast_el.classList.add("show")

    async def _hide():
        await asyncio.sleep(ms / 1000)
        toast_el.classList.remove("show")

    if toast_task is not None:
        try:
            toast_task.cancel()
        except Exception:
            pass
    toast_task = asyncio.ensure_future(_hide())

def set_rules_text():
    rules_el.innerHTML = (
        f"<b>But :</b> trouver le mot en <b>{TRIES}</b> tentatives.<br>"
        f"<b>Longueur :</b> <b>{WORD_LEN}</b> lettres.<br><br>"
        "Tape un mot puis appuie sur <b>Entrée</b>.<br>"
        "Utilise <b>Retour</b> pour effacer.<br>"
        "Le mot doit exister dans le dictionnaire."
    )

def set_difficulty_desc():
    d = DIFFICULTIES[difficulty]
    diff_desc_el.innerHTML = (
        f"<b>{d['name']}</b> : {d['len']} lettres, {d['tries']} tentatives."
    )

def set_selected_diff_button():
    buttons = diff_el.querySelectorAll("button.diff")
    for b in buttons:
        if b.getAttribute("data-diff") == difficulty:
            b.classList.add("selected")
        else:
            b.classList.remove("selected")

def css_set_cols(n: int):
    # Grid uses --cols variable
    document.documentElement.style.setProperty("--cols", str(n))


def build_grid():
    global cells, grid_letters
    grid_el.innerHTML = ""
    css_set_cols(WORD_LEN)

    cells = []
    grid_letters = []

    for r in range(TRIES):
        row_cells = []
        row_letters = []
        for c in range(WORD_LEN):
            cell = document.createElement("div")
            cell.classList.add("cell")
            grid_el.appendChild(cell)
            row_cells.append(cell)
            row_letters.append("")
        cells.append(row_cells)
        grid_letters.append(row_letters)

def key_priority(cls: str) -> int:
    # green > yellow > gray
    if cls == GREEN:
        return 3
    if cls == YELLOW:
        return 2
    if cls == GRAY:
        return 1
    return 0

def set_key_color(letter: str, cls: str):
    letter = letter.upper()
    if not letter or len(letter) != 1:
        return
    old = key_state.get(letter)
    if old is None or key_priority(cls) > key_priority(old):
        key_state[letter] = cls
        # update DOM key
        btn = kb_el.querySelector(f'button.key[data-key="{letter}"]')
        if btn:
            btn.classList.remove(GREEN, YELLOW, GRAY)
            btn.classList.add(cls)

def reset_keyboard_colors():
    global key_state
    key_state = {}
    btns = kb_el.querySelectorAll("button.key")
    for b in btns:
        b.classList.remove(GREEN, YELLOW, GRAY)

def build_keyboard():
    kb_el.innerHTML = ""
    for row_keys in KEYBOARD_ROWS:
        rdiv = document.createElement("div")
        rdiv.classList.add("krow")
        for k in row_keys:
            btn = document.createElement("button")
            btn.classList.add("key")
            btn.setAttribute("data-key", k)
            if k == "ENTER":
                btn.textContent = "ENTRER"
                btn.classList.add("wide")
            elif k == "BACKSPACE":
                btn.textContent = "⌫"
                btn.classList.add("wide")
            else:
                btn.textContent = k

            async def on_click(evt, key=k):
                handle_key(key)

            btn.addEventListener("click", create_proxy(on_click))
            rdiv.appendChild(btn)
        kb_el.appendChild(rdiv)

def open_modal(title: str, text: str):
    modal_title_el.textContent = title
    modal_text_el.textContent = text
    modal_el.classList.remove("hidden")

def close_modal():
    modal_el.classList.add("hidden")


# -----------------------
# Game logic
# -----------------------
def clear_row(r: int):
    for c in range(WORD_LEN):
        grid_letters[r][c] = ""
        cell = cells[r][c]
        cell.textContent = ""
        cell.classList.remove(GREEN, YELLOW, GRAY)

def add_letter(ch: str):
    global col
    if game_over:
        return
    if col >= WORD_LEN:
        return
    ch = normalize_char(ch)
    if not ch.isalpha():
        return
    grid_letters[row][col] = ch
    cells[row][col].textContent = ch
    col += 1

def backspace():
    global col
    if game_over:
        return
    if col <= 0:
        return
    col -= 1
    grid_letters[row][col] = ""
    cells[row][col].textContent = ""

def wordle_evaluate(guess: str, answer: str):
    """Return list of classes per position."""
    g = list(guess)
    a = list(answer)

    res = [GRAY] * len(g)
    remaining = {}

    # pass 1: greens
    for i in range(len(g)):
        if g[i] == a[i]:
            res[i] = GREEN
        else:
            remaining[a[i]] = remaining.get(a[i], 0) + 1

    # pass 2: yellows
    for i in range(len(g)):
        if res[i] == GREEN:
            continue
        ch = g[i]
        if remaining.get(ch, 0) > 0:
            res[i] = YELLOW
            remaining[ch] -= 1

    return res

def paint_row(r: int, guess: str, classes):
    for c, cls in enumerate(classes):
        cell = cells[r][c]
        cell.classList.remove(GREEN, YELLOW, GRAY)
        cell.classList.add(cls)
        set_key_color(guess[c], cls)

def submit_guess():
    global row, col, game_over
    if game_over:
        return
    if col < WORD_LEN:
        show_toast("Pas assez de lettres")
        return

    guess = "".join(grid_letters[row])
    guess = normalize_text(guess)

    # dictionary validation
    valid_set = dictionary_set_by_len.get(WORD_LEN, set())
    if guess not in valid_set:
        show_toast("Le mot est invalide")
        clear_row(row)
        col = 0
        return

    classes = wordle_evaluate(guess, secret)
    paint_row(row, guess, classes)

    if guess == secret:
        game_over = True
        open_modal("Bravo 🎉", f"Tu as trouvé : {secret}")
        return

    if row >= TRIES - 1:
        game_over = True
        open_modal("Game Over", f"Le mot était : {secret}")
        return

    row += 1
    col = 0

def handle_key(k: str):
    # Ensure ENTER doesn't count as a letter
    if k == "ENTER":
        submit_guess()
    elif k == "BACKSPACE":
        backspace()
    else:
        add_letter(k)

def on_keydown(evt):
    # Physical keyboard support
    k = evt.key
    if k == "Enter":
        handle_key("ENTER")
        evt.preventDefault()
        return
    if k == "Backspace":
        handle_key("BACKSPACE")
        evt.preventDefault()
        return
    if len(k) == 1:
        ch = normalize_char(k)
        if ch.isalpha():
            handle_key(ch)
            evt.preventDefault()

async def load_dictionary():
    global dictionary_by_len, dictionary_set_by_len
    try:
        resp = await fetch("dictionnaire_motus.txt")
        text = await resp.text()
        by_len = {}
        for line in text.splitlines():
            w = normalize_text(line)
            if not w.isalpha():
                continue
            L = len(w)
            if L in (5, 6, 7):
                by_len.setdefault(L, []).append(w)

        dictionary_by_len = by_len
        dictionary_set_by_len = {L: set(ws) for L, ws in by_len.items()}

        console.log("Dictionnaire chargé:", {k: len(v) for k, v in dictionary_by_len.items()})
    except Exception as e:
        console.log("Erreur dictionnaire, fallback.", e)
        dictionary_by_len = {
            5: ["POMME","ROUTE","TABLE","SALUT","CHOIX"],
            6: ["PYTHON","MOTIFS","ORANGE","TOMATE","SOURIS"],
            7: ["EXEMPLE","CERTAIN","PARTONS","HUITRES","ARBITRE"],
        }
        dictionary_set_by_len = {L: set(ws) for L, ws in dictionary_by_len.items()}

def pick_secret():
    global secret
    words = dictionary_by_len.get(WORD_LEN, [])
    if not words:
        # Should not happen with fallback
        secret = "PYTHON"[:WORD_LEN]
    else:
        secret = random.choice(words)
    console.log("Mot secret:", secret)

def apply_difficulty(diff: str):
    global difficulty, WORD_LEN, TRIES
    difficulty = diff
    d = DIFFICULTIES[diff]
    WORD_LEN = d["len"]
    TRIES = d["tries"]

def reset_game():
    global row, col, game_over
    close_modal()
    game_over = False
    row = 0
    col = 0
    reset_keyboard_colors()
    set_rules_text()
    set_difficulty_desc()
    set_selected_diff_button()
    build_grid()
    pick_secret()

def on_diff_click(evt):
    diff = evt.target.getAttribute("data-diff")
    if diff in DIFFICULTIES:
        apply_difficulty(diff)
        reset_game()

def on_restart(evt):
    reset_game()

async def start():
    # Build UI
    build_keyboard()

    # Difficulty buttons handlers
    diff_buttons = diff_el.querySelectorAll("button.diff")
    for b in diff_buttons:
        b.addEventListener("click", create_proxy(on_diff_click))

    restart_btn.addEventListener("click", create_proxy(on_restart))

    # Keyboard handler
    document.addEventListener("keydown", create_proxy(on_keydown))

    # Load dictionary
    await load_dictionary()

    # Start on medium by default (more classic)
    apply_difficulty("hard")
    reset_game()

asyncio.ensure_future(start())
