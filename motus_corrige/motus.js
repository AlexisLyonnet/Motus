const TAILLE = 7;
const ESSAIS = 7;

const grid = document.getElementById("grid");
const cells = [];

// Build 49 cells
for (let i = 0; i < TAILLE * ESSAIS; i++) {
    const cell = document.createElement("div");
    cell.classList.add("cell");
    grid.appendChild(cell);
    cells.push(cell);
}

let essai = 0;
let indexLettre = 0;

// Handle typing
function addLetter(letter) {
    if (indexLettre < TAILLE && essai < ESSAIS) {
        let cell = cells[essai * TAILLE + indexLettre];
        cell.textContent = letter.toUpperCase();
        cell.classList.add("pop");
        setTimeout(() => cell.classList.remove("pop"), 150);
        indexLettre++;
    }
}

function removeLetter() {
    if (indexLettre > 0) {
        indexLettre--;
        let cell = cells[essai * TAILLE + indexLettre];
        cell.textContent = "";
    }
}

// After Python validates, JS moves to next row
document.getElementById("validate").addEventListener("click", () => {
    indexLettre = 0;
    essai++;
});

// On-screen keyboard
document.querySelectorAll(".keyboard button").forEach(btn => {
    btn.addEventListener("click", () => {
        const key = btn.textContent;

        if (btn.classList.contains("back")) return removeLetter();
        if (btn.classList.contains("enter")) return; // Python handles it

        addLetter(key);
    });
});

// Physical keyboard
document.addEventListener("keydown", (e) => {
    if (/^[A-Za-z]$/.test(e.key)) addLetter(e.key);
    if (e.key === "Backspace") removeLetter();
});
