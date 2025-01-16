import re
import sys

class MTdVTranslator:
    def __init__(self):
        pass

    def parse_ts_lines(self, lines):
        instructions = []
        pattern = re.compile(
            r'^(?P<comment>\%.*)|'
            r'^(?P<endfile>\#)$|'
            r'.*?(?P<si0>si\s*\(\s*0\s*\))|'
            r'.*?(?P<si1>si\s*\(\s*1\s*\))|'
            r'.*?(?P<fin>\bfin\b)|'
            r'.*?(?P<I>\bI\b)|'
            r'.*?(?P<P>\bP\b)|'
            r'.*?(?P<G>\bG\b)|'
            r'.*?(?P<D>\bD\b)|'
            r'.*?(?P<zero>\b0\b)|'
            r'.*?(?P<one>\b1\b)|'
            r'.*?(?P<boucle>\bboucle\b)'
        )

        for line in lines:
            s = line.strip()
            if not s:
                continue
            m = pattern.match(s)
            if not m:
                continue
            if m.group('comment'):
                continue
            if m.group('endfile'):
                instructions.append({"type": "endfile"})
                break
            if m.group('si0'):
                instructions.append({"type": "si", "condition": 0, "content": []})
                continue
            if m.group('si1'):
                instructions.append({"type": "si", "condition": 1, "content": []})
                continue
            if m.group('fin'):
                instructions.append({"type": "fin"})
                continue
            if m.group('I'):
                instructions.append({"type": "instruction", "value": "I"})
                continue
            if m.group('P'):
                instructions.append({"type": "instruction", "value": "P"})
                continue
            if m.group('G'):
                instructions.append({"type": "instruction", "value": "G"})
                continue
            if m.group('D'):
                instructions.append({"type": "instruction", "value": "D"})
                continue
            if m.group('zero'):
                instructions.append({"type": "instruction", "value": "0"})
                continue
            if m.group('one'):
                instructions.append({"type": "instruction", "value": "1"})
                continue
            if m.group('boucle'):
                instructions.append({"type": "boucle", "content": []})
                continue
        return instructions

    def translate_instruction(self, inst, argv):
        lines = []
        if inst["type"] == "instruction":
            val = inst.get("value", "")
            if val == "I":
                lines = [
                    f"tape = ['0'] * 1000",
                    f"head = 30"
                ]
            elif val == "P":
                lines = ["print('Appuyez sur Entr\u00e9e pour continuer...')"]
            elif val == "G":
                lines = ["if head > 0:", "    head = head - 1"]
            elif val == "D":
                lines = ["if head < 999:", "    head = head + 1"]
            elif val in ["0", "1"]:
                lines = [
                    "if 0 <= head < 1000:",
                    f"    tape[head] = '{val}'"
                ]

        elif inst["type"] == "si":
            cond = inst.get("condition", 0)
            lines = [f"if tape[head] == '{cond}':"]
            sub_lines = []
            for sub in inst.get("content", []):
                sub_lines.extend(self.translate_instruction(sub, argv))
            if not sub_lines:
                lines.append("    pass")
            else:
                lines.extend(["    " + sub_line for sub_line in sub_lines])

        elif inst["type"] == "fin":
            lines = ["return"]

        elif inst["type"] == "boucle":
            boucle_id = f"boucle_{id(inst)}"
            lines = [f"def {boucle_id}():"]
            sub_lines = []
            for sub in inst.get("content", []):
                sub_lines.extend(self.translate_instruction(sub, argv))
            if not sub_lines:
                lines.append("    pass")
            else:
                lines.extend(["    " + sub_line for sub_line in sub_lines])
            lines.append(f"{boucle_id}()")

        return lines

    def generate_python_code(self, instructions, argv):
        program = [
            "def main(ARGC, ARG0):",
            "    tape = ['0'] * 1000",
            "    head = 30",
            "",
            "    # Initialisation",
            "    pos1 = int(ARG0[1])",
            "    pos2 = int(ARG0[2])",
            "    if 0 <= pos1 < 1000:",
            "        tape[pos1] = '1'",
            "    if 0 <= pos2 < 1000:",
            "        tape[pos2] = '1'",
            "",
            "    # Imprimer l'\u00e9tat initial",
            "    print('Etat initial :', ''.join(tape[:61]))",
            "    print(' ' * head + 'X')",
            ""
        ]

        for inst in instructions:
            if inst["type"] == "endfile":
                break
            program.extend(self.translate_instruction(inst, argv))

        program.extend([
            "    # Imprimer l'\u00e9tat final",
            "    print('Etat final :', ''.join(tape[:61]))",
            "    print(' ' * head + 'X')",
            "    print('Programme termin\u00e9.')",
            "",
            "if __name__ == '__main__':",
            "    ARGC = len(sys.argv) - 1",
            "    main(ARGC, sys.argv)",
        ])

        return "\n".join(program)

def main():
    if len(sys.argv) < 3:
        print("Usage: python traducteur.py input.ts arg1 arg2 ...")
        sys.exit(1)

    input_file = sys.argv[1]

    translator = MTdVTranslator()

    # Essayer d'ouvrir le fichier et lire les lignes avec un encodage par d\u00e9faut
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    instructions = translator.parse_ts_lines(lines)
    code = translator.generate_python_code(instructions, sys.argv)

    print(code)

if __name__ == '__main__':
    main()
