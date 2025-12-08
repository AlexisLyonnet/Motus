import random
import asyncio
from js import console, document, fetch
from pyodide.ffi import create_proxy

# ---------------- CONFIG ----------------
TAILLE = 7
ESSAIS = 7
VERT = "green"
JAUNE = "yellow"
GRIS = "gray"

# ---------------- CREATE GRID ----------------
grid = document.getElementById("grid")
cells = []

for i in range(ESSAIS):
    for j in range(TAILLE):
        cell = document.createElement("div")
        cell.classList.add("cell")
        grid.appendChild(cell)
        cells.append(cell)

# ---------------- FUNCTIONS ----------------
def color_cells(colors, row):
    for i, color in enumerate(colors):
        cells[row * TAILLE + i].classList.add(color)

def check_guess(prop, mot):
    affichage = [""] * TAILLE
    restes = {}
    for c in mot:
        restes[c] = restes.get(c, 0) + 1

    # Green letters
    for i in range(TAILLE):
        if prop[i] == mot[i]:
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

    return affichage, (prop == mot)

# ---------------- GAME LOGIC ----------------
essai = 0
mot = ""

# Validate guess
def on_validate(event=None):
    global essai, mot
    guess = "".join(cells[essai*TAILLE + i].textContent for i in range(TAILLE))
    if len(guess) != TAILLE:
        console.log("Mot incomplet")
        return

    colors, win = check_guess(guess, mot)
    color_cells(colors, essai)

    if win:
        console.log("Gagné !")
        return

    essai += 1
    if essai >= ESSAIS:
        console.log("Perdu. Mot:", mot)

validate_proxy = create_proxy(on_validate)
document.getElementById("validate").addEventListener("click", validate_proxy)

# Keyboard input
def on_key(event):
    global essai
    key = event.target.textContent

    if key == "ENTER":
        on_validate(None)
        return

    if key == "⌫":
        for i in reversed(range(TAILLE)):
            c = cells[essai*TAILLE + i]
            if c.textContent != "":
                c.textContent = ""
                break
        return

    # Add letter to first empty cell
    for i in range(TAILLE):
        c = cells[essai*TAILLE + i]
        if c.textContent == "":
            c.textContent = key
            break

keys = document.querySelectorAll(".keyboard button")
for k in keys:
    k.addEventListener("click", create_proxy(on_key))

# ---------------- DICTIONARY LOADING ----------------
async def start_game():
    global mot
    try:
        response = await fetch("dictionnaire_motus.txt")
        text = await response.text()
        mots = [w.strip().upper() for w in text.split("\n") if len(w.strip()) == TAILLE]
        if not mots:
            raise Exception("Dictionary empty")
    except Exception as e:
        console.log("Warning: dictionnaire_motus.txt not found. Using fallback words.", e)
        mots = ["PYTHON", "EXEMPLE", "MOTUSXX", "ANAGRAM", "SCHOOLX"]

    mot = random.choice(mots)
    console.log("Mot secret:", mot)

# Run async start_game() in PyScript
asyncio.ensure_future(start_game())
