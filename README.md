# MTdV_python_translator
Ce projet est réalisé dans le cadre du cours de Calculabilité en Master 2. L'objectif principal est de développer un traducteur en Python pour les programmes écrits dans le langage MTdV, tout en respectant des contraintes spécifiques pour différentes questions.

## Utilisation des scripts

### Question 1 :

```
python3 traducteur_1.py <input_file.TS> <output_file.py>
```

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

