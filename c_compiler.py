import json
import sys
import ply.lex as lex
import ply.yacc as yacc

reserved = {
    'int': 'INT',
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'return': 'RETURN',
    'printf': 'PRINTF'
}

tokens = [
    'ID', 'ICONST',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'ASSIGN',
    'EQ', 'NE', 'LT', 'LE', 'GT', 'GE',
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE', 'SEMI', 'COMMA'
] + list(reserved.values())

t_PLUS    = r'\+'
t_MINUS   = r'-'
t_TIMES   = r'\*'
t_DIVIDE  = r'/'
t_MOD     = r'%'
t_ASSIGN  = r'='
t_EQ      = r'=='
t_NE      = r'!='
t_LE      = r'<='
t_LT      = r'<'
t_GE      = r'>='
t_GT      = r'>'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_LBRACE  = r'\{'
t_RBRACE  = r'\}'
t_SEMI    = r';'
t_COMMA   = r','

t_ignore = ' \t'

def t_COMMENT(t):
    r'(/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)|(//.*)'
    pass

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_ICONST(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"Лексична помилка: неочікуваний символ '{t.value[0]}' у рядку {t.lexer.lineno}")
    t.lexer.skip(1)

lexer = lex.lex()

class ASTNode:
    def to_dict(self):
        raise NotImplementedError

class ProgramNode(ASTNode):
    def __init__(self, functions):
        self.functions = functions

    def to_dict(self):
        return {
            "name": "TranslationUnit (C Program)",
            "children": [f.to_dict() for f in self.functions]
        }

class FunctionDeclNode(ASTNode):
    def __init__(self, ret_type, name, body):
        self.ret_type = ret_type
        self.name = name
        self.body = body

    def to_dict(self):
        return {
            "name": f"FunctionDecl: {self.ret_type} {self.name}()",
            "children": [s.to_dict() for s in self.body]
        }

class VarDeclNode(ASTNode):
    def __init__(self, var_type, name, init_expr=None):
        self.var_type = var_type
        self.name = name
        self.init_expr = init_expr

    def to_dict(self):
        children = [self.init_expr.to_dict()] if self.init_expr else []
        return {"name": f"VarDecl: {self.var_type} {self.name}", "children": children}

class AssignNode(ASTNode):
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr

    def to_dict(self):
        return {"name": f"Assign: {self.name} =", "children": [self.expr.to_dict()]}

class IfNode(ASTNode):
    def __init__(self, condition, then_body, else_body=None):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body

    def to_dict(self):
        children = [
            {"name": "Condition", "children": [self.condition.to_dict()]},
            {"name": "Then", "children": [s.to_dict() for s in self.then_body]}
        ]
        if self.else_body:
            children.append({"name": "Else", "children": [s.to_dict() for s in self.else_body]})
        return {"name": "IfStmt", "children": children}

