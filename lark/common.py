import re
import sre_parse
import sys

Py36 = (sys.version_info[:2] >= (3, 6))

class GrammarError(Exception):
    pass

class ParseError(Exception):
    pass


class UnexpectedToken(ParseError):
    def __init__(self, token, expected, seq, index):
        self.token = token
        self.expected = expected
        self.line = getattr(token, 'line', '?')
        self.column = getattr(token, 'column', '?')

        try:
            context = ' '.join(['%r(%s)' % (t.value, t.type) for t in seq[index:index+5]])
        except AttributeError:
            context = seq[index:index+5]
        except TypeError:
            context = "<no context>"
        message = ("Unexpected token %r at line %s, column %s.\n"
                   "Expected: %s\n"
                   "Context: %s" % (token, self.line, self.column, expected, context))

        super(UnexpectedToken, self).__init__(message)



def is_terminal(sym):
    return isinstance(sym, Terminal) or sym.isupper() or sym == '$end'


class LexerConf:
    def __init__(self, tokens, ignore=(), postlex=None):
        self.tokens = tokens
        self.ignore = ignore
        self.postlex = postlex

class ParserConf:
    def __init__(self, rules, callback, start):
        assert all(len(r) == 4 for r in rules)
        self.rules = rules
        self.callback = callback
        self.start = start



class Pattern(object):
    def __init__(self, value, flags=()):
        self.value = value
        self.flags = frozenset(flags)

    def __repr__(self):
        return repr(self.to_regexp())

    # Pattern Hashing assumes all subclasses have a different priority!
    def __hash__(self):
        return hash((type(self), self.value, self.flags))
    def __eq__(self, other):
        return type(self) == type(other) and self.value == other.value and self.flags == other.flags

    if Py36:
        # Python 3.6 changed syntax for flags in regular expression
        def _get_flags(self, value):
            for f in self.flags:
                value = ('(?%s:%s)' % (f, value))
            return value

    else:
        def _get_flags(self, value):
            for f in self.flags:
                value = ('(?%s)' % f) + value
            return value

class PatternStr(Pattern):
    def to_regexp(self):
        return self._get_flags(re.escape(self.value))

    @property
    def min_width(self):
        return len(self.value)
    max_width = min_width

class PatternRE(Pattern):
    def to_regexp(self):
        return self._get_flags(self.value)

    @property
    def min_width(self):
        return sre_parse.parse(self.to_regexp()).getwidth()[0]
    @property
    def max_width(self):
        return sre_parse.parse(self.to_regexp()).getwidth()[1]

class TokenDef(object):
    def __init__(self, name, pattern, priority=1):
        assert isinstance(pattern, Pattern), pattern
        self.name = name
        self.pattern = pattern
        self.priority = priority

    def __repr__(self):
        return '%s(%r, %r)' % (type(self).__name__, self.name, self.pattern)


class Terminal:
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return '%r' % self.data

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.data == other.data
    def __hash__(self):
        return hash(self.data)


class Terminal_Regexp(Terminal):
    def __init__(self, name, regexp):
        Terminal.__init__(self, regexp)
        self.name = name
        self.match = re.compile(regexp).match

class Terminal_Token(Terminal):
    def match(self, other):
        return self.data == other.type

