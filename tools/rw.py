#!/usr/bin/env python3
"""rw - compact RimWorld save editor (edits the already-built save in place, tiny output).

  python3 rw.py -c "show 114 107 160 157; put Bed 120 140 0; wall 115 140 130 140; save"
  python3 rw.py script.txt

Commands (coords are world x z; z grows north; ';' or newline separates commands):
  show X0 Z0 X1 Z1 [w]      ascii map of region (w = also show wires as ~)
  info X Z                  what stands on the cell
  put DEF X Z [rot] [stuff] spawn a building (clone of an existing one, full HP, auto-wired if powered)
  wall X0 Z0 X1 Z1 [stuff]  straight wall line (horizontal or vertical)
  box X0 Z0 X1 Z1 [stuff]   wall outline of a rectangle
  door X Z [stuff]          door (replaces wall on that cell)
  rm X0 Z0 [X1 Z1] [DEF]    delete buildings in region (optionally only DEF)
  mv X Z X2 Z2 [DEF]        move a building (keeps bills, owner, contents)
  rot X Z R [DEF]           rotate
  floor X0 Z0 X1 Z1 TERRAIN set floor (TileMarble WoodPlankFloor Concrete SterileTile TileSandstone Soil ...)
  roof X0 Z0 X1 Z1 on|off   constructed roof
  wire X0 Z0 X1 Z1          lay conduits on every cell of region
  autowire                  connect every unpowered consumer to the nearest conduit
  hide                      turn all visible wires into underground cables
  clear X0 Z0 X1 Z1         remove trees/plants in region
  hp                        give every building without health its proper default
  zone ID X0 Z0 X1 Z1       replace stockpile zone ID cells with the rectangle (ID = zone number)
  save [path]               write (default: overwrites the edited save)
"""
import sys, re, heapq, collections, shlex
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
from model import SaveModel, Rec
from lib import h
from geom import rect
from layout import SIZES, POWERED
import apply_build as AB
import apply_world as AW

EDITED = '/home/user/first/mirella fans_edited.rws'
CONDUIT = 'HiddenConduit'   # underground cable (invisible)
BLD_SKIP = {'Pawn', 'Plant', 'DeadPlant', 'Filth', 'Corpse', 'Medicine', 'Apparel', 'ThingWithComps', 'UnfinishedThing', 'MinifiedThing', 'Thing'}
CH = {'Wall': '#', 'Door': '+', 'Bed': 'b', 'BedGuest': 'g', 'DiningChair': 'c', 'Table2x2c': 'T', 'Shelf': 's', 'Heater': 'H',
      'Cooler': 'C', 'Vent': 'v', 'SolarGenerator': 'S', 'Battery': 'B', 'Turret_MiniTurret': 'M', 'Turret_Mortar': 'N',
      'StandingLamp': 'l', 'FermentingBarrel': 'u', 'Grave': 'G', 'FueledStove': 'F', 'PowerConduit': '~', 'HiddenConduit': '~'}


def is_bld(r):
    return r.cls.startswith('Building') or r.cls == 'Building' or r.cls.endswith('GuestBed') or r.cls.endswith('ManagerStation') \
        or r.cls.startswith('Building_')


