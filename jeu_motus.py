import tkinter as tk
import random

# Exemple de mots (à remplacer par ton dictionnaire)
mots = ["BONJOUR", "BOISSON", "BOUFFIE", "BOÎTEUX"]

mot_a_deviner = random.choice(mots)

def verifier():
    mot = entree.get().upper()
    entree.delete(0, tk.END)
    resultat = ""
    for i in range(7):
        if i < len(mot):
            if mot[i] == mot_a_deviner[i]:
                resultat += mot[i].upper()
            elif mot[i] in mot_a_deviner:
                resultat += mot[i].lower()
            else:
                resultat += "."
        else:
            resultat += "."
    liste_resultats.insert(tk.END, resultat)
    if mot == mot_a_deviner:
        liste_resultats.insert(tk.END, "Félicitations ! Vous avez trouvé le mot.")

# Création fenêtre
fenetre = tk.Tk()
fenetre.title("Motus")

tk.Label(fenetre, text=f"Mot à deviner : {mot_a_deviner[0]}______").pack()
entree = tk.Entry(fenetre)
entree.pack()
tk.Button(fenetre, text="Valider", command=verifier).pack()
liste_resultats = tk.Listbox(fenetre)
liste_resultats.pack()

fenetre.mainloop()
