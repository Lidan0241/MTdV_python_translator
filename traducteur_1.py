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

    # =============== 1) 新的 parseur 主函数（对外接口） ===============
    def parse_ts_lines(self, lines):
        """
        从 .ts 文件行中，先用 tokenize + P0 分析得到 (tokID, tok, level) 列表；
        再将其转换为生成代码所需的指令结构列表 (list of dict)。
        """
        # 1) 用新版解析器获取 (tokID, tok, level) 列表
        parse_result = self.parse_ts_lines_new(lines)  # 下方方法

        # 2) 将 parse_result 转成指令树/列表
        instructions = self._convert_tokens_to_instructions(parse_result)
        return instructions

    # =============== 2) 词法分析 + 简单语法状态机 ===============
    def parse_ts_lines_new(self, lines):
        """
        使用新的解析器逻辑来对 .ts 文件的行进行解析，
        返回 [(tokID, tok, level), ...] 形式的解析结果。
        """
        # 1) 先准备词法分析所需的正则
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

        # 2) 把 lines 拼成一个大字符串，用以词法分析
        txt = "\n".join(lines)
        tokens = self._tokenize_string(txt, terminals_automata)

        # 3) 用小型状态机 P0 对 tokens 进行简单语法解析 (获取 (tokID, tok, K))
        parse_result = []
        success = self._parse_tokens_P0(tokens, parse_result)
        if not success:
            print("ERROR: parse failed.")
            return []
        
        return parse_result

    def _tokenize_string(self, txt, terms_automata):
        """
        根据若干正则，把大文本 txt 分割成 token 列表。
        如果遇到无法识别的文本，就报错退出或抛异常。
        """
        txt_sz = len(txt)
        tokens = []
        match = True

        while match and (len(txt) != 0):
            # 先跳过注释行
            if txt.lstrip().startswith('%'):
                # 找到下一个换行符的位置
                next_newline = txt.find('\n')
                if next_newline != -1:
                    txt = txt[next_newline + 1:]
                    continue
                else:
                    # 如果没有找到换行符，说明已经到文件末尾
                    break
            
            # 跳过空行
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
                # 如果 for 循环没有 break，说明没有任何 token 能匹配
                # 但我们应该跳过这一行并继续
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
        简单的递归下降 / 下推自动机：
          - '#' 且 K==0 => 结束
          - '}' => K减1
          - 'boucle','si(0)','si(1)' => K加1
          - 其余指令 => K不变
        parse_result 里会记录 (tokID, tok, K)
        """
        if not tokens:
            # 如果没有更多 token，一般认为错误结束；除非之前遇到 '#'
            return False

        tok = tokens[0]
        tokid += 1
        parse_result.append((tokid, tok, K))

        if tok == '#' and K == 0:
            # 在顶层读到 '#' 就算成功结束
            return True
        elif tok in ['I','P','G','D','0','1','fin']:
            # 普通指令 => K不变
            return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K, tokid)
        elif tok in ['boucle','si(0)','si(1)']:
            # 打开一个块 => K加1
            return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K+1, tokid)
        elif tok == '}':
            # 闭合一个块 => K减1
            if K < 1:
                print('ERROR: unbalanced "}" encountered.')
                return False
            else:
                return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K-1, tokid)
        else:
            print(f'ERROR: unexpected token "{tok}" (K={K})')
            return False

    # =============== 3) 将 (tokID, tok, level) 转换为“指令结构” ===============
    def _convert_tokens_to_instructions(self, parse_result):
        """
        把 parse_result 中的一连串 (tokID, tok, K) 转换成
        形如:
          [
            {"type":"boucle", "content":[]},
            {"type":"si","condition":0,"content":[]},
            {"type":"instruction","value":"I"},
            {"type":"fin"},
            {"type":"endfile"},
            ...
          ]
        等可被 generate_python_code() 使用的数据结构。
        
        此处示例：使用 `K` 来管理嵌套块。
        实现思路：
          - 维护一个根节点 root = {"type":"root","content":[]}
          - 维护一个 {level -> 当前所在 block} 的映射
          - 当遇到 "boucle" / "si(0)" / "si(1)" 就创建新 block，附加到当前 block 的 content，并更新 level_map[level+1]
          - 当遇到 "}" 就从 level_map 里弹出
          - 当遇到 '#' => endfile
          - 当遇到普通指令 => 附加到当前 block
        """
        root = {"type": "root", "content": []}
        level_map = {0: root}   # 用 level_map[k] 来代表“第 k 层所在的当前块”
        
        for (tokid, tok, k) in parse_result:
            # 若某次出现 k 不在 level_map 里，就先给它一个“空块”，
            # 以免后面找 current_block 出错
            if k not in level_map:
                # 注意：实际需要更多判断，否则如果解析中跳级就乱了
                level_map[k] = {"type": "unknown", "content": []}

            current_block = level_map[k]

            # 判断 token
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
                # 下一层 (k+1) 的块就是 new_block
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
                # 闭合当前块 => 从 level_map 中移除
                # 这样后续指令会回到父块
                level_map.pop(k, None)
            else:
                # 未知 token, 这里不应出现，因为在 parse_ts_lines_new 已处理
                pass

        # 最终，所有指令都挂在 root["content"]，可有嵌套
        # 如果只想要顶层，就返回 root["content"]
        return root["content"]


    # =============== 4) 将指令结构转成可执行 Python 代码 ===============
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
            # 当遇到 'fin'，插入这行以让循环退出
            self.add_line("program_continue = 0")

        elif inst["type"] == "boucle":
            sub_insts = inst.get("content", [])
            if not sub_insts:
                # 如果没有子指令，就别写循环了，直接 pass
                self.add_line("# boucle vide")
                self.add_line("pass")
            else:
                self.add_line("while program_continue:")
                self.indent_level += 1
                for sub in sub_insts:
                    self.translate_instruction(sub)
                self.indent_level -= 1

        elif inst["type"] == "endfile":
            # 如果想在这里结束翻译，可自行处理
            pass


    def generate_python_code(self, instructions):
        self.code = []
        self.step_counter = 0
        self.indent_level = 0
        
        # 头部：声明全局变量
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

        # 定义 process_args
        self.add_line("def process_args():")
        self.indent_level += 1
        self.add_line("global ARGC, ARG0")
        self.add_line("import sys")
        self.add_line("ARGC = len(sys.argv) - 1")
        self.add_line("ARG0 = sys.argv[0]")
        self.indent_level -= 1
        self.add_line("")

        # 定义 execute_program
        self.add_line("def execute_program():")
        self.indent_level += 1
        self.add_line("global tape, head, program_continue, STEP")
        self.add_line("")

        # -- 这里是初始化输入 (两次输入) --
        self.add_line("# Initialisation", self.indent_level)
        # 第一次输入
        self.add_line("start1 = int(input('Veuillez entrer la position de début de la 1re plage (0-999): '))", self.indent_level)
        self.add_line("length1 = int(input('Veuillez entrer la longueur de la 1re plage: '))", self.indent_level)
        self.add_line("if 0 <= start1 < 1000:", self.indent_level)
        self.add_line("    for i in range(length1):", self.indent_level)
        self.add_line("        if start1 + i < 1000:", self.indent_level)
        self.add_line("            tape[start1 + i] = 1", self.indent_level)

        # 第二次输入
        self.add_line("", self.indent_level)
        self.add_line("start2 = int(input('Veuillez entrer la position de début de la 2e plage (0-999): '))", self.indent_level)
        self.add_line("length2 = int(input('Veuillez entrer la longueur de la 2e plage: '))", self.indent_level)
        self.add_line("if 0 <= start2 < 1000:", self.indent_level)
        self.add_line("    for i in range(length2):", self.indent_level)
        self.add_line("        if start2 + i < 1000:", self.indent_level)
        self.add_line("            tape[start2 + i] = 1", self.indent_level)

        # 打印初始状态
        self.add_line("", self.indent_level)
        self.add_line("print('État initial :')", self.indent_level)
        self.add_line("print(''.join(str(x) for x in tape[0:61]))", self.indent_level)
        self.add_line("print(' ' * head + 'X')", self.indent_level)
        self.add_line("", self.indent_level)

        # -- 这里展开指令，无循环/无递归 --
        self.translate_instructions_no_loop(instructions, self.indent_level)

        # -- 打印最终状态 --
        self.add_line("", self.indent_level)
        self.add_line("# Imprimer l'état final", self.indent_level)
        self.add_line("print('État final :')", self.indent_level)
        self.add_line("print(''.join(str(x) for x in tape[0:61]))", self.indent_level)
        self.add_line("print(' ' * head + 'X')", self.indent_level)
        self.add_line("print('Programme terminé.')", self.indent_level)
        self.add_line("", self.indent_level)

        # 收尾
        self.indent_level -= 1
        self.add_line("")
        self.add_line("if __name__ == '__main__':")
        self.indent_level += 1
        self.add_line("process_args()")
        self.add_line("execute_program()")

        # 返回最终合并的字符串
        return "\n".join(self.code)

    def translate_instructions_no_loop(self, instructions, indent_level):
        """
        依次读取 instructions，每条指令在“STEP == X”分支下执行，然后 STEP= X+1。
        
        如果遇到“boucle”或“si(...)”等需要多次执行的地方：
          - 只能做“有限展开”，把循环体展开 N 次
            或者在这里发出警告/报错说“无循环不可实现无界 boucle”。
        """
        for inst in instructions:
            self.add_line(f"# Translating {inst}", indent_level)

            # 先记录当前指令所在 stepID
            current_step = self.step_counter
            self.step_counter += 1
            next_step = self.step_counter  # 下一个 step

            # 生成 if STEP == current_step: ...
            self.add_line(f"if STEP == {current_step}:", indent_level)
            self.add_line("    # 指令开始", indent_level)
            # 在这里翻译具体指令逻辑
            self.translate_single_instruction(inst, indent_level+1)
            # 指令结束后，把 STEP 设置为 next_step（相当于“继续”）
            self.add_line(f"STEP = {next_step}", indent_level+1)
            self.add_line("", indent_level)

    def translate_single_instruction(self, inst, level):
        """
        用 if/else/print/赋值等方式翻译单条指令。
        不产生循环/递归。
        """
        t = inst.get("type", "")
        if t == "instruction":
            val = inst.get("value","")
            if val == "I":
                self.add_line("# init tape/head (example)", level)
                # 这里是否重复做初始化，看你需求
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
            # 用 if/else
            # sub_insts 只有在 cond 成立时才执行
            sub_insts = inst.get("content", [])
            self.add_line(f"if tape[head] == {cond}:", level)
            if sub_insts:
                for s in sub_insts:
                    self.translate_single_instruction(s, level+1)
            else:
                self.add_line("    pass", level)

        elif t == "fin":
            # 对于 fin => 结束执行
            self.add_line("program_continue = 0", level)
            self.add_line("# 你也可以选择这里就把 STEP 设置为一个大值，以防继续执行", level)

        elif t == "boucle":
            sub_insts = inst.get("content", [])
            # 原本你会用 while program_continue: ...
            # 但现在不能用循环 => 只能有限展开或报错
            # 例如只展开一次 + 警告
            self.add_line("# [WARNING] boucle => 无循环模式只能执行一次", level)
            for s in sub_insts:
                self.translate_single_instruction(s, level)

        elif t == "endfile":
            # 无操作
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
    
    # 读取输入文件（尝试多种编码）
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(input_file, 'r', encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            pass

    # 调用新版 parser
    instructions = translator.parse_ts_lines(lines)
    # 生成 Python 代码
    code = translator.generate_python_code(instructions)
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f_out:
        f_out.write(code)


if __name__ == '__main__':
    main()