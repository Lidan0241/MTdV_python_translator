import sys

# Global variables
tape = [0] * 1000
head = 30
ARGC = 0
ARG0 = ''
program_continue = 1

def process_args():
    global ARGC, ARG0
    ARGC = len(sys.argv) - 1
    ARG0 = sys.argv[0]

def execute_program():
    global tape, head, program_continue

    # Initialisation
    pos1 = int(input('Veuillez entrer la 1re position (0-999): '))
    pos2 = int(input('Veuillez entrer la 2e position (0-999): '))
    if 0 <= pos1 < 1000:
        tape[pos1] = 1
    if 0 <= pos2 < 1000:
        tape[pos2] = 1

    # Imprimer l'état initial
    print('État initial :')
    print(''.join(str(x) for x in tape[0:61]))
    print(' ' * head + 'X')

    tape = [0] * 1000
    head = 30
    def boucle_1():
        global tape, head, program_continue
        pass
        if program_continue:
            boucle_1()
    boucle_1()
    if tape[head] == 0:
        pass
    if head < 999:
        head = head + 1
    def boucle_1():
        global tape, head, program_continue
        pass
        if program_continue:
            boucle_1()
    boucle_1()
    def boucle_1():
        global tape, head, program_continue
        pass
        if program_continue:
            boucle_1()
    boucle_1()
    if head < 999:
        head = head + 1
    if tape[head] == 1:
        pass
    if head >= 0 and head < 1000:
        tape[head] = 0
    if head < 999:
        head = head + 1
    if tape[head] == 0:
        pass
    def boucle_1():
        global tape, head, program_continue
        pass
        if program_continue:
            boucle_1()
    boucle_1()
    if head > 0:
        head = head - 1
    if tape[head] == 1:
        pass
    if head < 999:
        head = head + 1
    if head >= 0 and head < 1000:
        tape[head] = 1
    if head < 999:
        head = head + 1
    def boucle_1():
        global tape, head, program_continue
        pass
        if program_continue:
            boucle_1()
    boucle_1()
    if head > 0:
        head = head - 1
    if tape[head] == 1:
        pass
    def boucle_1():
        global tape, head, program_continue
        pass
        if program_continue:
            boucle_1()
    boucle_1()
    if head > 0:
        head = head - 1
    if tape[head] == 0:
        pass
    if head < 999:
        head = head + 1
    # Imprimer l'état final
    print('État final :')
    print(''.join(str(x) for x in tape[0:61]))
    print(' ' * head + 'X')
    print('Programme terminé.')

if __name__ == '__main__':
    process_args()
    execute_program()