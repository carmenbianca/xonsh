"""Implements the xonsh parser"""
from __future__ import print_function, unicode_literals
import re

from ply import yacc

from xonsh import ast
from xonsh.lexer import Lexer


class Location(object):
    """Location in a file."""

    def __init__(self, fname, lineno, column=None):
        """Takes a filename, line number, and optionally a column number."""
        self.fname = fname
        self.lineno = line
        self.column = column

    def __str__(self):
        s = '{0}:{1}'.format(self.fname, self.lineno)
        if self.column is not None: 
            s += ':{0}'.format(self.column)
        return s


class Parser(object):
    """A class that parses the xonsh language."""

    def __init__(self, lexer_optimize=True, lexer_table='xonsh.lexer_table',
                 yacc_optimize=True, yacc_table='xonsh.yacc_table',
                 yacc_debug=False):
        """Parameters
        ----------
        lexer_optimize : bool, optional
            Set to false when unstable and true when lexer is stable.
        lexer_table : str, optional
            Lexer module used when optimized.
        yacc_optimize : bool, optional
            Set to false when unstable and true when parser is stable.
        yacc_table : str, optional
            Parser module used when optimized.
        yacc_debug : debug, optional
            Dumps extra debug info.
        """
        self.lexer = lexer = Lexer(errfunc=self._lexer_errfunc)
        lexer.build(optimize=lexer_optimize, lextab=lexer_table)
        self.tokens = lexer.tokens

        opt_rules = [
            #'abstract_declarator',
            #'assignment_expression',
            ##'declaration_list',
            #'declaration_specifiers',
            #'designation',
            #'expression',
            #'identifier_list',
            #'init_declarator_list',
            #'parameter_type_list',
            #'specifier_qualifier_list',
            #'block_item_list',
            #'type_qualifier_list',
            #'struct_declarator_list'
            ]
        for rule in opt_rules:
            self._create_opt_rule(rule)

        self.parser = yacc.yacc(module=self, debug=yacc_debug,
            start='translation_unit_or_empty', optimize=yacc_optimize,
            tabmodule=yacc_table)

        # Stack of scopes for keeping track of symbols. _scope_stack[-1] is
        # the current (topmost) scope. Each scope is a dictionary that
        # specifies whether a name is a type. If _scope_stack[n][name] is
        # True, 'name' is currently a type in the scope. If it's False,
        # 'name' is used in the scope but not as a type (for instance, if we
        # saw: int name;
        # If 'name' is not a key in _scope_stack[n] then 'name' was not defined
        # in this scope at all.
        self._scope_stack = [dict()]

        # Keeps track of the last token given to yacc (the lookahead token)
        self._last_yielded_token = None

    def parse(self, s, filename='<code>', debug_level=0):
        """Returns an abstract syntax tree of xonsh code.

        Parameters
        ----------
        s : str
            The xonsh code.
        filename : str, optional
            Name of the file.
        debug_level : str, optional
            Debugging level passed down to yacc.

        Returns
        -------
        tree : AST
        """
        self.lexer.filename = filename
        self.lexer.lineno = 0
        self._scope_stack = [dict()]
        self._last_yielded_token = None
        tree = self.cparser.parse(input=s, lexer=self.lexer,
                                  debug=debug_level)
        return tree

    def _lexer_errfunc(self, msg, line, column):
        self._parse_error(msg, self.currloc(line, column))

    def _yacc_lookahead_token(self):
        """Gets the last token seen by the lexer."""
        return self.lexer.last

    #def _create_opt_rule(self, rulename):
    #    """Given a rule name, creates an optional ply.yacc rule
    #        for it. The name of the optional rule is
    #        <rulename>_opt
    #    """
    #    optname = rulename + '_opt'
    #
    #    def optrule(self, p):
    #        p[0] = p[1]
    #
    #    optrule.__doc__ = '%s : empty\n| %s' % (optname, rulename)
    #    optrule.__name__ = 'p_%s' % optname
    #    setattr(self.__class__, optrule.__name__, optrule)

    def currloc(self, lineno, column=None):
        """Returns the current location."""
        return Location(fname=self.lexer.fname, lineno=lineno,
                        column=column)

    def _parse_error(self, msg, loc):
        raise SyntaxError('{0}: {1}'.format(loc, msg))

    #
    # Precedence of operators
    #
    precedence = (
        ('left', 'LOGIC_OR'),
        ('left', 'LOGIC_AND'),
        ('left', 'PIPE'),
        ('left', 'XOR'),
        ('left', 'AMPERSAND'),
        ('left', 'EQ', 'NE'),
        ('left', 'GT', 'GE', 'LT', 'LE'),
        ('left', 'RSHIFT', 'LSHIFT'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MOD'), 
        ('left', 'POW'),
        )

    #
    # Grammar as defined by BNF
    #

    def p_single_input(self, p):
        """single_input : NEWLINE 
                        | simple_stmt 
                        | compound_stmt NEWLINE
        """
        p[0] = p[1]

    def p_file_input(self, p):
        """file_input : (NEWLINE | stmt)* ENDMARKER"""
        p[0] = p[1]

    def p_eval_input(self, p):
        """eval_input : testlist NEWLINE* ENDMARKER"""
        p[0] = p[1]

    def p_decorator(self, p):
        """decorator : AT dotted_name [ '(' [arglist] ')' ] NEWLINE
        """
        p[0] = p[1:]

    def p_decorators(self, p):
        """decorators : decorator+"""
        p[0] = p[1:]

    def p_decorated(self, p):
        """decorated : decorators (classdef | funcdef)"""
        p[0] = p[1:]

    def p_funcdef(self, p):
        """funcdef : 'def' NAME parameters ['->' test] ':' suite
        """
        p[0] = p[1:]

    def p_(self, p):
        """parameters : '(' [typedargslist] ')'
        """
        p[0] = p[1:]

    def p_(self, p):
        """typedargslist: (tfpdef ['=' test] (',' tfpdef ['=' test])* [','
       ['*' [tfpdef] (',' tfpdef ['=' test])* [',' '**' tfpdef] | '**' tfpdef]]
     |  '*' [tfpdef] (',' tfpdef ['=' test])* [',' '**' tfpdef] | '**' tfpdef)
        """
        p[0] = p[1:]

    def p_(self, p):
        """tfpdef: NAME [':' test]
        """
        p[0] = p[1:]

    def p_(self, p):
        """varargslist: (vfpdef ['=' test] (',' vfpdef ['=' test])* [','
       ['*' [vfpdef] (',' vfpdef ['=' test])* [',' '**' vfpdef] | '**' vfpdef]]
     |  '*' [vfpdef] (',' vfpdef ['=' test])* [',' '**' vfpdef] | '**' vfpdef)
        """
        p[0] = p[1:]

    def p_(self, p):
        """vfpdef : NAME"""
        p[0] = p[1:]

    def p_(self, p):
        """stmt : simple_stmt | compound_stmt
        """
        p[0] = p[1:]

    def p_(self, p):
        """simple_stmt: small_stmt (';' small_stmt)* [';'] NEWLINE
        """
        p[0] = p[1:]

    def p_(self, p):
        """small_stmt: (expr_stmt | del_stmt | pass_stmt | flow_stmt |
             import_stmt | global_stmt | nonlocal_stmt | assert_stmt)
        """
        p[0] = p[1:]

    def p_(self, p):
        """expr_stmt: testlist_star_expr (augassign (yield_expr|testlist) |
                     ('=' (yield_expr|testlist_star_expr))*)
        """
        p[0] = p[1:]

    def p_(self, p):
        """testlist_star_expr: (test|star_expr) (',' (test|star_expr))* [',']
        """
        p[0] = p[1:]

    def p_(self, p):
        """augassign: ('+=' | '-=' | '*=' | '/=' | '%=' | '&=' | '|=' | '^=' |
            '<<=' | '>>=' | '**=' | '//=')
        """
        p[0] = p[1:]

    #
    # For normal assignments, additional restrictions enforced 
    # by the interpreter
    #
    def p_(self, p):
        """del_stmt: 'del' exprlist
        """
        p[0] = p[1:]

    def p_(self, p):
        """pass_stmt : 'pass'
        """
        p[0] = p[1:]

    def p_(self, p):
        """flow_stmt: break_stmt | continue_stmt | return_stmt | raise_stmt | yield_stmt
        """
        p[0] = p[1:]

    def p_(self, p):
        """break_stmt: 'break'
        """
        p[0] = p[1:]

    def p_(self, p):
        """continue_stmt: 'continue'
        """
        p[0] = p[1:]

    def p_(self, p):
        """return_stmt: 'return' [testlist]
        """
        p[0] = p[1:]

    def p_(self, p):
        """yield_stmt: yield_expr
        """
        p[0] = p[1:]

    def p_(self, p):
        """raise_stmt: 'raise' [test ['from' test]]
        """
        p[0] = p[1:]

    def p_(self, p):
        """import_stmt: import_name | import_from
        """
        p[0] = p[1:]

    def p_(self, p):
        """import_name: 'import' dotted_as_names
        """
        p[0] = p[1:]

    #
    # note below: the ('.' | '...') is necessary because '...' is 
    # tokenized as ELLIPSIS
    #
    def p_(self, p):
        """import_from: ('from' (('.' | '...')* dotted_name | ('.' | '...')+)
              'import' ('*' | '(' import_as_names ')' | import_as_names))
        """
        p[0] = p[1:]

    def p_(self, p):
        """import_as_name: NAME ['as' NAME]
        """
        p[0] = p[1:]

    def p_(self, p):
        """dotted_as_name: dotted_name ['as' NAME]
        """
        p[0] = p[1:]

    def p_(self, p):
        """import_as_names: import_as_name (',' import_as_name)* [',']
        """
        p[0] = p[1:]

    def p_(self, p):
        """dotted_as_names: dotted_as_name (',' dotted_as_name)*
        """
        p[0] = p[1:]

    def p_(self, p):
        """dotted_name: NAME ('.' NAME)*
        """
        p[0] = p[1:]

    def p_(self, p):
        """global_stmt: 'global' NAME (',' NAME)*
        """
        p[0] = p[1:]

    def p_(self, p):
        """nonlocal_stmt: 'nonlocal' NAME (',' NAME)*
        """
        p[0] = p[1:]

    def p_(self, p):
        """assert_stmt: 'assert' test [',' test]
        """
        p[0] = p[1:]

    def p_(self, p):
        """compound_stmt: if_stmt | while_stmt | for_stmt | try_stmt | with_stmt | funcdef | classdef | decorated
        """
        p[0] = p[1:]

    def p_(self, p):
        """if_stmt: 'if' test ':' suite ('elif' test ':' suite)* ['else' ':' suite]
        """
        p[0] = p[1:]

    def p_(self, p):
        """while_stmt: 'while' test ':' suite ['else' ':' suite]
        """
        p[0] = p[1:]

    def p_(self, p):
        """for_stmt: 'for' exprlist 'in' testlist ':' suite ['else' ':' suite]
        """
        p[0] = p[1:]

    def p_(self, p):
        """try_stmt: ('try' ':' suite
           ((except_clause ':' suite)+
            ['else' ':' suite]
            ['finally' ':' suite] |
           'finally' ':' suite))
        """
        p[0] = p[1:]

    def p_(self, p):
        """with_stmt: 'with' with_item (',' with_item)*  ':' suite
        """
        p[0] = p[1:]

    def p_(self, p):
        """with_item: test ['as' expr]
        """
        p[0] = p[1:]

    def p_(self, p):
        """except_clause: 'except' [test ['as' NAME]]
        """
        p[0] = p[1:]

    def p_(self, p):
        """suite: simple_stmt | NEWLINE INDENT stmt+ DEDENT
        """
        p[0] = p[1:]

    def p_(self, p):
        """
        """
        p[0] = p[1:]



    """

test: or_test ['if' or_test 'else' test] | lambdef
test_nocond: or_test | lambdef_nocond
lambdef: 'lambda' [varargslist] ':' test
lambdef_nocond: 'lambda' [varargslist] ':' test_nocond
or_test: and_test ('or' and_test)*
and_test: not_test ('and' not_test)*
not_test: 'not' not_test | comparison
comparison: expr (comp_op expr)*
# <> isn't actually a valid comparison operator in Python. It's here for the
# sake of a __future__ import described in PEP 401
comp_op: '<'|'>'|'=='|'>='|'<='|'<>'|'!='|'in'|'not' 'in'|'is'|'is' 'not'
star_expr: '*' expr
expr: xor_expr ('|' xor_expr)*
xor_expr: and_expr ('^' and_expr)*
and_expr: shift_expr ('&' shift_expr)*
shift_expr: arith_expr (('<<'|'>>') arith_expr)*
arith_expr: term (('+'|'-') term)*
term: factor (('*'|'/'|'%'|'//') factor)*
factor: ('+'|'-'|'~') factor | power
power: atom trailer* ['**' factor]
atom: ('(' [yield_expr|testlist_comp] ')' |
       '[' [testlist_comp] ']' |
       '{' [dictorsetmaker] '}' |
       NAME | NUMBER | STRING+ | '...' | 'None' | 'True' | 'False')
testlist_comp: (test|star_expr) ( comp_for | (',' (test|star_expr))* [','] )
trailer: '(' [arglist] ')' | '[' subscriptlist ']' | '.' NAME
subscriptlist: subscript (',' subscript)* [',']
subscript: test | [test] ':' [test] [sliceop]
sliceop: ':' [test]
exprlist: (expr|star_expr) (',' (expr|star_expr))* [',']
testlist: test (',' test)* [',']
dictorsetmaker: ( (test ':' test (comp_for | (',' test ':' test)* [','])) |
                  (test (comp_for | (',' test)* [','])) )

classdef: 'class' NAME ['(' [arglist] ')'] ':' suite

arglist: (argument ',')* (argument [',']
                         |'*' test (',' argument)* [',' '**' test] 
                         |'**' test)
# The reason that keywords are test nodes instead of NAME is that using NAME
# results in an ambiguity. ast.c makes sure it's a NAME.
argument: test [comp_for] | test '=' test  # Really [keyword '='] test
comp_iter: comp_for | comp_if
comp_for: 'for' exprlist 'in' or_test [comp_iter]
comp_if: 'if' test_nocond [comp_iter]

# not used in grammar, but may appear in "node" passed from Parser to Compiler
encoding_decl: NAME

yield_expr: 'yield' [yield_arg]
yield_arg: 'from' test | testlist
"""

    def p_empty(self, p):
        'empty : '
        p[0] = None

    def p_error(self, p):
        if p:
            msg = 'code: {0}'.format(p.value),
            self._parse_error(msg, self.currloc(lineno=p.lineno,
                                   column=self.lexer.token_col(p)))
        else:
            self._parse_error('no further code', '')

