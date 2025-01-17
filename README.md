# MTdV_python_translator
Ce projet est réalisé dans le cadre du cours de Calculabilité en Master 2. L'objectif principal est de développer un traducteur en Python pour les programmes écrits dans le langage MTdV, tout en respectant des contraintes spécifiques pour différentes questions.

## Utilisation des scripts
- Seul le script `traducteur_1.py` est fonctionnel, les autres (`traducteur_2.py`, `traducteur_3.py` et `traducteur_4.py`) n'ont pas pu être exécutés avec succès.

### Question 1 :
- Pour exécuter le traducteur :
```
python3 traducteur_1.py <input_file.TS> <output_file.py>
```
- Pour exécuter le fichier Python généré :
```
python3 <output_file.py>
```

#### Explication du script :

|  MTdV  |                            Python                            |                            Effet                             |
| :----: | :----------------------------------------------------------: | :----------------------------------------------------------: |
|   I    |               "tape = [0] * 1000","head = 30"                | bande de longeur de 1000, afficher l’état actuel, à partir de la position 30 |
|   P    |        input('Appuyez sur Entrée pour continuer...')         |        faire une pause dans le programme (oas réussi)        |
|   G    |            "if head > 0:", "    head = head - 1"             |                  déplacer le ruban à gauche                  |
|   D    |          ["if head < 999:", "    head = head + 1"]           |                  déplacer le ruban à droite                  |
|   0    |  "if head >= 0 and head < 1000:", f"    tape[head] = {val}"  |                    changer le nombre à 0                     |
|   1    | "if head >= 0 and head < 1000:",      f"    tape[head] = {val}" |                    changer le nombre à 1                     |
|  si()  |                   if tape[head] == {cond}:                   |            pour voir si la condition est remplie             |
| boucle |                          pas réussi                          |                                                              |
|   \#   |                    "program_continue = 0"                    |                     arrêter le programme                     |


### Question 2 :
- Pour exécuter le traducteur :
```
python3 traducteur_2.py <input_file.TS> <output_file.py>
```
- Pour exécuter le fichier Python généré :
```
python3 <output_file.py>
```

| MTdV     | Python                                                | Effet                                                        |
| -------- | ----------------------------------------------------- | ------------------------------------------------------------ |
| `I`      | `tape = [0] * 1000` `head = 30`                       | Initialise un ruban de longueur 1000 et la tête à la position 30. |
| `P`      | `print`suivi de `input('Appuyez sur Entrée...')       | Affiche l’état actuel et attend une entrée utilisateur.      |
| `G`      | `if head > 0:` ` head = head - 1                      | Déplace la tête à gauche.                                    |
| `D`      | `if head < 999:` ` head = head + 1`                   | Déplace la tête à droite.                                    |
| `0`,`1`  | `if head >= 0 and head < 1000:` ` tape[head] = <val>` | Modifie la valeur sur le ruban à la position actuelle.       |
| `si(0)`  | `if tape[head] == 0:`                                 | Exécute des instructions si la condition sur le ruban est remplie. |
| `si(1)`  | `if tape[head] == 1:`                                 | Exécute des instructions si la condition sur le ruban est remplie. |
| `boucle` | Fonction récursive                                    | Implémente une boucle via des appels récursifs.              |
| `#`      | `program_continue = 0`                                | Arrêt de programme


### Question 3 :
- Pour exécuter le traducteur :
```
python3 traducteur_3.py <input_file.TS> <output_file.py>
```
- Pour exécuter le fichier Python généré :
```
python3 <output_file.py>
```

| MTdV     | Python                                            | Effet                                                        |
| -------- | ------------------------------------------------- | ------------------------------------------------------------ |
| `I`      | `tape = [0] * 1000` `head = 30`                   | Initialise un ruban de longueur 1000 et la tête à la position 30. |
| `P`      | `print`suivi de `input('Appuyez sur Entrée...')   | Affiche l’état actuel et attend une entrée utilisateur.      |
| `G`      | `move_left(head)`                                 | Déplace la tête à gauche.                                    |
| `D`      | `move_right(head)`                                | Déplace la tête à droite.                                    |
| `0`      | `write_zero(tape, head)`                          | Écrire un `0` à la position actuelle                         |
| `1`      | `write_one(tape, head)`                           | Écrire un `1` à la position actuelle                         |
| `si(0)`  | `if tape[head] == 0:`                             | Vérifier si la condition est remplie (tête sur 0)            |
| `si(1)`  | `if tape[head] == 1:`                             | Vérifier si la condition est remplie (tête sur 1)            |
| `boucle` | Fonction récursive gérant le contenu de la boucle | Répéter les instructions dans la boucle                      |
| `#`      | `return (tape, head)`                             | Arrêt de programme, fin des instructions


### Question 4 :
- Pour exécuter le traducteur :
```
python3 traducteur_4.py <input_file.TS> <output_file.py>
```
- Pour exécuter le fichier Python généré :
```
python3 <output_file.py>
```

| MTdV     | Python                                                     | Effet                                                    |
| -------- | ---------------------------------------------------------- | -------------------------------------------------------- |
| `I`      | `print_tape(state)`                                        | Affiche l’état actuel du ruban et la position de la tête |
| `P`      | `input('Appuyez sur Entrée pour continuer...')`            | Fait une pause dans l’exécution                          |
| `G`      | `move_left(state)`                                         | Déplace la tête à gauche.                                |
| `D`      | `move_right(state)`                                        | Déplace la tête à droite.                                |
| `0`      | `write_zero(state)`                                        | Écrire un `0` à la position actuelle                     |
| `1`      | `write_one(state)`                                         | Écrire un `1` à la position actuelle                     |
| `si(0)`  | `if tape[head] == 0:`                                      | Vérifier si la condition est remplie (tête sur 0)        |
| `si(1)`  | `if tape[head] == 1:`                                      | Vérifier si la condition est remplie (tête sur 1)        |
| `boucle` | `run_instructions([state[0], state[1], sub])`  (récursive) | Répéter un bloc d'instructions                           |
| `#`      | `return (tape, head, [])`                                  | Arrêt de l'exécution                                     |