class WhileNode(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def to_dict(self):
        return {
            "name": "WhileStmt",
            "children": [
                {"name": "Condition", "children": [self.condition.to_dict()]},
                {"name": "Body", "children": [s.to_dict() for s in self.body]}
            ]
        }

class ReturnNode(ASTNode):
    def __init__(self, expr):
        self.expr = expr

    def to_dict(self):
        return {"name": "ReturnStmt", "children": [self.expr.to_dict()]}

class PrintfNode(ASTNode):
    def __init__(self, expr):
        self.expr = expr

    def to_dict(self):
        return {"name": "Call: printf", "children": [self.expr.to_dict()]}

class BinOpNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def to_dict(self):
        return {"name": f"BinaryOp: {self.op}", "children": [self.left.to_dict(), self.right.to_dict()]}

class UnaryOpNode(ASTNode):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

    def to_dict(self):
        return {"name": f"UnaryOp: {self.op}", "children": [self.expr.to_dict()]}

class NumNode(ASTNode):
    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return {"name": f"Literal: {self.value}"}

class IdNode(ASTNode):
    def __init__(self, name):
        self.name = name

    def to_dict(self):
        return {"name": f"Identifier: {self.name}"}

precedence = (
    ('left', 'EQ', 'NE'),
    ('left', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE', 'MOD'),
    ('right', 'UMINUS')
)

def p_program(p):
    '''program : function_list'''
    p[0] = ProgramNode(p[1])

def p_function_list(p):
    '''function_list : function_list function
                     | function'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_function(p):
    '''function : INT ID LPAREN RPAREN LBRACE statement_list RBRACE'''
    p[0] = FunctionDeclNode(p[1], p[2], p[6])

def p_statement_list(p):
    '''statement_list : statement_list statement
                      | statement'''
    p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

def p_statement(p):
    '''statement : var_decl
                 | assignment
                 | if_stmt
                 | while_stmt
                 | printf_stmt
                 | return_stmt
                 | block'''
    p[0] = p[1]

def p_block(p):
    '''block : LBRACE statement_list RBRACE
             | LBRACE RBRACE'''
    p[0] = p[2] if len(p) == 4 else []

def p_var_decl(p):
    '''var_decl : INT ID SEMI
                | INT ID ASSIGN expr SEMI'''
    p[0] = VarDeclNode(p[1], p[2], None if len(p) == 4 else p[4])

def p_assignment(p):
    '''assignment : ID ASSIGN expr SEMI'''
    p[0] = AssignNode(p[1], p[3])

def p_if_stmt(p):
    '''if_stmt : IF LPAREN expr RPAREN statement
               | IF LPAREN expr RPAREN statement ELSE statement'''
    then_b = p[5] if isinstance(p[5], list) else [p[5]]
    else_b = None
    if len(p) == 8:
        else_b = p[7] if isinstance(p[7], list) else [p[7]]
    p[0] = IfNode(p[3], then_b, else_b)

def p_while_stmt(p):
    '''while_stmt : WHILE LPAREN expr RPAREN statement'''
    body = p[5] if isinstance(p[5], list) else [p[5]]
    p[0] = WhileNode(p[3], body)

def p_printf_stmt(p):
    '''printf_stmt : PRINTF LPAREN expr RPAREN SEMI'''
    p[0] = PrintfNode(p[3])

def p_return_stmt(p):
    '''return_stmt : RETURN expr SEMI'''
    p[0] = ReturnNode(p[2])

def p_expr_binop(p):
    '''expr : expr PLUS expr
            | expr MINUS expr
            | expr TIMES expr
            | expr DIVIDE expr
            | expr MOD expr
            | expr EQ expr
            | expr NE expr
            | expr LT expr
            | expr LE expr
            | expr GT expr
            | expr GE expr'''
    p[0] = BinOpNode(p[1], p[2], p[3])

def p_expr_uminus(p):
    '''expr : MINUS expr %prec UMINUS'''
    p[0] = UnaryOpNode('-', p[2])

def p_expr_group(p):
    '''expr : LPAREN expr RPAREN'''
    p[0] = p[2]

def p_expr_number(p):
    '''expr : ICONST'''
    p[0] = NumNode(p[1])

def p_expr_id(p):
    '''expr : ID'''
    p[0] = IdNode(p[1])

def p_error(p):
    if p:
        print(f"Синтаксична помилка біля токена '{p.value}' (рядок {p.lineno})")
    else:
        print("Синтаксична помилка: неочікуваний кінець файлу")

parser = yacc.yacc(debug=False)

class Interpreter:
    def __init__(self):
        self.symtab = {}
        self.returned_value = None

    def run(self, node):
        if isinstance(node, ProgramNode):
            for func in node.functions:
                if func.name == 'main':
                    self.run(func)
        elif isinstance(node, FunctionDeclNode):
            for stmt in node.body:
                self.run(stmt)
                if self.returned_value is not None:
                    break
        elif isinstance(node, VarDeclNode):
            val = self.eval_expr(node.init_expr) if node.init_expr else 0
            self.symtab[node.name] = val
        elif isinstance(node, AssignNode):
            if node.name not in self.symtab:
                raise Exception(f"Семантична помилка: змінна '{node.name}' не оголошена!")
            self.symtab[node.name] = self.eval_expr(node.expr)
        elif isinstance(node, PrintfNode):
            val = self.eval_expr(node.expr)
            print(f"[printf output]: {val}")
        elif isinstance(node, ReturnNode):
            self.returned_value = self.eval_expr(node.expr)
        elif isinstance(node, IfNode):
            cond = self.eval_expr(node.condition)
            branch = node.then_body if cond != 0 else (node.else_body or [])
            for s in branch:
                self.run(s)
        elif isinstance(node, WhileNode):
            while self.eval_expr(node.condition) != 0:
                for s in node.body:
                    self.run(s)

    def eval_expr(self, expr):
        if isinstance(expr, NumNode): return expr.value
        if isinstance(expr, IdNode):
            if expr.name not in self.symtab:
                raise Exception(f"Змінна '{expr.name}' не оголошена!")
            return self.symtab[expr.name]
        if isinstance(expr, UnaryOpNode):
            v = self.eval_expr(expr.expr)
            return -v if expr.op == '-' else v
        if isinstance(expr, BinOpNode):
            l = self.eval_expr(expr.left)
            r = self.eval_expr(expr.right)
            ops = {
                '+': l + r, '-': l - r, '*': l * r,
                '/': int(l / r), '%': l % r,
                '==': int(l == r), '!=': int(l != r),
                '<': int(l < r), '<=': int(l <= r),
                '>': int(l > r), '>=': int(l >= r)
            }
            return ops[expr.op]
        return 0

class CodeGenerator:
    def __init__(self):
        self.temp_count = 0
        self.label_count = 0
        self.code = []

    def new_temp(self):
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self):
        self.label_count += 1
        return f"L{self.label_count}"

    def gen(self, node):
        if isinstance(node, ProgramNode):
            for func in node.functions:
                self.gen(func)
        elif isinstance(node, FunctionDeclNode):
            self.code.append(f"FUNC_{node.name}:")
            for stmt in node.body:
                self.gen(stmt)
        elif isinstance(node, VarDeclNode):
            if node.init_expr:
                res = self.gen_expr(node.init_expr)
                self.code.append(f"{node.name} = {res}")
        elif isinstance(node, AssignNode):
            res = self.gen_expr(node.expr)
            self.code.append(f"{node.name} = {res}")
        elif isinstance(node, PrintfNode):
            res = self.gen_expr(node.expr)
            self.code.append(f"PARAM {res}")
            self.code.append("CALL printf, 1")
        elif isinstance(node, ReturnNode):
            res = self.gen_expr(node.expr)
            self.code.append(f"RETURN {res}")
        elif isinstance(node, IfNode):
            l_else, l_end = self.new_label(), self.new_label()
            cond = self.gen_expr(node.condition)
            self.code.append(f"IF_FALSE {cond} GOTO {l_else}")
            for s in node.then_body: self.gen(s)
            self.code.append(f"GOTO {l_end}")
            self.code.append(f"{l_else}:")
            if node.else_body:
                for s in node.else_body: self.gen(s)
            self.code.append(f"{l_end}:")
        elif isinstance(node, WhileNode):
            l_start, l_end = self.new_label(), self.new_label()
            self.code.append(f"{l_start}:")
            cond = self.gen_expr(node.condition)
            self.code.append(f"IF_FALSE {cond} GOTO {l_end}")
            for s in node.body: self.gen(s)
            self.code.append(f"GOTO {l_start}")
            self.code.append(f"{l_end}:")

    def gen_expr(self, expr):
        if isinstance(expr, NumNode): return str(expr.value)
        if isinstance(expr, IdNode): return expr.name
        if isinstance(expr, UnaryOpNode):
            sub = self.gen_expr(expr.expr)
            t = self.new_temp()
            self.code.append(f"{t} = - {sub}")
            return t
        if isinstance(expr, BinOpNode):
            l = self.gen_expr(expr.left)
            r = self.gen_expr(expr.right)
            t = self.new_temp()
            self.code.append(f"{t} = {l} {expr.op} {r}")
            return t

if __name__ == '__main__':
    source_file = 'test_program.c' if len(sys.argv) < 2 else sys.argv[1]
    with open(source_file, 'r', encoding='utf-8') as f:
        src = f.read()

    print("[1] Синтаксичний розбір (Grammar: C / C++)")
    ast = parser.parse(src, lexer=lexer)

    if ast:
        print("Розбір завершено успішно!\n")

        print("[2] Виконання програми (Семантика C)")
        interpreter = Interpreter()
        interpreter.run(ast)
        print("Таблиця змінних:", interpreter.symtab)
        print("Код завершення (Exit Code):", interpreter.returned_value)
        print()

        print("[3] Генерація цільового коду (Three-Address Code)")
        codegen = CodeGenerator()
        codegen.gen(ast)
        for line in codegen.code:
            print("   ", line)
        print()

        with open('ast_data.json', 'w', encoding='utf-8') as f:
            json.dump(ast.to_dict(), f, ensure_ascii=False, indent=2)
        print("[4] Дерево збережено у 'ast_data.json'")
