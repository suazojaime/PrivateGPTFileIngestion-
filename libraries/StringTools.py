from string import uppercase, lowercase
from cgi import escape
import minestar

logger = minestar.initApp()

def isEmpty(s):
    """Return True if string is None or consisting only of zero or more whitespaces.

    >>> isEmpty(None)
    True
    >>> isEmpty('')
    True
    >>> isEmpty(' ')
    True
    >>> isEmpty("\t")
    True
    >>> isEmpty('Not Empty')
    False
    """
    return not s or not s.strip()

def mixedCaseSplit(s):
    """Split a mixedCaseWord into a list of words.

    >>> mixedCaseSplit('hello')
    ['hello']
    >>> mixedCaseSplit('helloWorld')
    ['hello', 'World']
    >>> mixedCaseSplit('helloURL')
    ['hello', 'URL']
    """
    result = []
    i = 0
    word_start = 0
    previous_c = None
    for c in s:
        if c in uppercase and i > 0 and previous_c in lowercase:
            this_word = s[word_start:i]
            result.append(this_word)
            word_start = i
        i = i + 1
        previous_c = c
    result.append(s[word_start:])
    return result

def escapeHtml(s):
    "wrapper around escape in the cgi module to overcome security"
    return escape(s)

def quoteString(s):
    "put double-quotes around the String s"
    return '"%s"' % s


def splitString(s, separator=' ', escape='\\', quote='"', skipWhiteSpace=True):
    """Split a string by a separator character, handling quotes and escapes."""
    s = s.strip()
    tokens = []
    quoting = False
    escaping = False
    skippingWhiteSpace = False
    token = None
    for ch in s:
        # Skip whitespace if required.
        if skippingWhiteSpace:
            if ch == ' ':
                continue
            skippingWhiteSpace = False
        # Check for escape character.
        escaping = (ch == escape and not escaping)
        if escaping:
            continue
        # Check for quote character.
        if ch == quote:
            quoting = not quoting
        # Check for separator character.
        if ch == separator and not escaping and not quoting:
            if token is None:
                token = ""
            tokens.append(token.strip())
            escaping = False
            quoting = False
            token = ""
            skippingWhiteSpace = skipWhiteSpace
            continue
        # Add character to the current token.
        if token is None:
            token = ""
        token = token + ch
    # Add token, if remaining.
    if token is not None:
        tokens.append(token.strip())
    return tokens

# Test harness
if __name__ == '__main__':
    import doctest
    doctest.testmod()
