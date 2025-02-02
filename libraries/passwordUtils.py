"""
Utilities to obfuscate and deobfuscate passwords to use with Jetty.
See https://www.eclipse.org/jetty/documentation/9.4.x/configuring-security-secure-passwords.html
These are python equivalents to the Java methods in org.eclipse.jetty.util.security.Password
"""

OBF_PREFIX = 'OBF:'

def obfuscate(plaintext):
    ciphertext = OBF_PREFIX
    if isinstance(plaintext, bytes):
        plaintext = plaintext.decode('utf-8')
    b = bytearray(plaintext, 'utf-8')
    l = len(b)
    for i in range(0, l):
        b1, b2 = b[i], b[l - (i + 1)]
        if b1 < 0 or b2 < 0:
            i0 = (0xff & b1) * 256 + (0xff & b2)
            ciphertext += 'U0000'[0:5 - len(x)] + x
        else:
            i1, i2 = 127 + b1 + b2, 127 + b1 - b2
            i0 = i1 * 256 + i2
            x = _to36(i0)
            j0 = int(x, 36)
            j1, j2 = i0 / 256, i0 % 256
            ciphertext += '000'[0:4 - len(x)] + x
    return ciphertext


def deobfuscate(ciphertext):
    if ciphertext.startswith(OBF_PREFIX):
        ciphertext = ciphertext[len(OBF_PREFIX):]
    plaintext = ""
    for i in range(0, len(ciphertext), 4):
        t = ciphertext[i:i + 4]
        i0 = int(t, 36)
        i1, i2 = divmod(i0, 256)
        x = (i1 + i2 - 254) >> 1
        plaintext += chr(x)
    return plaintext


def _to36(value):
    if value == 0:
        return '0'
    if value < 0:
        sign = '-'
        value = -value
    else:
        sign = ''
    result = []
    while value:
        value, mod = divmod(value, 36)
        result.append('0123456789abcdefghijklmnopqrstuvwxyz'[mod])
    return sign + ''.join(reversed(result))
