import re,base64,zlib,struct,collections
FN="/home/user/first/mirella fans.rws"
def h(n):
    x=23
    for c in n: x=(x*31+ord(c))&0xFFFFFFFF
    return x%65535
def load(): return open(FN,encoding="utf-8-sig").read()
def dec(s,tag,name):
    st=s.find('<%s>'%tag)
    m=re.search(r'<%s>\s*(.*?)\s*</%s>'%(name,name),s[st:],re.S)
    return zlib.decompress(base64.b64decode(re.sub(r'\s','',m.group(1))),-15)
def enc(b):
    c=zlib.compressobj(6,zlib.DEFLATED,-15); d=c.compress(b)+c.flush()
    return base64.b64encode(d).decode()
