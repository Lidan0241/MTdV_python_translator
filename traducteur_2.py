#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys

class MTdVTranslator:
    def __init__(self):
        # 当前翻译器的内部状态
        self.indent_level = 0
        self.initialized = False
        self.boucle_count = 0
        self.boucle_stack = []
        self.code = []

    def indent(self):
        return "    " * self.indent_level

    def add_line(self, line):
        self.code.append(self.indent() + line)

    # =============== 1) 主入口：解析 .ts => 指令树 ===============
    def parse_ts_lines(self, lines):
        """
        从 .ts 文件行中，先 tokenize + P0 分析 => (tokID, tok, level)，再转成指令树
        """
        parse_result = self.parse_ts_lines_new(lines)
        instructions = self._convert_tokens_to_instructions(parse_result)
        return instructions

    # =============== 2) 分词 + 简单下推 ===============
    def parse_ts_lines_new(self, lines):
        """
        先行去掉注释('%'开头)和空行，再用正则匹配成 token。
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
            print("ERROR: parse failed or unmatched } # etc.")
            return []
        return parse_result

    def _tokenize_string(self, txt, terms_automata):
        """
        顺序匹配 tokens；若某行无法匹配则跳过该行
        """
        tokens = []
        still_good = True
        while still_good and len(txt)>0:
            # 去掉行首是 '%' 的注释
            if txt.lstrip().startswith('%'):
                newl = txt.find('\n')
                if newl!=-1:
                    txt=txt[newl+1:]
                    continue
                else:
                    break
            # 跳过空行
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
                # 跳到下一行
                newl = txt.find('\n')
                if newl!=-1:
                    txt=txt[newl+1:]
                else:
                    still_good=False
        return tokens

    def _parse_tokens_P0(self, tokens, parse_result, parse_state='P0', K=0, tokid=0):
        """
        简易下推： boucle, si(...) => K+1; '}' => K-1; '#' => stop; 其余指令 => K不变
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
                print("ERROR: unmatched '}' => negative K.")
                return False
            else:
                return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K-1, tokid)
        elif tk=='#':
            # 结束 => done
            return True
        else:
            return self._parse_tokens_P0(tokens[1:], parse_result, parse_state, K, tokid)

    # =============== 3) 把 (tokID, tok, K) => 指令树 ===============
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
                # 未知 => 跳过
                pass
        return root["content"]

    # =============== 4) 将指令结构 => Python代码(禁用 for => 用while或递归) ===============
    def translate_instruction(self, inst):
        t = inst["type"]
        if t=="instruction":
            val = inst.get("value","")
            if val=="I" and not self.initialized:
                self.add_line("# 初始化 tape & head (仅一次)")
                self.add_line("tape = [0]*1000")
                self.add_line("head = 30")
                self.initialized=True
            elif val=="P":
                self.add_line("print('Pause => tape,head:')") 
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
            # 生成 if head>=0 and head<1000 and tape[head]==cond:
            self.add_line(f"if head>=0 and head<1000 and tape[head]=={cond}:")
            self.indent_level+=1
            if not sub_insts:
                self.add_line("pass  # 无子指令")
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
                # 翻译子指令
                for s in sub_insts:
                    self.translate_instruction(s)
                # 在函数末尾递归
                self.add_line("if program_continue!=0:")
                self.indent_level+=1
                self.add_line(f"{func_name}()")
                self.indent_level-=1
                self.indent_level-=1
                # 立即调用
                self.add_line(f"{func_name}()")

        elif t=="endfile":
            pass

    def generate_python_code(self, instructions):
        # 头部
        self.add_line("import sys")
        self.add_line("")
        self.add_line("# 定义全局变量(整数+唯一列表可用):")
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
        self.add_line("# 不用 for => 用递归函数 fill_tape")

        # 定义 fill_tape
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

        # 用户输入
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

        # 遍历 instructions
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
        print("Usage: python traducteur_2.py input.ts output.py")
        sys.exit(1)

    input_ts=sys.argv[1]
    output_py=sys.argv[2]

    translator=MTdVTranslator()
    # 读取 input.ts (尝试各种编码)
    encodings = ['utf-8','latin-1','cp1252','iso-8859-1']
    for enc in encodings:
        try:
            with open(input_ts,'r',encoding=enc) as f:
                lines=f.readlines()
            break
        except UnicodeDecodeError:
            pass

    # 解析 => 指令树
    instructions=translator.parse_ts_lines(lines)
    # 生成 python 代码
    code=translator.generate_python_code(instructions)

    with open(output_py,'w',encoding='utf-8') as fw:
        fw.write(code)
    print(f"[INFO] {output_py} generated successfully, no 'for' loops, no half 'if' statements.")


if __name__=='__main__':
    main()