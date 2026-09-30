"""Parse the save into editable records (text based, round-trip safe)."""
import re
from lib import *

THING_RE = re.compile(r'<thing Class="([\w.]+)">(.*?)</thing>', re.S)


def g(b, t):
    m = re.search(r'<%s>(.*?)</%s>' % (t, t), b)
    return m.group(1) if m else None


class Rec:
    __slots__ = ('cls', 'raw', 'd', 'id', 'pos', 'rot', 'stuff', 'faction', 'keep', 'deleted', 'stack')

    def __init__(self, cls, raw):
        self.cls = cls
        self.raw = raw
        self.d = g(raw, 'def')
        self.id = g(raw, 'id')
        m = re.search(r'<pos>\((-?\d+), (-?\d+), (-?\d+)\)</pos>', raw)
        self.pos = (int(m.group(1)), int(m.group(3))) if m else None
        self.rot = int(g(raw, 'rot') or 0)
        self.stuff = g(raw, 'stuff')
        self.faction = g(raw, 'faction')
        self.deleted = False
        self.stack = int(g(raw, 'stackCount') or 1)

    def set_pos(self, x, z):
        self.raw = re.sub(r'<pos>\(-?\d+, (-?\d+), -?\d+\)</pos>', lambda m: '<pos>(%d, %s, %d)</pos>' % (x, m.group(1), z), self.raw, count=1)
        self.pos = (x, z)

    def set_rot(self, r):
        if re.search(r'<rot>\d</rot>', self.raw):
            self.raw = re.sub(r'<rot>\d</rot>', '<rot>%d</rot>' % r, self.raw, count=1)
        elif r != 0:
            self.raw = self.raw.replace('</pos>', '</pos><rot>%d</rot>' % r, 1)
        self.rot = r

    def set_tag(self, tag, val):
        if re.search(r'<%s>.*?</%s>' % (tag, tag), self.raw):
            self.raw = re.sub(r'<%s>.*?</%s>' % (tag, tag), '<%s>%s</%s>' % (tag, val, tag), self.raw, count=1)
        else:
            self.raw = self.raw.replace('</thing>', '<%s>%s</%s></thing>' % (tag, val, tag))


class SaveModel:
    def __init__(self):
        self.s = load()
        ms = self.s.find('<maps>')
        a = self.s.find('<things>', ms)
        a2 = a + len('<things>')
        b = self.s.find('</things>', a2)
        self.head = self.s[:a2]
        self.tail = self.s[b:]
        body = self.s[a2:b]
        self.parts = []          # alternating text / Rec
        pos = 0
        self.recs = []
        for m in THING_RE.finditer(body):
            if m.start() > pos:
                self.parts.append(body[pos:m.start()])
            r = Rec(m.group(1), m.group(0))
            self.parts.append(r)
            self.recs.append(r)
            pos = m.end()
        self.parts.append(body[pos:])
        self.new = []            # new raw thing strings
        self.next_id = int(re.search(r'<nextThingID>(\d+)</nextThingID>', self.s).group(1))

    def nid(self):
        self.next_id += 1
        return self.next_id - 1

    def assemble(self):
        out = [self.head]
        for p in self.parts:
            if isinstance(p, str):
                out.append(p)
            elif not p.deleted:
                out.append(p.raw)
        for n in self.new:
            out.append('\n\t\t\t\t\t' + n)
        out.append(self.tail)
        txt = ''.join(out)
        txt = re.sub(r'<nextThingID>\d+</nextThingID>', '<nextThingID>%d</nextThingID>' % self.next_id, txt, count=1)
        return txt


if __name__ == '__main__':
    M = SaveModel()
    body_rt = M.assemble()
    print(len(M.recs), body_rt == M.s)
