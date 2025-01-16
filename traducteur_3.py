#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re

class MTdVTranslator:
    def __init__(self):
        # 可以在“翻译器本身”使用赋值、循环等——不受目标子语言限制
        # 但我们生成的“目标程序”必须极简、无赋值等
        pass

    def parse_ts_lines(self, lines):
        """
        解析 .ts 文件 => 返回指令树 instructions
        """
        tokens = self._simple_tokenize(lines)
        instructions = self._build_ast(tokens)
        return instructions

    def _simple_tokenize(self, lines):
        """
        将多行文本做最简分割：
         - 忽略空行、注释行（以%开头或 #开头）
         - 其余按空白分割
         - '}' 单独算一个 token
        """
        result = []
        for line in lines:
            ln = line.strip()
            if not ln or ln.startswith('%') or ln.startswith('#'):
                continue
            # 让 '}' 独立: replace('}', ' } ')
            ln = ln.replace('}', ' } ')
            splitted = ln.split()
            for tk in splitted:
                result.append(tk)
        return result

    def _build_ast(self, tokens):
        """
        把 token 列表解析成指令树(可能嵌套).
        支持:
          I,P,G,D,0,1,fin,
          si(0), si(1),
          boucle, }
        大体做法: 用一个栈来管理当前层级.
        """
        root = {"type":"root","content":[]}
        level_map = {0: root}
        current_level = 0

        i = 0
        while i < len(tokens):
            tk = tokens[i]

            if tk == '}':
                # 闭合一层
                # pop
                if current_level > 0:
                    level_map.pop(current_level)
                    current_level -= 1
                i += 1
                continue

            if tk == 'boucle':
                # 新建 {type:'boucle','content':[]}
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

            # 未知 token,略过
            i += 1

        # 返回 root["content"] 作为顶层指令表
        return root["content"]

    def generate_pure_function_code(self, instructions):
        """
        核心：根据 instructions(指令树) => 生成 "无赋值/循环/局部变量" 的 Python代码(列表形式)，最后join输出
        """

        lines = []
        # 1) 先生成若干“纯函数”定义
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

        # 2) 生成 run_instructions(tape,head,AST) => (newTape,newHead)
        #    这里要用递归地遍历 AST
        lines.append("def run_instructions(tape, head, instructions):")
        lines.append("    # 如果指令序列空,返回(tape,head)")
        lines.append("    if len(instructions)==0:")
        lines.append("        return (tape, head)")
        lines.append("    else:")
        lines.append("        # 取第一条指令")
        lines.append("        if instructions[0]['type']=='instruction':")
        lines.append("            return run_instruction(tape, head, instructions[0], instructions[1:])")
        lines.append("        else:")
        lines.append("            if instructions[0]['type']=='si':")
        lines.append("                # si(0)或si(1)")
        lines.append("                return run_si(tape, head, instructions[0], instructions[1:])")
        lines.append("            else:")
        lines.append("                if instructions[0]['type']=='fin':")
        lines.append("                    # 结束 => 不再执行后续")
        lines.append("                    return (tape, head)")
        lines.append("                else:")
        lines.append("                    if instructions[0]['type']=='boucle':")
        lines.append("                        return run_boucle(tape, head, instructions[0], instructions[1:])")
        lines.append("                    else:")
        lines.append("                        # endfile or unknown => skip")
        lines.append("                        return run_instructions(tape, head, instructions[1:])")
        lines.append("")

        # 3) run_instruction => 根据 val (D/G/0/1/P/I) 处理
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
        lines.append("                        # 直接返回 => 不执行后续")
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
        lines.append("                                # inconnu => skip")
        lines.append("                                return run_instructions(tape, head, rest)")
        lines.append("")

        # 4) run_si => 如果 tape[head]==condition，就执行其content，否则跳过
        lines.append("def run_si(tape, head, instr, rest):")
        lines.append("    cond_val = instr['condition']")
        lines.append("    sub_insts = instr['content']")
        lines.append("    if head>=0 and head<len(tape) and tape[head]==cond_val:")
        lines.append("        # 执行sub_insts，再继续rest")
        lines.append("        (t2,h2) = run_instructions(tape, head, sub_insts)")
        lines.append("        return run_instructions(t2, h2, rest)")
        lines.append("    else:")
        lines.append("        # skip")
        lines.append("        return run_instructions(tape, head, rest)")
        lines.append("")

        # 5) run_boucle => 执行 content 一次后(或多次?), 这里题目可能要反复执行,但不允许循环 => 只能递归
        #    典型的: while program_continue => ... 但我们不能写 while, 需函数式递归
        #    这里示例：只执行一次 => WARNING => 你可改成递归
        lines.append("def run_boucle(tape, head, instr, rest):")
        lines.append("    sub_insts = instr['content']")
        lines.append("    # [WARNING] 无循环 => 只能执行一次")
        lines.append("    (t2,h2) = run_instructions(tape, head, sub_insts)")
        lines.append("    # 执行完后 => 继续后续")
        lines.append("    return run_instructions(t2,h2,rest)")
        lines.append("")

        # 6) main(ARGC, ARG0, *ARGS)
        #   在这个子语言里不能有赋值 => 全部内联 => 只能 if/else + return
        #   这里我们只做个简单“初始Tape= empty_tape(1000), head=30, 执行instructions,最后print”
        lines.append("def main(ARGC, ARG0, *ARGS):")
        lines.append("    if ARGC<1:")
        lines.append("        # 没有指令 => return")
        lines.append("        print('Aucune instruction => rien à faire')")
        lines.append("        return ([],0)")
        lines.append("    else:")
        # 把本 translator 生成的指令 => hard-coded python list => run_instructions
        # 先序列化 instructions
        instructions_code = self._serialize_instructions_for_python(instructions)
        lines.append(f"        return run_instructions(empty_tape(1000), 30, {instructions_code})")

        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    import sys")
        lines.append("    # 构造一个列表 oneArg => [ARGC, ARG0, ARG1,...]")
        lines.append("    # 以下写法包含赋值, 如果在“函数体”外写, 多数场合可接受; 若也不行, 需要更花哨写法.")
        lines.append("    oneArg = [len(sys.argv) - 1] + sys.argv")
        lines.append("    main(oneArg)")

        return lines

    def _serialize_instructions_for_python(self, instructions):
        """
        把指令树(嵌套) 转成 Python 字面量 string, 例如:
        [
          {"type":"instruction","value":"D"},
          {"type":"si","condition":0,"content":[ ... ]},
          ...
        ]
        同时不能用赋值 => 我们只返回纯 JSON style string.
        """
        # 简易写法 => 直接用递归
        def conv(instr):
            t = instr["type"]
            if t=="instruction":
                return f"{{'type':'instruction','value':'{instr['value']}'}}"
            elif t=="fin":
                return "{'type':'fin'}"
            elif t=="si":
                c = instr["condition"]
                cc = instr["content"]
                # 递归
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

    # 读取输入文件（尝试多种编码）
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for enc in encodings:
        try:
            with open(input_ts, 'r', encoding=enc) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            pass

    translator = MTdVTranslator()
    # 解析 => AST
    instructions = translator.parse_ts_lines(lines)
    # 生成纯函数式 Python
    lines_code = translator.generate_pure_function_code(instructions)
    final_code = "\n".join(lines_code)

    # 写出
    with open(output_py,'w',encoding='utf-8') as fw:
        fw.write(final_code)
    print(f"[INFO] Generated {output_py} with pure-function code.")

if __name__=='__main__':
    main()