class Ed:
    def __init__(self, path=EDITED):
        self.M = SaveModel(path)
        self.path = path
        self.T = AB.make_templates(self.M)
        for r in self.M.recs:                      # keep class for spawning
            if r.d in self.T and not hasattr(self.T[r.d], 'cls'):
                self.T[r.d].cls = r.cls
        self.terr = self.roof = None
        self.zones_touched = {}
        self.out = []
        self.index()

    # ------------------------------------------------------------ index
    def foot(self, r):
        return rect(r.pos[0], r.pos[1], SIZES.get(r.d, (1, 1)), r.rot)

    def index(self):
        self.cell = collections.defaultdict(list)
        for r in self.M.recs:
            if r.deleted or not r.pos or not is_bld(r) or r.d == 'SteamGeyser':
                continue
            for c in self.foot(r):
                self.cell[c].append(r)

    def say(self, *a):
        self.out.append(' '.join(str(x) for x in a))

    # ------------------------------------------------------------ views
    def show(self, x0, z0, x1, z1, wires=False):
        legend = {}
        rows = []
        for z in range(z1, z0 - 1, -1):
            row = ''
            for x in range(x0, x1 + 1):
                ch = '.'
                rs = self.cell.get((x, z), [])
                pick = None
                for r in rs:
                    if r.d in ('PowerConduit', 'HiddenConduit'):
                        if wires and pick is None: pick = r
                        continue
                    if r.d == 'Wall' and any(q.d in ('Cooler', 'Vent') for q in rs):
                        continue
                    if pick is None or pick.d in ('PowerConduit', 'HiddenConduit', 'Wall'):
                        pick = r
                if pick:
                    ch = CH.get(pick.d)
                    if not ch:
                        ch = legend.setdefault(pick.d, chr(ord('A') + len(legend) % 26) if False else None)
                        if ch is None:
                            for cand in (pick.d[0].lower(), pick.d[0].upper(), *'aeiopqrwxyzkdfjmnL0123456789@%&*=$^?'):
                                if cand not in CH.values() and cand not in legend.values():
                                    ch = cand; break
                            ch = ch or '?'
                            legend[pick.d] = ch
                row += ch
            rows.append('%3d %s' % (z, row))
        head = '    ' + ''.join(str((x // 10) % 10) if x % 10 == 0 else ' ' for x in range(x0, x1 + 1))
        self.say(head); self.out.extend(rows)
        self.say('legend:', ' '.join('%s=%s' % (v, k) for k, v in legend.items()), '| # wall + door b bed g guestbed c chair T table s shelf H heater C cooler v vent l lamp M turret ~ wire')

    def info(self, x, z):
        rs = self.cell.get((x, z), [])
        if not rs: self.say('(%d,%d) empty' % (x, z))
        for r in rs:
            hp = re.search(r'<health>(\d+)', r.raw)
            self.say('(%d,%d)' % (x, z), r.d, r.id, 'rot', r.rot, 'stuff', r.stuff, 'hp', hp.group(1) if hp else '-', 'pos', r.pos)

    # ------------------------------------------------------------ building
    def _add_rec(self, raw, cls):
        r = Rec(cls, raw)
        self.M.parts.append(r); self.M.recs.append(r)
        for c in self.foot(r):
            self.cell[c].append(r)
        return r

    def spawn(self, d, x, z, rot=0, stuff=None, **o):
        if d not in self.T:
            raise KeyError('no template for %s (spawn by cloning: only defs already on the map)' % d)
        M, T = self.M, self.T
        t = T[d]
        if d in ('Bed', 'BedGuest'):
            raw, nid = AB.new_thing(M, T, d, x, z, rot, stuff or 'WoodLog')
            raw = re.sub(r'<assignedPawns>.*?</assignedPawns>', '<assignedPawns />', raw, flags=re.S)
            raw = re.sub(r'<forOwnerType>.*?</forOwnerType>', '', raw)
            raw = re.sub(r'<medical>.*?</medical>', '', raw)
            raw = re.sub(r'<quality>\w+</quality>', '<quality>Normal</quality>', raw)
            if o.get('role') == 'prisoner': raw = raw.replace('</thing>', '<forOwnerType>Prisoner</forOwnerType></thing>')
            if o.get('role') == 'medical': raw = raw.replace('<alreadySetDefaultMed>', '<medical>True</medical><alreadySetDefaultMed>')
        elif d == 'Turret_MiniTurret':
            raw, nid = AB.new_thing(M, T, d, x, z, rot, 'Steel')
            gm = re.search(r'Gun_MiniTurret(\d+)', raw)
            raw = raw.replace(gm.group(1), str(M.nid()))
            raw = re.sub(r'<lastShotTick>-?\d+</lastShotTick>', '<lastShotTick>-999999</lastShotTick>', raw)
        elif d == 'Shelf':
            raw, nid = AB.new_thing(M, T, d, x, z, rot, stuff or 'WoodLog')
            if o.get('filt'):
                raw = re.sub(r'<allowedDefs>.*?</allowedDefs>', lambda m: '<allowedDefs>%s</allowedDefs>' % ''.join('<li>%s</li>' % q for q in o['filt']), raw, flags=re.S)
        elif d == 'FueledStove':
            raw, nid = AB.new_thing(M, T, d, x, z, rot)
            raw = re.sub(r'<billStack>.*?</billStack>', '<billStack><bills /></billStack>', raw, flags=re.S)
        elif d in ('Heater', 'Cooler'):
            raw, nid = AB.new_thing(M, T, d, x, z, rot)
            raw = re.sub(r'<targetTemperature>[^<]*</targetTemperature>', '<targetTemperature>%d</targetTemperature>' % o.get('target', 21), raw)
        elif d == 'Battery':
            raw, nid = AB.new_thing(M, T, d, x, z, rot)
            raw = re.sub(r'<storedPower>[^<]*</storedPower>', '<storedPower>600</storedPower>', raw)
        elif d in ('Grave', 'Corpse'):
            raise KeyError('graves carry corpses; move existing ones with mv')
        else:
            raw, nid = AB.new_thing(M, T, d, x, z, rot, stuff)
        r = self._add_rec(raw, t.cls)
        if d in POWERED:
            self.wire_rec(r)
        return r

    def put(self, d, x, z, rot=0, stuff=None):
        r = self.spawn(d, x, z, rot, stuff)
        self.say('put', d, x, z, r.id)

    def wall(self, x0, z0, x1, z1, stuff='BlocksGranite'):
        n = 0
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                if any(q.d in ('Wall', 'Door') for q in self.cell.get((x, z), [])): continue
                self.spawn('Wall', x, z, 0, stuff); n += 1
        self.say('walls +%d' % n)

    def box(self, x0, z0, x1, z1, stuff='BlocksGranite'):
        for a in ((x0, z0, x1, z0), (x0, z1, x1, z1), (x0, z0, x0, z1), (x1, z0, x1, z1)):
            self.wall(*a, stuff)

    def door(self, x, z, stuff='Steel'):
        for q in list(self.cell.get((x, z), [])):
            if q.d == 'Wall': q.deleted = True
        self.index()
        self.spawn('Door', x, z, 0, stuff)
        self.say('door', x, z)

    def rm(self, x0, z0, x1=None, z1=None, d=None):
        if x1 is None: x1, z1 = x0, z0
        if isinstance(x1, str): d, x1, z1 = x1, x0, z0
        n = 0
        for r in self.M.recs:
            if r.deleted or not r.pos or not is_bld(r): continue
            if min(x0, x1) <= r.pos[0] <= max(x0, x1) and min(z0, z1) <= r.pos[1] <= max(z0, z1) and (d is None or r.d == d):
                if r.d in ('SteamGeyser',): continue
                r.deleted = True; n += 1
        self.index(); self.say('removed', n)

    def mv(self, x, z, x2, z2, d=None):
        rs = [r for r in self.cell.get((x, z), []) if r.d not in ('PowerConduit', 'HiddenConduit') and (d is None or r.d == d)]
        for r in rs[:1]:
            r.set_pos(x2, z2)
            r.raw = re.sub(r'<parentThing>[^<]*</parentThing>', '<parentThing>null</parentThing>', r.raw)
            self.say('moved', r.d, r.id)
        self.index()
        for r in rs[:1]:
            if r.d in POWERED: self.wire_rec(r)

    def rot(self, x, z, rot, d=None):
        for r in self.cell.get((x, z), []):
            if d is None or r.d == d:
                r.set_rot(rot); self.say('rot', r.d, rot); break
        self.index()

    # ------------------------------------------------------------ terrain / roof
    def _grids(self):
        if self.terr is None:
            self.terr = AW.get_grid(self.M.head, 'terrainGrid', 'topGridDeflate')
            self.roof = AW.get_grid(self.M.head, 'roofGrid', 'roofsDeflate')

    def floor(self, x0, z0, x1, z1, name):
        self._grids(); v = h(name)
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                self.terr[z * 250 + x] = v
        self.say('floor', name)

    def roof_(self, x0, z0, x1, z1, mode):
        self._grids()
        v = AW.ROOF_CONSTRUCTED if mode == 'on' else 0
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                if self.roof[z * 250 + x] not in AW.ROOF_ROCK:
                    self.roof[z * 250 + x] = v
        self.say('roof', mode)

    def zone(self, zid, x0, z0, x1, z1):
        cells = [(x, z) for z in range(min(z0, z1), max(z0, z1) + 1) for x in range(min(x0, x1), max(x0, x1) + 1)]
        self.M.head = AW.set_zone_cells(self.M.head, zid, cells)
        self.say('zone', zid, len(cells), 'cells')

    # ------------------------------------------------------------ power
    def trans(self):
        tr = {}
        for r in self.M.recs:
            if r.deleted or not r.pos: continue
            if r.d in ('PowerConduit', 'HiddenConduit', 'Battery', 'SolarGenerator', 'WindTurbine'):
                for c in (self.foot(r) if r.d != 'PowerConduit' and r.d != 'HiddenConduit' else [r.pos]):
                    tr[c] = r
        return tr

    def wire_rec(self, r, tr=None):
        tr = tr if tr is not None else self.trans()
        x, z = r.pos
        nb = lambda c: ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1))
        for c in [(x, z)] + list(nb((x, z))):
            if c in tr:
                r.raw = AB.set_raw_tag(r.raw, 'parentThing', 'Thing_' + tr[c].id); return True
        solid = {c for c, rs in self.cell.items() if any(q.d not in ('PowerConduit', 'HiddenConduit', 'Wall', 'Door', 'Heater', 'StandingLamp', 'Vent', 'Cooler', 'Battery', 'SolarGenerator') for q in rs)}
        walls = {c for c, rs in self.cell.items() if any(q.d == 'Wall' for q in rs)}
        pq = []; dist = {}; prev = {}
        for s in [(x, z)] + list(nb((x, z))):
            dist[s] = 0; prev[s] = None; heapq.heappush(pq, (0, s))
        while pq:
            dc, cur = heapq.heappop(pq)
            if dc > dist[cur]: continue
            if cur in tr and cur not in [(x, z)]:
                path = []; c = cur
                while c is not None: path.append(c); c = prev[c]
                for c in path:
                    if c not in tr:
                        raw, nid = AB.new_thing(self.M, self.T, CONDUIT, c[0], c[1])
                        raw = AB.set_raw_tag(raw, 'parentThing', 'null')
                        nr = self._add_rec(raw, 'Building'); tr[c] = nr
                r.raw = AB.set_raw_tag(r.raw, 'parentThing', 'Thing_' + tr[cur].id)
                return True
            for n in nb(cur):
                if n in solid and n not in tr: continue
                nd = dc + (6 if n in walls else 1)
                if nd < dist.get(n, 1e9):
                    dist[n] = nd; prev[n] = cur; heapq.heappush(pq, (nd, n))
        self.say('NO POWER PATH', r.d, r.pos); return False

    def wire(self, x0, z0, x1, z1):
        tr = self.trans(); n = 0
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                if (x, z) in tr: continue
                raw, nid = AB.new_thing(self.M, self.T, CONDUIT, x, z)
                self._add_rec(AB.set_raw_tag(raw, 'parentThing', 'null'), 'Building'); n += 1
        self.say('conduits +%d' % n)

    def autowire(self):
        tr = self.trans(); n = bad = 0
        ids = {r.id for r in tr.values()}
        for r in list(self.M.recs):
            if r.deleted or not r.pos or r.d not in POWERED: continue
            m = re.search(r'<parentThing>Thing_(\w+)</parentThing>', r.raw)
            if m and m.group(1) in ids: continue
            if self.wire_rec(r, tr): n += 1
            else: bad += 1
        self.say('autowired', n, 'failed', bad)

    def hide(self):
        """convert every visible PowerConduit into an underground HiddenConduit"""
        t = self.T.get('HiddenConduit')
        hp = re.search(r'<health>(\d+)</health>', t.raw).group(1) if t and re.search(r'<health>(\d+)</health>', t.raw) else None
        n = 0
        for r in self.M.recs:
            if r.deleted or r.d != 'PowerConduit': continue
            r.raw = r.raw.replace('<def>PowerConduit</def>', '<def>HiddenConduit</def>')
            r.raw = re.sub(r'<id>PowerConduit(\d+)</id>', r'<id>HiddenConduit\1</id>', r.raw)
            if hp: r.raw = re.sub(r'<health>\d+</health>', '<health>%s</health>' % hp, r.raw)
            r.d = 'HiddenConduit'; r.id = 'HiddenConduit' + r.id[len('PowerConduit'):]; n += 1
        rx = re.compile(r'Thing_PowerConduit(\d+)')
        for r in self.M.recs:
            if not r.deleted and 'Thing_PowerConduit' in r.raw:
                r.raw = rx.sub(r'Thing_HiddenConduit\1', r.raw)
        self.M.head = rx.sub(r'Thing_HiddenConduit\1', self.M.head)
        self.index(); self.say('hidden conduits', n)

    def clear(self, x0, z0, x1, z1):
        n = 0
        for r in self.M.recs:
            if r.deleted or not r.pos or r.cls not in ('Plant', 'DeadPlant'): continue
            if min(x0, x1) <= r.pos[0] <= max(x0, x1) and min(z0, z1) <= r.pos[1] <= max(z0, z1):
                r.deleted = True; n += 1
        self.say('plants cleared', n)

    # ------------------------------------------------------------ bills / stock
    @staticmethod
    def _spans(raw):
        """(start,end,recipe) of every Bill_* <li> inside the bill stack"""
        out = []; i = 0
        while True:
            s = raw.find('<li Class="Bill_', i)
            if s < 0: break
            depth = 0; j = s
            for m in re.finditer(r'<li\b[^>]*?(/?)>|</li>', raw[s:]):
                t = m.group(0)
                if t == '</li>': depth -= 1
                elif not t.endswith('/>'): depth += 1
                if depth == 0:
                    j = s + m.end(); break
            rec = re.search(r'<recipe>(\w+)</recipe>', raw[s:j]).group(1)
            out.append((s, j, rec)); i = j
        return out

    def _bill_tmpl(self, plain):
        for r in self.M.recs:
            if r.deleted or '<billStack>' not in r.raw: continue
            for s, e, rc in self._spans(r.raw):
                head = r.raw[s:s + 40]
                if plain != ('Bill_ProductionWithUft' in head):
                    return r.raw[s:e]
        raise KeyError('no bill template')

    def bill(self, bench, recipe, count, ings=None, mode='TargetCount'):
        """bill BENCH RECIPE COUNT [ING1,ING2] [TargetCount|RepeatCount|Forever]"""
        name, _, idx = bench.partition('@')
        rec = [r for r in self.M.recs if not r.deleted and r.d == name][int(idx or 0)]
        plain = recipe.startswith('Cook') or recipe in ('Make_Kibble',)
        if plain:
            t = self._bill_tmpl(True)
            keep_filter = True
        else:
            t = self._bill_tmpl(False); keep_filter = False
        bid = int(re.search(r'<nextBillID>(\d+)</nextBillID>', self.M.head).group(1))
        self.M.head = re.sub(r'<nextBillID>\d+</nextBillID>', '<nextBillID>%d</nextBillID>' % (bid + 1), self.M.head, count=1)
        t = re.sub(r'<loadID>\d+</loadID>', '<loadID>%d</loadID>' % bid, t, count=1)
        t = re.sub(r'<recipe>\w+</recipe>', '<recipe>%s</recipe>' % recipe, t, count=1)
        if ings:
            t = re.sub(r'<ingredientFilter>.*?</ingredientFilter>', lambda m: AB.filter_xml(ings.split(',')), t, count=1, flags=re.S)
        t = re.sub(r'<repeatMode>\w+</repeatMode>', '<repeatMode>%s</repeatMode>' % mode, t, count=1)
        t = re.sub(r'<targetCount>\d+</targetCount>', '<targetCount>%d</targetCount>' % count, t, count=1)
        t = re.sub(r'<repeatCount>\d+</repeatCount>', '<repeatCount>%d</repeatCount>' % count, t, count=1)
        if '<bills />' in rec.raw:
            rec.raw = rec.raw.replace('<bills />', '<bills>' + t + '</bills>', 1)
        else:
            i = rec.raw.rfind('</bills>')
            rec.raw = rec.raw[:i] + t + rec.raw[i:]
        self.say('bill', bench, recipe, count)

    def unbill(self, bench, recipe):
        n = 0
        for rec in self.M.recs:
            if rec.deleted or rec.d != bench or '<billStack>' not in rec.raw: continue
            for s, e, rc in reversed(self._spans(rec.raw)):
                if rc == recipe:
                    rec.raw = rec.raw[:s] + rec.raw[e:]; n += 1
            if '<bills>' in rec.raw and not self._spans(rec.raw):
                rec.raw = re.sub(r'<bills>\s*</bills>', '<bills />', rec.raw)
        self.say('unbill', bench, recipe, n)

    def stock(self, d, x0, z0, x1, z1, limit=999):
        """put existing item stacks of DEF one per cell into the rectangle (e.g. onto shelf cells)"""
        cells = [(x, z) for z in range(min(z0, z1), max(z0, z1) + 1) for x in range(min(x0, x1), max(x0, x1) + 1)]
        taken = {r.pos for r in self.M.recs if not r.deleted and r.pos and not is_bld(r) and r.cls not in ('Pawn', 'Plant', 'DeadPlant', 'Filth')}
        free = [c for c in cells if c not in taken]
        n = 0
        for r in self.M.recs:
            if r.deleted or r.d != d or not r.pos or is_bld(r) or r.cls == 'Pawn' or not free or n >= limit: continue
            if r.id in self.__dict__.setdefault('_stocked', set()): continue
            self._stocked.add(r.id); r.set_pos(*free.pop(0)); n += 1
        self.say('stocked', d, n)

    # ------------------------------------------------------------ diagnostics
    def leaks(self):
        """cells inside the compound reachable from outside without passing a wall/closed door"""
        bar = {c for c, rs in self.cell.items() if any(q.d in ('Wall', 'Door') for q in rs)}
        for c, rs in self.cell.items():
            if any(q.d in ('Turret_MiniTurret',) for q in rs) and c[1] >= 107 and 114 <= c[0] <= 159: pass
        start = (98, 100); seen = {start}; st = [start]
        while st:
            x, z = st.pop()
            for n in ((x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)):
                if n in seen or n in bar or not (80 <= n[0] <= 185 and 80 <= n[1] <= 170): continue
                seen.add(n); st.append(n)
        roofed = [c for c in seen if 114 < c[0] < 159 and 107 < c[1] < 156]
        self.say('leaking cells inside main compound:', len(roofed), sorted(roofed)[:12])

    def nets(self, fix=False):
        tr = self.trans()
        cells = set(tr)
        comp = {}; comps = []
        for c in cells:
            if c in comp: continue
            cid = len(comps); comps.append([]); st = [c]; comp[c] = cid
            while st:
                a = st.pop(); comps[cid].append(a)
                for n in ((a[0] + 1, a[1]), (a[0] - 1, a[1]), (a[0], a[1] + 1), (a[0], a[1] - 1)):
                    if n in cells and n not in comp: comp[n] = cid; st.append(n)
        src = max(range(len(comps)), key=lambda i: sum(1 for c in comps[i] if tr[c].d == 'SolarGenerator'))
        cons = collections.Counter()
        for r in self.M.recs:
            if r.deleted or not r.pos or r.d not in POWERED: continue
            m = re.search(r'<parentThing>Thing_(\w+)</parentThing>', r.raw)
            if not m: cons['none'] += 1; continue
            t = next((c for c, q in tr.items() if q.id == m.group(1)), None)
            cons[comp.get(t, 'missing')] += 1
        self.say('power nets:', len(comps), 'source net', src, 'sizes', sorted((len(c) for c in comps), reverse=True)[:6], 'consumers per net', dict(cons))
        if not fix: return
        for i, cc in enumerate(comps):
            if i == src: continue
            goal = set(comps[src]); pq = []; dist = {}; prev = {}
            solid = {c for c, rs in self.cell.items() if any(q.d not in ('PowerConduit', 'HiddenConduit', 'Wall', 'Door', 'Heater', 'StandingLamp', 'Vent', 'Cooler', 'Battery', 'SolarGenerator', 'Turret_MiniTurret') for q in rs)}
            walls = {c for c, rs in self.cell.items() if any(q.d == 'Wall' for q in rs)}
            for c in cc: dist[c] = 0; prev[c] = None; heapq.heappush(pq, (0, c))
            end = None
            while pq:
                d0, cur = heapq.heappop(pq)
                if d0 > dist[cur]: continue
                if cur in goal: end = cur; break
                for n in ((cur[0] + 1, cur[1]), (cur[0] - 1, cur[1]), (cur[0], cur[1] + 1), (cur[0], cur[1] - 1)):
                    if n in solid: continue
                    nd = d0 + (6 if n in walls else 1)
                    if nd < dist.get(n, 1e9): dist[n] = nd; prev[n] = cur; heapq.heappush(pq, (nd, n))
            if end is None: self.say('net', i, 'cannot be joined'); continue
            c = end; added = 0
            while c is not None:
                if c not in tr:
                    raw, nid = AB.new_thing(self.M, self.T, CONDUIT, c[0], c[1])
                    tr[c] = self._add_rec(AB.set_raw_tag(raw, 'parentThing', 'null'), 'Building'); added += 1
                c = prev[c]
            self.say('joined net', i, 'size', len(cc), 'with +%d cables' % added)

    def hp(self):
        n = 0
        for r in self.M.recs:
            if r.deleted or not r.pos or not is_bld(r) or '<health>' in r.raw or r.d == 'PartySpot': continue
            t = self.T.get(r.d)
            m = re.search(r'<health>(\d+)</health>', t.raw) if t else None
            if m:
                r.raw = re.sub(r'(<pos>[^<]*</pos>)', lambda q: q.group(1) + '<health>%s</health>' % m.group(1), r.raw, count=1); n += 1
        self.say('hp fixed', n)

    # ------------------------------------------------------------ save
    def save(self, path=None):
        path = path or self.path
        if self.terr is not None:
            self.M.head = AW.put_grid(self.M.head, 'terrainGrid', 'topGridDeflate', self.terr)
            self.M.head = AW.put_grid(self.M.head, 'roofGrid', 'roofsDeflate', self.roof)
            self.terr = self.roof = None
        txt = AW.clean_dangling(self.M.assemble(), log=lambda *a: None)
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write(txt)
        self.say('saved', path)

    # ------------------------------------------------------------ cli
    def run(self, text):
        for line in re.split(r'[;\n]', text):
            line = line.strip()
            if not line or line.startswith('#'): continue
            parts = shlex.split(line); cmd, args = parts[0], parts[1:]
            conv = lambda a: int(a) if re.fullmatch(r'-?\d+', a) else a
            args = [conv(a) for a in args]
            try:
                if cmd == 'show':
                    self.show(*args[:4], wires=len(args) > 4)
                elif cmd == 'roof':
                    self.roof_(*args)
                elif cmd in ('info', 'put', 'wall', 'box', 'door', 'rm', 'mv', 'rot', 'floor', 'wire', 'autowire', 'hp', 'zone', 'save', 'hide', 'clear', 'bill', 'unbill', 'stock', 'leaks', 'nets'):
                    getattr(self, cmd)(*args)
                else:
                    self.say('unknown command', cmd)
            except Exception as e:
                self.say('ERROR in "%s": %s' % (line, e))
        print('\n'.join(self.out)); self.out = []


if __name__ == '__main__':
    argv = sys.argv[1:]
    path = EDITED
    if argv and argv[0] == '--file':
        path = argv[1]; argv = argv[2:]
    if not argv:
        print(__doc__); sys.exit()
    text = argv[1] if argv[0] == '-c' else open(argv[0]).read()
    Ed(path).run(text)
