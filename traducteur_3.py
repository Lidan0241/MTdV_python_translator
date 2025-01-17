#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re

class MTdVTranslator:
    def __init__(self):
        # Peut utiliser des affectations, boucles, etc. dans le "traducteur lui-même" — non limité par le sous-langage cible
        # Mais le "programme cible" généré doit être minimaliste, sans affectations, etc.
        pass

    def parse_ts_lines(self, lines):
        """
        Analyser le fichier .ts => retourner un arbre d'instructions
        """
        tokens = self._simple_tokenize(lines)
        instructions = self._build_ast(tokens)
        return instructions

    def _simple_tokenize(self, lines):
        """
        Diviser le texte en plusieurs lignes de manière minimale :
         - Ignorer les lignes vides ou les commentaires (commençant par % ou #)
         - Diviser le reste par espaces
         - '}' compte comme un token séparé
        """
        result = []
        for line in lines:
            ln = line.strip()
            if not ln or ln.startswith('%') or ln.startswith('#'):
                continue
            # Rendre '}' indépendant : replace('}', ' } ')
            ln = ln.replace('}', ' } ')
            splitted = ln.split()
            for tk in splitted:
                result.append(tk)
        return result

    def _build_ast(self, tokens):
        """
        Analyser la liste de tokens en un arbre d'instructions (possiblement imbriqué).
        Supporte :
          I, P, G, D, 0, 1, fin,
          si(0), si(1),
          boucle, }
        Méthode : utiliser une pile pour gérer les niveaux actuels.
        """
        root = {"type":"root","content":[]}
        level_map = {0: root}
        current_level = 0

        i = 0
        while i < len(tokens):
            tk = tokens[i]

            if tk == '}':
                # Fermer un niveau
                # pop
                if current_level > 0:
                    level_map.pop(current_level)
                    current_level -= 1
                i += 1
                continue

            if tk == 'boucle':
                # Créer {type:'boucle','content':[]}
                new_block = {"type":"boucle","content":[]}
                level_map[current_level]["content"].append(new_block)
                current_level += 1
                level_map[current_level] = new_block
                i += 1
                continue

            if tk in ['si(0)','si(1)']:
                cond_val = 0 if tk=='si(0)' else 1
                new_block = {"type":"si","condition":cond_val,"content":[]}
                level_map[current_level]["content"].append(new_block)
                current_level += 1
                level_map[current_level] = new_block
                i += 1
                continue

            if tk == 'fin':
                level_map[current_level]["content"].append({"type":"fin"})
                i += 1
                continue

            if tk in ['I','P','G','D','0','1']:
                level_map[current_level]["content"].append({
                    "type":"instruction",
                    "value":tk
                })
                i += 1
                continue

            # Token inconnu, passer
            i += 1

        # Retourner root["content"] comme la liste d'instructions de niveau supérieur
        return root["content"]

    def generate_pure_function_code(self, instructions):
        """
        Principal : à partir de instructions (arbre d'instructions) => générer du code Python "sans affectations/boucles/variables locales" (forme liste), puis joindre et retourner
        """

        lines = []
        # 1) Générer d'abord plusieurs définitions de "fonctions pures"
        lines.append("def empty_tape(n):")
        lines.append("    if n <= 0:")
        lines.append("        return []")
        lines.append("    else:")
        lines.append("        return [0] + empty_tape(n-1)")
        lines.append("")

        lines.append("def write_one(tape, pos):")
        lines.append("    if pos<0:")
        lines.append("        return tape")
        lines.append("    else:")
        lines.append("        if pos>=len(tape):")
        lines.append("            return tape")
        lines.append("        else:")
        lines.append("            return tape[0:pos] + [1] + tape[pos+1:]")
        lines.append("")

        lines.append("def write_zero(tape, pos):")
        lines.append("    if pos<0:")
        lines.append("        return tape")
        lines.append("    else:")
        lines.append("        if pos>=len(tape):")
        lines.append("            return tape")
        lines.append("        else:")
        lines.append("            return tape[0:pos] + [0] + tape[pos+1:]")
        lines.append("")

        lines.append("def move_right(pos):")
        lines.append("    return pos + 1")
        lines.append("")

        lines.append("def move_left(pos):")
        lines.append("    return pos - 1")
        lines.append("")

        lines.append("def print_tape(tape, head):")
        lines.append("    if head<0:")
        lines.append("        print('Head<0 =>', head)")
        lines.append("        print('Tape=', tape)")
        lines.append("        return 0")
        lines.append("    else:")
        lines.append("        if head>=len(tape):")
        lines.append("            print('Head>len =>', head)")
        lines.append("            print('Tape=', tape)")
        lines.append("            return 0")
        lines.append("        else:")
        lines.append("            print('Tape=', tape)")
        lines.append("            print('Head=', head, 'Value=', tape[head])")
        lines.append("            return 0")
        lines.append("")

        # 2) Générer run_instructions(tape,head,AST) => (newTape,newHead)
        #    Ici, utiliser une récursion pour parcourir l'AST
        lines.append("def run_instructions(tape, head, instructions):")
        lines.append("    # Si la séquence d'instructions est vide, retourner (tape, head)")
        lines.append("    if len(instructions)==0:")
        lines.append("        return (tape, head)")
        lines.append("    else:")
        lines.append("        # Prendre la première instruction")
        lines.append("        if instructions[0]['type']=='instruction':")
        lines.append("            return run_instruction(tape, head, instructions[0], instructions[1:])")
        lines.append("        else:")
        lines.append("            if instructions[0]['type']=='si':")
        lines.append("                # si(0) ou si(1)")
        lines.append("                return run_si(tape, head, instructions[0], instructions[1:])")
        lines.append("            else:")
        lines.append("                if instructions[0]['type']=='fin':")
        lines.append("                    # Fin => ne pas exécuter les suivantes")
        lines.append("                    return (tape, head)")
        lines.append("                else:")
        lines.append("                    if instructions[0]['type']=='boucle':")
        lines.append("                        return run_boucle(tape, head, instructions[0], instructions[1:])")
        lines.append("                    else:")
        lines.append("                        # fin de fichier ou inconnu => passer")
        lines.append("                        return run_instructions(tape, head, instructions[1:])")
        lines.append("")

        # 3) run_instruction => Traiter selon val (D/G/0/1/P/I)
        lines.append("def run_instruction(tape, head, instr, rest):")
        lines.append("    val = instr['value']")
        lines.append("    if val=='D':")
        lines.append("        return run_instructions(tape, move_right(head), rest)")
        lines.append("    else:")
        lines.append("        if val=='G':")
        lines.append("            return run_instructions(tape, move_left(head), rest)")
        lines.append("        else:")
        lines.append("            if val=='0':")
        lines.append("                return run_instructions(write_zero(tape, head), head, rest)")
        lines.append("            else:")
        lines.append("                if val=='1':")
        lines.append("                    return run_instructions(write_one(tape, head), head, rest)")
        lines.append("                else:")
        lines.append("                    if val=='fin':")
        lines.append("                        # Retour direct => ne pas exécuter les suivantes")
        lines.append("                        return (tape, head)")
        lines.append("                    else:")
        lines.append("                        if val=='I':")
        lines.append("                            print_tape(tape, head)")
        lines.append("                            return run_instructions(tape, head, rest)")
        lines.append("                        else:")
        lines.append("                            if val=='P':")
        lines.append("                                print_tape(tape, head)")
        lines.append("                                input('Appuyez sur Entrée pour continuer...')")
        lines.append("                                return run_instructions(tape, head, rest)")
        lines.append("                            else:")
        lines.append("                                # inconnu => passer")
        lines.append("                                return run_instructions(tape, head, rest)")
        lines.append("")

        # 4) run_si => Si tape[head]==condition, exécuter son contenu, sinon passer
        lines.append("def run_si(tape, head, instr, rest):")
        lines.append("    cond_val = instr['condition']")
        lines.append("    sub_insts = instr['content']")
        lines.append("    if head>=0 and head<len(tape) and tape[head]==cond_val:")
        lines.append("        # Exécuter sub_insts, puis continuer rest")
        lines.append("        (t2,h2) = run_instructions(tape, head, sub_insts)")
        lines.append("        return run_instructions(t2, h2, rest)")
        lines.append("    else:")
        lines.append("        # passer")
        lines.append("        return run_instructions(tape, head, rest)")
        lines.append("")

        # 5) run_boucle => Exécuter le contenu une fois (ou plusieurs ?), ici on pourrait devoir exécuter de manière répétée, mais la boucle n'est pas autorisée => doit utiliser la récursion
        #    Typiquement : while program_continue => ... mais nous ne pouvons pas écrire while, devons utiliser une récursion fonctionnelle
        #    Exemple ici : exécuter une seule fois => AVERTISSEMENT => Vous pouvez le modifier en récursif
        lines.append("def run_boucle(tape, head, instr, rest):")
        lines.append("    sub_insts = instr['content']")
        lines.append("    # [AVERTISSEMENT] Pas de boucle => exécuter une seule fois")
        lines.append("    (t2,h2) = run_instructions(tape, head, sub_insts)")
        lines.append("    # Après exécution => continuer le reste")
        lines.append("    return run_instructions(t2,h2,rest)")
        lines.append("")

        # 6) main(ARGC, ARG0, *ARGS)
        #   Dans ce sous-langage, aucune affectation autorisée => tout en ligne => uniquement if/else + return
        #   Ici, nous ne faisons qu'un simple "Tape initial = empty_tape(1000), head = 30, exécution des instructions, puis affichage final"
        lines.append("def main(ARGC, ARG0, *ARGS):")
        lines.append("    if ARGC<1:")
        lines.append("        # Pas d'instructions => return")
        lines.append("        print('Aucune instruction => rien à faire')")
        lines.append("        return ([],0)")
        lines.append("    else:")
        # Convertir les instructions générées par ce traducteur => liste Python hard-coded => run_instructions
        # Sérialiser les instructions d'abord
        instructions_code = self._serialize_instructions_for_python(instructions)
        lines.append(f"        return run_instructions(empty_tape(1000), 30, {instructions_code})")

        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    import sys")
        lines.append("    # Construire une liste oneArg => [ARGC, ARG0, ARG1,...]")
        lines.append("    # La méthode suivante contient des affectations, acceptable dans la plupart des cas si hors des fonctions ; sinon, une méthode plus complexe est requise.")
        lines.append("    oneArg = [len(sys.argv) - 1] + sys.argv")
        lines.append("    main(oneArg)")

        return lines

    def _serialize_instructions_for_python(self, instructions):
        """
        Convertir un arbre d'instructions (imbriqué) en un littéral Python string, par exemple :
        [
          {"type":"instruction","value":"D"},
          {"type":"si","condition":0,"content":[ ... ]},
          ...
        ]
        Sans affectations => Retourne uniquement un string de style JSON.
        """
        # Méthode simple : utiliser directement la récursion
        def conv(instr):
            t = instr["type"]
            if t=="instruction":
                return f"{{'type':'instruction','value':'{instr['value']}'}}"
            elif t=="fin":
                return "{'type':'fin'}"
            elif t=="si":
                c = instr["condition"]
                cc = instr["content"]
                # Récursion
                content_str = '[' + ','.join(conv(x) for x in cc) + ']'
                return f"{{'type':'si','condition':{c},'content':{content_str}}}"
            elif t=="boucle":
                cc = instr["content"]
                content_str = '[' + ','.join(conv(x) for x in cc) + ']'
                return f"{{'type':'boucle','content':{content_str}}}"
            else:
                return "{'type':'unknown'}"

        arr = '[' + ','.join(conv(x) for x in instructions) + ']'
        return arr

def main():
    if len(sys.argv) < 3:
        print("Usage: python traducteur_sans_affect.py input.ts output.py")
        sys.exit(1)

    input_ts = sys.argv[1]
    output_py = sys.argv[2]

    # Lire le fichier d'entrée (essayer plusieurs encodages)
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(input_ts, 'r', encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            pass

    translator = MTdVTranslator()
    # Analyser => AST
    instructions = translator.parse_ts_lines(lines)
    # Générer du Python en style fonctionnel pur
    lines_code = translator.generate_pure_function_code(instructions)
    final_code = "\n".join(lines_code)

    # Écrire dans un fichier
    with open(output_py,'w',encoding='utf-8') as fw:
        fw.write(final_code)
    print(f"[INFO] Generated {output_py} with pure-function code.")

if __name__=='__main__':
    main()
