import random

TAILLE = 7
ESSAIS = 7

# couleurs terminal
VERT = "\033[92m"
JAUNE = "\033[33m"
GRIS = "\033[90m"
RESET = "\033[0m"

with open("dictionnaire_motus.txt", "r", encoding="utf-8") as f:
    mots = [line.strip().upper() for line in f if line.strip()]

mots = [m for m in mots if len(m) == TAILLE and m.isalpha()]
mot = random.choice(mots)

for essai in range(1, ESSAIS + 1):
    prop = input(f"Essai {essai}/{ESSAIS} - donne un mot de {TAILLE} lettres: ").strip().upper()

    if len(prop) != TAILLE or not prop.isalpha():
        print("Entrée invalide.")
        continue

    affichage = []
    for i in range(TAILLE):
        if prop[i] == mot[i]:
            affichage.append(VERT + prop[i] + RESET)
        elif prop[i] in mot:
            affichage.append(JAUNE + prop[i] + RESET)
        else:
            affichage.append(GRIS + prop[i] + RESET)
    print(" ".join(affichage))

    if prop == mot:
        print("Gagné !")
        break
else:
    print("Perdu. Le mot était:", mot)