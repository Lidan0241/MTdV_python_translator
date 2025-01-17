#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re

class MTdVTranslator:
    def __init__(self):
        pass

    def parse_ts_lines(self, lines):
        """
        analyse .ts -> retourne un arbre d'instructions
        """
        tokens = self._tokenize(lines)
        instructions = self._build_ast(tokens)
        return instructions

    def _tokenize(self, lines):
        """
        tokénisation simple: suppression des lignes vides, séparations '{}' etc.
        """
        res = []
        for line in lines:
            ln = line.strip()
            if not ln or ln.startswith('%') or ln.startswith('#'):
                continue
            ln = ln.replace('}', ' } ')
            splitted = ln.split()
            for tk in splitted:
                res.append(tk)
        return res

    def _build_ast(self, tokens):
        """
        construction de l'arbre d'instructions,supporte { boucles, si(0), si(1), } etc.
        """
        root = {"type":"root","content":[]}
        level_map = {0: root}
        cur_level = 0
        i = 0
        while i<len(tokens):
            tk = tokens[i]
            if tk == '}':
                # fin de bloc
                if cur_level>0:
                    level_map.pop(cur_level)
                    cur_level-=1
                i+=1
                continue
            if tk=='boucle':
                newb = {"type":"boucle","content":[]}
                level_map[cur_level]["content"].append(newb)
                cur_level+=1
                level_map[cur_level] = newb
                i+=1
                continue
            if tk=='si(0)':
                newsi = {"type":"si","condition":0,"content":[]}
                level_map[cur_level]["content"].append(newsi)
                cur_level+=1
                level_map[cur_level] = newsi
                i+=1
                continue
            if tk=='si(1)':
                newsi = {"type":"si","condition":1,"content":[]}
                level_map[cur_level]["content"].append(newsi)
                cur_level+=1
                level_map[cur_level] = newsi
                i+=1
                continue
            if tk=='fin':
                level_map[cur_level]["content"].append({"type":"fin"})
                i+=1
                continue
            if tk in ['I','P','G','D','0','1']:
                level_map[cur_level]["content"].append({
                    "type":"instruction",
                    "value":tk
                })
                i+=1
                continue
            # incoonu => ignorer
            i+=1
        return root["content"]

    def generate_pure_function_code(self, instructions):
        """
        生成 只有单参函数 + 无赋值/无循环/无局部变量 + 纯函数式 Python
        """
        lines = []

        # 1) Définir plusieurs fonctions pures avec un seul paramètre
        #    Par exemple state = [tape, head, instructions]
        #    Accéder à state[0], state[1], state[2] pour obtenir les éléments
        #    Ne pas utiliser newTape = ... => uniquement en ligne
        lines.append("def empty_tape(n):")
        lines.append("    if n<=0:")
        lines.append("        return []")
        lines.append("    else:")
        lines.append("        return [0] + empty_tape(n-1)")
        lines.append("")

        lines.append("def write_one(state):")
        lines.append("    # state=[tape, head, instructions], 这里只改 tape[head]=>1")
        lines.append("    if len(state)<2:")
        lines.append("        return state")
        lines.append("    else:")
        lines.append("        tap = state[0]")
        lines.append("        hd = state[1]")
        lines.append("        if hd<0:")
        lines.append("            return [ tap, hd, state[2] ]")
        lines.append("        else:")
        lines.append("            if hd>=len(tap):")
        lines.append("                return [ tap, hd, state[2] ]")
        lines.append("            else:")
        lines.append("                return [ tap[0:hd]+[1]+tap[hd+1:], hd, state[2] ]")
        lines.append("")

        lines.append("def write_zero(state):")
        lines.append("    if len(state)<2:")
        lines.append("        return state")
        lines.append("    else:")
        lines.append("        tap = state[0]")
        lines.append("        hd = state[1]")
        lines.append("        if hd<0:")
        lines.append("            return [tap,hd, state[2]]")
        lines.append("        else:")
        lines.append("            if hd>=len(tap):")
        lines.append("                return [tap,hd, state[2]]")
        lines.append("            else:")
        lines.append("                return [tap[0:hd]+[0]+tap[hd+1:], hd, state[2]]")
        lines.append("")

        lines.append("def move_right(state):")
        lines.append("    # state=[tape,head,instructions]")
        lines.append("    if len(state)<2:")
        lines.append("        return state")
        lines.append("    else:")
        lines.append("        tap=state[0]")
        lines.append("        hd=state[1]")
        lines.append("        return [tap, hd+1, state[2]]")
        lines.append("")

        lines.append("def move_left(state):")
        lines.append("    if len(state)<2:")
        lines.append("        return state")
        lines.append("    else:")
        lines.append("        tap=state[0]")
        lines.append("        hd=state[1]")
        lines.append("        return [tap, hd-1, state[2]]")
        lines.append("")

        lines.append("def get_instructions(state):")
        lines.append("    if len(state)<3:")
        lines.append("        return []")
        lines.append("    else:")
        lines.append("        return state[2]")
        lines.append("")

        lines.append("def set_instructions(state, newInstrs):")
        lines.append("    if len(state)<3:")
        lines.append("        return state")
        lines.append("    else:")
        lines.append("        return [ state[0], state[1], newInstrs ]")
        lines.append("")

        lines.append("def print_tape(state):")
        lines.append("    if len(state)<2:")
        lines.append("        print('State incomplete =>', state)")
        lines.append("        return state")
        lines.append("    else:")
        lines.append("        tap=state[0]")
        lines.append("        hd=state[1]")
        lines.append("        if hd<0:")
        lines.append("            print('Head<0 =>', hd)")
        lines.append("            print('Tape=', tap)")
        lines.append("            return state")
        lines.append("        else:")
        lines.append("            if hd>=len(tap):")
        lines.append("                print('Head>len =>', hd)")
        lines.append("                print('Tape=', tap)")
        lines.append("                return state")
        lines.append("            else:")
        lines.append("                print('Tape=', tap)")
        lines.append("                print('Head=', hd, 'Value=', tap[hd])")
        lines.append("                return state")
        lines.append("")

        # Exécution des instructions : n'accepte qu'un paramètre state => retourne un nouvel état
        lines.append("def step_instruction(state):")
        lines.append("    # 取 instructions[0] =>执行 => 返回新state+去掉instructions[0]")
        lines.append("    instrs = get_instructions(state)")
        lines.append("    if len(instrs)==0:")
        lines.append("        return state")
        lines.append("    else:")
        lines.append("        first = instrs[0]")
        lines.append("        rest = instrs[1:]")
        lines.append("        if first['type']=='instruction':")
        lines.append("            val = first['value']")
        lines.append("            if val=='D':")
        lines.append("                return set_instructions(move_right(state), rest)")
        lines.append("            else:")
        lines.append("                if val=='G':")
        lines.append("                    return set_instructions(move_left(state), rest)")
        lines.append("                else:")
        lines.append("                    if val=='0':")
        lines.append("                        return set_instructions(write_zero(state), rest)")
        lines.append("                    else:")
        lines.append("                        if val=='1':")
        lines.append("                            return set_instructions(write_one(state), rest)")
        lines.append("                        else:")
        lines.append("                            if val=='I':")
        lines.append("                                # print tape")
        lines.append("                                return set_instructions(print_tape(state), rest)")
        lines.append("                            else:")
        lines.append("                                if val=='P':")
        lines.append("                                    print_tape(state)")
        lines.append("                                    input('Appuyez sur Entrée pour continuer...')")
        lines.append("                                    return set_instructions(state, rest)")
        lines.append("                                else:")
        lines.append("                                    if val=='fin':")
        lines.append("                                        # fin => ignore rest")
        lines.append("                                        return [ state[0], state[1], [] ]")
        lines.append("                                    else:")
        lines.append("                                        # inconnue => skip")
        lines.append("                                        return set_instructions(state, rest)")
        lines.append("        else:")
        lines.append("            if first['type']=='si':")
        lines.append("                cond = first['condition']")
        lines.append("                tap = state[0]")
        lines.append("                hd  = state[1]")
        lines.append("                if hd>=0 and hd<len(tap) and tap[hd]==cond:")
        lines.append("                    # 执行sub_insts => 纯函数 => 递归")
        lines.append("                    sub = first['content']")
        lines.append("                    newState = run_instructions([tap,hd,sub])")
        lines.append("                    return set_instructions(newState, rest)")
        lines.append("                else:")
        lines.append("                    # skip sub")
        lines.append("                    return set_instructions(state, rest)")
        lines.append("            else:")
        lines.append("                if first['type']=='boucle':")
        lines.append("                    # 只能执行一次 => 或递归 => 这里先一次")
        lines.append("                    sub = first['content']")
        lines.append("                    newState = run_instructions([ state[0], state[1], sub])")
        lines.append("                    return set_instructions(newState, rest)")
        lines.append("                else:")
        lines.append("                    if first['type']=='fin':")
        lines.append("                        # fin => ignore remainder")
        lines.append("                        return [ state[0], state[1], [] ]")
        lines.append("                    else:")
        lines.append("                        # skip")
        lines.append("                        return set_instructions(state, rest)")
        lines.append("")

        lines.append("def run_instructions(state):")
        lines.append("    # 递归地执行指令列表,直到空或fin")
        lines.append("    instrs = get_instructions(state)")
        lines.append("    if len(instrs)==0:")
        lines.append("        return state")
        lines.append("    else:")
        lines.append("        newState = step_instruction(state)")
        lines.append("        # tail recursion => run_instructions(newState)")
        lines.append("        return run_instructions(newState)")
        lines.append("")

        # 生成 instructions 的 python list => all in a single param
        instructions_code = self._serialize_instructions(instructions)

        lines.append("def main(oneArg):")
        lines.append("    # oneArg => [ARGC, ARG0, ARG1, ...]?")
        lines.append("    # 不能写 any assignment => 只能 if else => return")
        lines.append("    if len(oneArg)<=2:")
        lines.append("        # 不传指令 => do nothing")
        lines.append("        return []")
        lines.append("    else:")
        lines.append(f"        # 构造 state=[tape,head,instructions], tape=empty_tape(1000), head=30")
        lines.append(f"        st0 = [ empty_tape(1000), 30, {instructions_code} ]")
        lines.append(f"        stFinal = run_instructions(st0)")
        lines.append(f"        print('Programme terminé.')")
        lines.append(f"        print_tape(stFinal)")
        lines.append(f"        return stFinal")
        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    import sys")
        lines.append("    theArgs = [len(sys.argv)-1] + sys.argv")
        lines.append("    main(theArgs)")
        return lines

    def _serialize_instructions(self, instructions):
        """
        把指令树转成 python list string, 例如:
        [{'type':'instruction','value':'D'}, {'type':'si','condition':0,'content':[...]}]
        """
        def conv(inst):
            t = inst["type"]
            if t=="instruction":
                return f"{{'type':'instruction','value':'{inst['value']}'}}"
            elif t=="fin":
                return f"{{'type':'fin'}}"
            elif t=="si":
                c = inst["condition"]
                subs = inst["content"]
                subStr = "[" + ",".join(conv(x) for x in subs) + "]"
                return f"{{'type':'si','condition':{c},'content':{subStr}}}"
            elif t=="boucle":
                subs = inst["content"]
                subStr = "[" + ",".join(conv(x) for x in subs) + "]"
                return f"{{'type':'boucle','content':{subStr}}}"
            else:
                return f"{{'type':'unknown'}}"

        arr = "[" + ",".join(conv(x) for x in instructions) + "]"
        return arr


def main():
    if len(sys.argv)<3:
        print("Usage: python traducteur_one_arg.py input.ts output.py")
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
    instructions = translator.parse_ts_lines(lines)

    code_lines = translator.generate_pure_function_code(instructions)
    final_code = "\n".join(code_lines)

    with open(output_py,'w',encoding='utf-8') as fw:
        fw.write(final_code)

    print(f"[INFO] Generated {output_py} . Functions have only ONE param (state or oneArg).")


if __name__=='__main__':
    main()