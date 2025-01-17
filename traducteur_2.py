#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys

class MTdVTranslator:
    def __init__(self):
        # État interne actuel du traducteur
        self.indent_level = 0
        self.initialized = False
        self.boucle_count = 0
        self.boucle_stack = []
        self.code = []

    def indent(self):
        return "    " * self.indent_level

    def add_line(self, line):
        self.code.append(self.indent() + line)

    # =============== 1) Point d'entrée principal : analyse .ts => arbre d'instructions ===============
    def parse_ts_lines(self, lines):
        """
        À partir des lignes du fichier .ts, d'abord tokeniser + analyse P0 => (tokID, tok, level), puis convertir en arbre d'instructions
        """
        parse_result = self.parse_ts_lines_new(lines)
        instructions = self._convert_tokens_to_instructions(parse_result)
        return instructions

    # =============== 2) Tokenisation + analyse descendante simple ===============
    def parse_ts_lines_new(self, lines):
        """
        Supprimer d'abord les commentaires (lignes commençant par '%') et les lignes vides, puis correspondre avec des tokens à l'aide de regex.
        """
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
            'si(0)'  : r'^[ \n]*si[ \n]*\(\s*0\s*\)\s*',
            'si(1)'  : r'^[ \n]*si[ \n]*\(\s*1\s*\)\s*'
        }
        terminals_automata = {x: re.compile(terminals_re[x]) for x in terminals_re}

        txt = "\n".join(lines)
        tokens = self._tokenize_string(txt, terminals_automata)

        parse_result = []
        success = self._parse_tokens_P0(tokens, parse_result)
        if not success:
            print("ERREUR : échec de l'analyse ou '}' non apparié.")
            return []
        return parse_result

    def _tokenize_string(self, txt, terms_automata):
        """
        Correspondre aux tokens de manière séquentielle ; si une ligne ne peut pas être appariée, elle est ignorée
        """
        tokens = []
        still_good = True
        while still_good and len(txt)>0:
            # Supprimer les commentaires commençant par '%'
            if txt.lstrip().startswith('%'):
                newl = txt.find('\n')
                if newl!=-1:
                    txt=txt[newl+1:]
                    continue
                else:
                    break
            # Ignorer les lignes vides
            if txt.strip()=='':
                newl = txt.find('\n')
                if newl!=-1:
                    txt=txt[newl+1:]
                    continue
                else:
                    break

            matched_something=False
            for tk_name, pattern in terms_automata.items():
                m = pattern.match(txt)
                if m:
                    tokens.append(tk_name)
                    txt=txt[m.end():]
                    matched_something=True
                    break
            if not matched_something:
                # Passer à la ligne suivante
                newl = txt.find('\n')
                if newl!=-1:
                    txt=txt[newl+1:]
                else:
                    still_good=False
        return tokens

    def _parse_tokens_P0(self, tokens, parse_result, parse_state='P0', K=0, tokid=0):
        """
        Analyse descendante simple : boucle, si(...) => K+1 ; '}' => K-1 ; '#' => stop ; autres instructions => K inchangé
        """
        if not tokens:
            return True
        tk = tokens[0]
        tokid+=1
        parse_result.append((tokid, tk, K))

        if tk in ['I','P','G','D','0','1','fin']:
            return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K, tokid)
        elif tk in ['boucle','si(0)','si(1)']:
            return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K+1, tokid)
        elif tk=='}':
            if K<1:
                print("ERREUR : '}' non apparié => K négatif.")
                return False
            else:
                return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K-1, tokid)
        elif tk=='#':
            # Fin => terminé
            return True
        else:
            return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K, tokid)

    # =============== 3) Convertir (tokID, tok, K) => arbre d'instructions ===============
    def _convert_tokens_to_instructions(self, parse_result):
        root = {"type":"root","content":[]}
        level_map = {0: root}
        for (tid, tk, k) in parse_result:
            if k not in level_map:
                level_map[k] = {"type":"unknown","content":[]}
            current_block=level_map[k]

            if tk in ['I','P','G','D','0','1']:
                current_block["content"].append({"type":"instruction","value":tk})
            elif tk=='fin':
                current_block["content"].append({"type":"fin"})
            elif tk=='boucle':
                newb = {"type":"boucle","content":[]}
                current_block["content"].append(newb)
                level_map[k+1]=newb
            elif tk=='si(0)':
                newsi={"type":"si","condition":0,"content":[]}
                current_block["content"].append(newsi)
                level_map[k+1]=newsi
            elif tk=='si(1)':
                newsi={"type":"si","condition":1,"content":[]}
                current_block["content"].append(newsi)
                level_map[k+1]=newsi
            elif tk=='}':
                level_map.pop(k,None)
            elif tk=='#':
                current_block["content"].append({"type":"endfile"})
            else:
                # Inconnu => ignorer
                pass
        return root["content"]

    # =============== 4) Convertir la structure d'instructions => Code Python (interdiction des boucles for => utiliser while ou récursivité) ===============
    def translate_instruction(self, inst):
        t = inst["type"]
        if t=="instruction":
            val = inst.get("value","")
            if val=="I" and not self.initialized:
                self.add_line("# Initialiser la bande & la tête (une seule fois)")
                self.add_line("tape = [0]*1000")
                self.add_line("head = 30")
                self.initialized=True
            elif val=="P":
                self.add_line("print('Pause => tape, head:')") 
                self.add_line("print('Tape=', tape)")
                self.add_line("print('Head=', head)") 
                self.add_line("input('Appuyez sur Entrée...')")

            elif val=="G":
                self.add_line("if head>0:")
                self.indent_level+=1
                self.add_line("head = head-1")
                self.indent_level-=1

            elif val=="D":
                self.add_line("if head<999:")
                self.indent_level+=1
                self.add_line("head = head+1")
                self.indent_level-=1

            elif val in ["0","1"]:
                self.add_line("if head>=0 and head<1000:")
                self.indent_level+=1
                self.add_line(f"tape[head] = {val}")
                self.indent_level-=1

            elif val=="fin":
                self.add_line("program_continue = 0")

        elif t=="si":
            cond = inst.get("condition",0)
            sub_insts = inst.get("content",[])
            # Générer if head>=0 and head<1000 and tape[head]==cond:
            self.add_line(f"if head>=0 and head<1000 and tape[head]=={cond}:")
            self.indent_level+=1
            if not sub_insts:
                self.add_line("pass  # Pas de sous-instructions")
            else:
                for s in sub_insts:
                    self.translate_instruction(s)
            self.indent_level-=1

        elif t=="boucle":
            sub_insts = inst.get("content", [])
            if not sub_insts:
                self.add_line("# boucle vide => pass")
                self.add_line("pass")
            else:
                func_name = f"boucle_{self.boucle_count}"
                self.boucle_count+=1
                self.add_line(f"def {func_name}():")
                self.indent_level+=1
                self.add_line("global program_continue, head, tape")
                # Traduire les sous-instructions
                for s in sub_insts:
                    self.translate_instruction(s)
                # Répéter récursivement à la fin de la fonction
                self.add_line("if program_continue!=0:")
                self.indent_level+=1
                self.add_line(f"{func_name}()")
                self.indent_level-=1
                self.indent_level-=1
                # Appel immédiat
                self.add_line(f"{func_name}()")

        elif t=="endfile":
            pass

    def generate_python_code(self, instructions):
        # En-tête
        self.add_line("import sys")
        self.add_line("")
        self.add_line("# Définir les variables globales (entiers + liste unique utilisable) :")
        self.add_line("tape = [0]*1000")
        self.add_line("head = 30")
        self.add_line("program_continue = 1")
        self.add_line("ARGC = 0")
        self.add_line("ARG0 = ''")
        self.add_line("")

        self.add_line("def process_args():")
        self.indent_level+=1
        self.add_line("global ARGC, ARG0")
        self.add_line("ARGC = len(sys.argv)-1")
        self.add_line("ARG0 = sys.argv[0]")
        self.indent_level-=1
        self.add_line("")

        self.add_line("def execute_program():")
        self.indent_level+=1
        self.add_line("global tape, head, program_continue")
        self.add_line("# Pas de boucle for => utiliser une fonction récursive fill_tape")

        # Définir fill_tape
        self.add_line("def fill_tape(pos, remain):")
        self.indent_level+=1
        self.add_line("if remain<=0:")
        self.indent_level+=1
        self.add_line("return")
        self.indent_level-=1
        self.add_line("if pos<1000:")
        self.indent_level+=1
        self.add_line("tape[pos] = 1")
        self.add_line("fill_tape(pos+1, remain-1)")
        self.indent_level-=2

        # Entrée utilisateur
        self.add_line("start1 = int(input('Début 1re plage(0-999)? '))")
        self.add_line("length1= int(input('Longueur 1re plage? '))")
        self.add_line("if start1>=0 and start1<1000:")
        self.indent_level+=1
        self.add_line("fill_tape(start1, length1)")
        self.indent_level-=1
        self.add_line("")
        self.add_line("start2 = int(input('Début 2e plage(0-999)? '))")
        self.add_line("length2= int(input('Longueur 2e plage? '))")
        self.add_line("if start2>=0 and start2<1000:")
        self.indent_level+=1
        self.add_line("fill_tape(start2, length2)")
        self.indent_level-=1
        self.add_line("")

        self.add_line("print('État initial:')")
        self.add_line("print(''.join(str(x) for x in tape[0:61]))")
        self.add_line("print(' ' * head + 'X')")
        self.add_line("")

        # Parcourir les instructions
        for inst in instructions:
            if inst.get("type")=="endfile":
                break
            self.translate_instruction(inst)

        self.add_line("")
        self.add_line("print('État final:')")
        self.add_line("print(''.join(str(x) for x in tape[0:61]))")
        self.add_line("print(' ' * head + 'X')")
        self.add_line("print('Programme terminé.')")
        self.indent_level=0
        self.add_line("")
        self.add_line("if __name__=='__main__':")
        self.indent_level+=1
        self.add_line("process_args()")
        self.add_line("execute_program()")
        self.indent_level=0

        return "\n".join(self.code)


def main():
    if len(sys.argv)!=3:
        print("Utilisation : python traducteur_2.py input.ts output.py")
        sys.exit(1)

    input_ts=sys.argv[1]
    output_py=sys.argv[2]

    translator=MTdVTranslator()
    # Lire input.ts (essayer divers encodages)
    encodings = ['utf-8','latin-1','cp1252','iso-8859-1']
    for enc in encodings:
        try:
            with open(input_ts,'r',encoding=enc) as f:
                lines=f.readlines()
            break
        except UnicodeDecodeError:
            pass

    # Analyser => arbre d'instructions
    instructions=translator.parse_ts_lines(lines)
    # Générer le code Python
    code=translator.generate_python_code(instructions)

    with open(output_py,'w',encoding='utf-8') as fw:
        fw.write(code)
    print(f"[INFO] {output_py} généré avec succès, pas de boucles 'for', pas de 'if' incomplets.")


if __name__=='__main__':
    main()
