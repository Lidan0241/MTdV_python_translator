import re
import sys

class MTdVTranslator:
    def __init__(self):
        self.indent_level = 0
        self.initialized = False
        self.boucle_count = 0
        self.boucle_stack = []
        self.code = []
    
    def indent(self):
        return "    " * self.indent_level
    
    def add_line(self, line, indent_level=None):
        if indent_level is not None:
            old_indent = self.indent_level
            self.indent_level = indent_level
            self.code.append(self.indent() + line)
            self.indent_level = old_indent
        else:
            self.code.append(self.indent() + line)

    def parse_ts_lines(self, lines):
        """
        À partir des lignes d'un fichier .ts, effectue une analyse avec tokenize + P0 pour obtenir une liste de (tokID, tok, level).
        Ensuite, convertit cette liste en une structure d'instructions requise pour la génération de code.
        """
        # 1) Utilise le nouveau parseur pour obtenir la liste (tokID, tok, level)
        parse_result = self.parse_ts_lines_new(lines)

        # 2) Convertit parse_result en une liste/arborescence d'instructions
        instructions = self._convert_tokens_to_instructions(parse_result)
        return instructions

    def parse_ts_lines_new(self, lines):
        """
        使用新的解析器逻辑来对 .ts 文件的行进行解析，
        返回 [(tokID, tok, level), ...] 形式的解析结果。
        """
        # 1) Prépare les expressions régulières nécessaires pour l'analyse lexicale
        terminals_re = {
            '#'      : r'^[ \n]*#[ \n]*',
            '}'      : r'^[ \n]*}[ \n]*',
            'I'      : r'^[ \n]*I[ \n]*',
            'P'      : r'^[ \n]*P[ \n]*',
            'G'      : r'^[ \n]*G[ \n]*',
            'D'      : r'^[ \n]*D[ \n]*',
            '0'      : r'^[ \n]*0[ \n]*',
            '1'      : r'^[ \n]*1[ \n]*',
            'fin'    : r'^[ \n]*fin[ \n]*',
            'boucle' : r'^[ \n]*boucle[ \n]*',
            'si(0)'  : r'^[ \n]*si[ \n]*\([ \n]*0[ \n]*\)[ \n]*',
            'si(1)'  : r'^[ \n]*si[ \n]*\([ \n]*1[ \n]*\)[ \n]*'
        }
        terminals_automata = {
            x: re.compile(terminals_re[x]) for x in terminals_re.keys()
        }

        # 2) Assemble les lignes en une grande chaîne pour l'analyse lexicale
        txt = "\n".join(lines)
        tokens = self._tokenize_string(txt, terminals_automata)

        # 3) Utilise une petite machine à états P0 pour une analyse syntaxique simple (obtenir (tokID, tok, K))
        parse_result = []
        success = self._parse_tokens_P0(tokens, parse_result)
        if not success:
            print("ERROR: parse failed.")
            return []
        
        return parse_result

    def _tokenize_string(self, txt, terms_automata):
        """
        Divise le texte txt en une liste de tokens en utilisant plusieurs expressions régulières.
        Si un texte non reconnu est rencontré, signale une erreur ou lève une exception.。
        """
        txt_sz = len(txt)
        tokens = []
        match = True

        while match and (len(txt) != 0):
            # Saute les lignes de commentaires
            if txt.lstrip().startswith('%'):
                # Trouve la position du prochain saut de ligne
                next_newline = txt.find('\n')
                if next_newline != -1:
                    txt = txt[next_newline + 1:]
                    continue
                else:
                    # Si aucun saut de ligne n'est trouvé, c'est la fin du fichier
                    break
            
            # sauter lignes vides
            if txt.strip() == '':
                next_newline = txt.find('\n')
                if next_newline != -1:
                    txt = txt[next_newline + 1:]
                    continue
                else:
                    break

            for tok_nm, pattern in terms_automata.items():
                match = pattern.search(txt)
                if match:
                    (b, e) = match.span(0)
                    if b == 0:
                        tokens.append(tok_nm)
                        txt = txt[e:]
                        break
            else:
                next_newline = txt.find('\n')
                if next_newline != -1:
                    txt = txt[next_newline + 1:]
                else:
                    match = False

        if match or len(txt) == 0:
            return tokens
        else:
            offset = txt_sz - len(txt)
            print(f"ERROR: unknown token at position {offset}. Remainder: {txt[:40]!r}...")
            return []

    def _parse_tokens_P0(self, tokens, parse_result, parse_state='P0', K=0, tokid=0):
        """
        Descente récursive simple / automate à pile :
          - '#' et K==0 => fin
          - '}' => K diminue de 1
          - 'boucle','si(0)','si(1)' => K augmente de 1
          - autres instructions => K reste inchangé
        parse_result enregistre (tokID, tok, K)
        """
        if not tokens:
            # Si aucun token restant, on considère une fin erronée, sauf si '#' a été rencontré
            return False

        tok = tokens[0]
        tokid += 1
        parse_result.append((tokid, tok, K))

        if tok == '#' and K == 0:
            # Rencontrer '#' au niveau supérieur indique une fin réussie
            return True
        elif tok in ['I','P','G','D','0','1','fin']:
            # Instructions normales => K reste inchangé
            return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K, tokid)
        elif tok in ['boucle','si(0)','si(1)']:
            # Ouvre un bloc => K augmente de 1
            return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K+1, tokid)
        elif tok == '}':
            # Ferme un bloc => K diminue de 1
            if K < 1:
                print('ERROR: unbalanced "}" encountered.')
                return False
            else:
                return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K-1, tokid)
        else:
            print(f'ERROR: unexpected token "{tok}" (K={K})')
            return False


    def _convert_tokens_to_instructions(self, parse_result):
        """
        Convertit une série de (tokID, tok, K) de parse_result en une structure comme :
          [
            {"type":"boucle", "content":[]},
            {"type":"si","condition":0,"content":[]},
            {"type":"instruction","value":"I"},
            {"type":"fin"},
            {"type":"endfile"},
            ...
          ]
        Ce format est utilisable par generate_python_code().

        Idée d'implémentation :
          - Maintenir un nœud racine root = {"type":"root","content":[]}
          - Maintenir une correspondance {level -> bloc courant}
          - Lors de la rencontre de "boucle" / "si(0)" / "si(1)", créer un nouveau bloc, l'ajouter au contenu du bloc courant, et mettre à jour level_map[level+1]
          - Lors de la rencontre de "}", retirer de level_map
          - Lors de la rencontre de '#', ajouter endfile
          - Pour une instruction normale, l'ajouter au bloc courant
        """
        root = {"type": "root", "content": []}
        level_map = {0: root}   # Utiliser level_map[k] pour représenter "le bloc courant au niveau k"
        
        for (tokid, tok, k) in parse_result:
            # Si k n'est pas encore dans level_map, créer un "bloc vide"
            # Sinon, les blocs sautés causeraient des erreurs
            if k not in level_map:
                # Attention : nécessiterait plus de vérifications en cas de sauts de niveau
                level_map[k] = {"type": "unknown", "content": []}

            current_block = level_map[k]

            # Analyse du token
            if tok == '#':
                current_block["content"].append({"type": "endfile"})
            elif tok in ['I','P','G','D','0','1']:
                current_block["content"].append({
                    "type": "instruction",
                    "value": tok
                })
            elif tok == 'fin':
                current_block["content"].append({"type": "fin"})
            elif tok == 'boucle':
                new_block = {"type": "boucle", "content": []}
                current_block["content"].append(new_block)
                # Le bloc suivant (k+1) devient new_block
                level_map[k+1] = new_block
            elif tok == 'si(0)':
                new_block = {"type": "si", "condition": 0, "content": []}
                current_block["content"].append(new_block)
                level_map[k+1] = new_block
            elif tok == 'si(1)':
                new_block = {"type": "si", "condition": 1, "content": []}
                current_block["content"].append(new_block)
                level_map[k+1] = new_block
            elif tok == '}':
                # Ferme le bloc courant => Retirer de level_map
                # Ainsi, les instructions suivantes retournent au bloc parent
                level_map.pop(k, None)
            else:
                # Token inconnu, ne devrait pas arriver car géré dans parse_ts_lines_new
                pass

        # Finalement, toutes les instructions sont dans root["content"], avec des blocs imbriqués
        # Si seules les instructions de niveau supérieur sont nécessaires, retourner root["content"]
        return root["content"]


    def translate_instruction(self, inst):
        if inst["type"] == "instruction":
            val = inst.get("value", "")
            if val == "I" and not self.initialized:
                self.add_line("tape = [0] * 1000")
                self.add_line("head = 30")
                self.initialized = True
            elif val == "P":
                self.add_line("input('Appuyez sur Entrée pour continuer...')")
            elif val == "G":
                self.add_line("if head > 0:")
                self.indent_level += 1
                self.add_line("head = head - 1")
                self.indent_level -= 1
            elif val == "D":
                self.add_line("if head < 999:")
                self.indent_level += 1
                self.add_line("head = head + 1")
                self.indent_level -= 1
            elif val in ["0","1"]:
                self.add_line("if head >= 0 and head < 1000:")
                self.indent_level += 1
                self.add_line(f"tape[head] = {val}")
                self.indent_level -= 1

        elif inst["type"] == "si":
            cond = inst.get("condition", 0)
            self.add_line(f"if tape[head] == {cond}:")
            self.indent_level += 1
            sub_insts = inst.get("content", [])
            if not sub_insts:
                self.add_line("pass")
            else:
                for sub in sub_insts:
                    self.translate_instruction(sub)
            self.indent_level -= 1

        elif inst["type"] == "fin":
            # lors de "fin", insérer cette ligne
            self.add_line("program_continue = 0")

        elif inst["type"] == "boucle":
            sub_insts = inst.get("content", [])
            if not sub_insts:
                # si aucune sous-instruction, ne pas créer de boulce et écrire pas
                self.add_line("# boucle vide")
                self.add_line("pass")
            else:
                self.add_line("while program_continue:")
                self.indent_level += 1
                for sub in sub_insts:
                    self.translate_instruction(sub)
                self.indent_level -= 1

        elif inst["type"] == "endfile":
            # si nécessaire, traiter la fin de fichier ici
            pass


    def generate_python_code(self, instructions):
        self.code = []
        self.step_counter = 0
        self.indent_level = 0
        
        # entête: déclaration des variables globales
        self.add_line("import sys")
        self.add_line("")
        self.add_line("# Global variables")
        self.add_line("tape = [0] * 1000")
        self.add_line("head = 30")
        self.add_line("ARGC = 0")
        self.add_line("ARG0 = ''")
        self.add_line("program_continue = 1")
        self.add_line("STEP = 0  # 用于模拟程序执行步骤")
        self.add_line("")

        # déf process_args
        self.add_line("def process_args():")
        self.indent_level += 1
        self.add_line("global ARGC, ARG0")
        self.add_line("import sys")
        self.add_line("ARGC = len(sys.argv) - 1")
        self.add_line("ARG0 = sys.argv[0]")
        self.indent_level -= 1
        self.add_line("")

        # déf execute_program
        self.add_line("def execute_program():")
        self.indent_level += 1
        self.add_line("global tape, head, program_continue, STEP")
        self.add_line("")

        # -- initialisation des entrées (2 entrées) --
        self.add_line("# Initialisation", self.indent_level)
        # 1ère entrée
        self.add_line("start1 = int(input('Veuillez entrer la position de début de la 1re plage (0-999): '))", self.indent_level)
        self.add_line("length1 = int(input('Veuillez entrer la longueur de la 1re plage: '))", self.indent_level)
        self.add_line("if 0 <= start1 < 1000:", self.indent_level)
        self.add_line("    for i in range(length1):", self.indent_level)
        self.add_line("        if start1 + i < 1000:", self.indent_level)
        self.add_line("            tape[start1 + i] = 1", self.indent_level)

        # 2ème entrée
        self.add_line("", self.indent_level)
        self.add_line("start2 = int(input('Veuillez entrer la position de début de la 2e plage (0-999): '))", self.indent_level)
        self.add_line("length2 = int(input('Veuillez entrer la longueur de la 2e plage: '))", self.indent_level)
        self.add_line("if 0 <= start2 < 1000:", self.indent_level)
        self.add_line("    for i in range(length2):", self.indent_level)
        self.add_line("        if start2 + i < 1000:", self.indent_level)
        self.add_line("            tape[start2 + i] = 1", self.indent_level)

        # print l'état initial
        self.add_line("", self.indent_level)
        self.add_line("print('État initial :')", self.indent_level)
        self.add_line("print(''.join(str(x) for x in tape[0:61]))", self.indent_level)
        self.add_line("print(' ' * head + 'X')", self.indent_level)
        self.add_line("", self.indent_level)

        # -- instructions, sans boucle ni récursivité --
        self.translate_instructions_no_loop(instructions, self.indent_level)

        # -- print l'état final --
        self.add_line("", self.indent_level)
        self.add_line("# Imprimer l'état final", self.indent_level)
        self.add_line("print('État final :')", self.indent_level)
        self.add_line("print(''.join(str(x) for x in tape[0:61]))", self.indent_level)
        self.add_line("print(' ' * head + 'X')", self.indent_level)
        self.add_line("print('Programme terminé.')", self.indent_level)
        self.add_line("", self.indent_level)

        # fin
        self.indent_level -= 1
        self.add_line("")
        self.add_line("if __name__ == '__main__':")
        self.indent_level += 1
        self.add_line("process_args()")
        self.add_line("execute_program()")

        # retourner le code final sous forme de chaîne
        return "\n".join(self.code)

    def translate_instructions_no_loop(self, instructions, indent_level):
        """
        Lire séquentiellement les instructions, chaque instruction est exécutée dans une branche "STEP == X", puis STEP = X+1.
        
        Si une "boucle" ou un "si(...)" nécessitant plusieurs exécutions est rencontré :
          - Faire un "déroulement limité", dérouler N fois la boucle
            ou émettre un avertissement/erreur disant que "les boucles infinies ne peuvent pas être réalisées sans boucle".
        """
        for inst in instructions:
            self.add_line(f"# Translating {inst}", indent_level)

            # noter le stepID actuel de l'instruction
            current_step = self.step_counter
            self.step_counter += 1
            next_step = self.step_counter  # 下一个 step

            # générer if STEP == current_step: ...
            self.add_line(f"if STEP == {current_step}:", indent_level)
            self.add_line("    # 指令开始", indent_level)
            # traduire ici la logique spécifique de l'instruction
            self.translate_single_instruction(inst, indent_level+1)
            # après l'instruction, définir STEP au next_step (= "continuer")
            self.add_line(f"STEP = {next_step}", indent_level+1)
            self.add_line("", indent_level)

    def translate_single_instruction(self, inst, level):
        """
        Traduire une instruction individuelle en utilisant if/else/print/assignation, etc.
        Ne pas générer de boucle/ni de récursivité.
        """
        t = inst.get("type", "")
        if t == "instruction":
            val = inst.get("value","")
            if val == "I":
                self.add_line("# init tape/head (example)", level)
                # Décider si l'initialisation doit être répétée selon besoins
            elif val == "P":
                self.add_line("input('Appuyez sur Entrée pour continuer...')", level)
            elif val == "G":
                self.add_line("if head > 0:", level)
                self.add_line("    head = head - 1", level)
            elif val == "D":
                self.add_line("if head < 999:", level)
                self.add_line("    head = head + 1", level)
            elif val == "0":
                self.add_line("if 0 <= head < 1000:", level)
                self.add_line("    tape[head] = 0", level)
            elif val == "1":
                self.add_line("if 0 <= head < 1000:", level)
                self.add_line("    tape[head] = 1", level)

        elif t == "si":
            cond = inst.get("condition", 0)
            # Utiliser if/else
            # sub_insts est exécuté uniquement si cond est vrai
            sub_insts = inst.get("content", [])
            self.add_line(f"if tape[head] == {cond}:", level)
            if sub_insts:
                for s in sub_insts:
                    self.translate_single_instruction(s, level+1)
            else:
                self.add_line("    pass", level)

        elif t == "fin":
            # pour fin -> arrêter l'exécution
            self.add_line("program_continue = 0", level)
            self.add_line("# 你也可以选择这里就把 STEP 设置为一个大值，以防继续执行", level)

        elif t == "boucle":
            sub_insts = inst.get("content", [])
            # Normalement, on utilisera while program_continue: ...
            # Mais ici, pas de boucle => dérouler ou émettre un avertissement
            # Par exemple, dérouler une fois + avertissement
            self.add_line("# [WARNING] boucle => 无循环模式只能执行一次", level)
            for s in sub_insts:
                self.translate_single_instruction(s, level)

        elif t == "endfile":
            # pas d'opération
            self.add_line("# endfile => do nothing", level)
        else:
            self.add_line(f"# Unrecognized instruction: {t}", level)


def main():
    if len(sys.argv) != 3:
        print("Usage: python traducteur_2.py input.ts output.py")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    translator = MTdVTranslator()
    
    # lire le fichier d'entrée (avec plusieurs encodages)
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(input_file, 'r', encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            pass

    # appeler le nouveau parser
    instructions = translator.parse_ts_lines(lines)
    # générer code python
    code = translator.generate_python_code(instructions)
    
    # écrire dans le fichier de sortie
    with open(output_file, 'w', encoding='utf-8') as f_out:
        f_out.write(code)


if __name__ == '__main__':
    main()