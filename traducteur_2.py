import re
import sys

class MTdVTranslator:
    def __init__(self):
        self.indent_level = 0
        self.initialized = False

    def indent(self, text):
        return "    " * self.indent_level + text if text.strip() else ""

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

    def translate_instruction(self, inst):
        lines = []
        if inst["type"] == "instruction":
            val = inst.get("value", "")
            if val == "I" and not self.initialized:
                lines = [
                    "tape = [0] * 1000",
                    "head = 30"
                ]
                self.initialized = True
            elif val == "P":
                lines = ["input('Appuyez sur Entrée pour continuer...')"]
            elif val == "G":
                lines = ["if head > 0:", "    head = head - 1"]
            elif val == "D":
                lines = ["if head < 999:", "    head = head + 1"]
            elif val in ["0", "1"]:
                lines = [
                    "if 0 <= head < 1000:",
                    f"    tape[head] = {val}"
                ]

        elif inst["type"] == "si":
            cond = inst.get("condition", 0)
            lines = [f"if tape[head] == {cond}:"]
            self.indent_level += 1
            sub_lines = []
            for sub in inst.get("content", []):
                sub_lines.extend(self.translate_instruction(sub))
            if not sub_lines:
                lines.append("    pass")
            else:
                lines.extend(["    " + sub_line for sub_line in sub_lines])
            self.indent_level -= 1

        elif inst["type"] == "fin":
            lines = ["program_continue = 0"]

        elif inst["type"] == "boucle":
            boucle_id = f"boucle_{self.indent_level}"
            lines = [f"def {boucle_id}():", "    global tape, head, program_continue"]
            self.indent_level += 1
            sub_lines = []
            for sub in inst.get("content", []):
                sub_lines.extend(self.translate_instruction(sub))
            if not sub_lines:
                lines.append("    pass")
            else:
                lines.extend(["    " + sub_line for sub_line in sub_lines])
            self.indent_level -= 1
            lines.append("    if program_continue:")
            lines.append(f"        {boucle_id}()")
            lines.append(f"{boucle_id}()")

        return ["    " * self.indent_level + line for line in lines]

    def generate_python_code(self, instructions):
        program = [
            "import sys",
            "",
            "# Global variables",
            "tape = [0] * 1000",
            "head = 30",
            "ARGC = 0",
            "ARG0 = ''",
            "program_continue = 1",
            "",
            "def process_args():",
            "    global ARGC, ARG0",
            "    ARGC = len(sys.argv) - 1",
            "    ARG0 = sys.argv[0]",
            "",
            "def execute_program():",
            "    global tape, head, program_continue",
            "",
            "    # Initialisation",
            "    pos1 = int(input('Veuillez entrer la 1re position (0-999): '))",
            "    pos2 = int(input('Veuillez entrer la 2e position (0-999): '))",
            "    if 0 <= pos1 < 1000:",
            "        tape[pos1] = 1",
            "    if 0 <= pos2 < 1000:",
            "        tape[pos2] = 1",
            "",
            "    # Imprimer l'état initial",
            "    print('État initial :')",
            "    print(''.join(str(x) for x in tape[0:61]))",
            "    print(' ' * head + 'X')",
            ""
        ]

        self.indent_level = 1
        for inst in instructions:
            if inst["type"] == "endfile":
                break
            program.extend(self.translate_instruction(inst))

        program.extend([
            "    # Imprimer l'état final",
            "    print('État final :')",
            "    print(''.join(str(x) for x in tape[0:61]))",
            "    print(' ' * head + 'X')",
            "    print('Programme terminé.')"
        ])

        program.extend([
            "",
            "if __name__ == '__main__':",
            "    process_args()",
            "    execute_program()"
        ])

        return "\n".join(program)

def main():
    if len(sys.argv) != 3:
        print("Usage: python traducteur2.py input.ts output.py")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    translator = MTdVTranslator()

    # Essayer d'ouvrir le fichier et lire les lignes avec différents encodages
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(input_file, 'r', encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            pass

    instructions = translator.parse_ts_lines(lines)
    code = translator.generate_python_code(instructions)

    with open(output_file, 'w', encoding='utf-8') as f_out:
        f_out.write(code)

if __name__ == '__main__':
    main()
