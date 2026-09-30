import sys, collections
from layout import *
from geom import rect
from PIL import Image, ImageDraw

def footprint(o):
    return rect(o['pos'][0], o['pos'][1], SIZES.get(o['d'], (1, 1)), o['rot'])

def analyse(P, verbose=True):
    occ = collections.defaultdict(list)
    probs = []
    for i, o in enumerate(P.objs):
        for c in footprint(o):
            occ[c].append(i)
    for c, ids in occ.items():
        ds = [P.objs[i]['d'] for i in ids]
        if len(ids) > 1:
            probs.append(('overlap', c, ds))
    for i, o in enumerate(P.objs):
        if o['d'] in ('Cooler', 'Vent'):
            continue
        for c in footprint(o):
            if c in P.walls or c in P.doors:
                if o.get('replaces_wall'):
                    continue
                probs.append(('on-wall', c, o['d']))
    for i, o in enumerate(P.objs):
        if o['d'] == 'Vent' and (o['pos'] not in P.walls):
            probs.append(('vent-not-on-wall', o['pos']))
        if o['d'] == 'Cooler':
            cells = footprint(o)
            if not all(c in P.walls for c in cells):
                probs.append(('cooler-not-on-wall', o['pos'], [c for c in cells if c not in P.walls]))
            dx, dz = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}[o['rot']]
            # cold side of each cell should be open floor, hot side too
            for (x, z) in cells:
                cold = (x + dx, z + dz); hot = (x - dx, z - dz)
                if cold in P.walls or hot in P.walls:
                    probs.append(('cooler-side-blocked', (x, z), o['rot']))
    return occ, probs

def blocked(P, occ):
    b = set(P.walls)
    for c, ids in occ.items():
        for i in ids:
            o = P.objs[i]
            if o['d'] in ('Table2x2c', 'Bed', 'BedGuest', 'Shelf', 'FermentingBarrel', 'Battery', 'SolarGenerator',
                          'Grave', 'Turret_MiniTurret', 'ElectricSmithy', 'TableMachining', 'DrugLab', 'ElectricSmelter',
                          'BiofuelRefinery', 'ElectricTailoringBench', 'HandTailoringBench', 'TableSculpting', 'Brewery',
                          'HiTechResearchBench', 'FueledStove', 'TableButcher', 'PokerTable', 'WindTurbine',
                          'HC_SlotMachineRed', 'HC_SlotMachineGreen', 'HC_SlotMachineBlue', 'Heater', 'StandingLamp',
                          'Cooler', 'Vent', 'SculptureLarge', 'ChessTable', 'MultiAnalyzer', 'CommsConsole', 'LongRangeMineralScanner'):
                b.add(c)
    return b

def connectivity(P, occ):
    """flood from outside through doors/openings; return set of reachable cells in box"""
    solid = set(P.walls)
    start = (123, 92)
    seen = {start}; q = [start]
    while q:
        x, z = q.pop()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in seen or n in solid: continue
            if not (80 <= n[0] <= 175 and 85 <= n[1] <= 170): continue
            seen.add(n); q.append(n)
    return seen

COL = dict(TileMarble=(225, 225, 230), WoodPlankFloor=(185, 135, 75), Concrete=(150, 150, 155), SterileTile=(200, 230, 240))
CH = dict(Bed='b', BedGuest='g', DiningChair='c', Table2x2c='T', Shelf='s', Heater='H', Cooler='C', Vent='v',
          SolarGenerator='S', Battery='B', Turret_MiniTurret='M', StandingLamp='l', FermentingBarrel='u',
          Grave='G', FueledStove='F', TableButcher='K', ElectricSmithy='W', TableMachining='W', DrugLab='W',
          ElectricSmelter='W', BiofuelRefinery='W', ElectricTailoringBench='Y', HandTailoringBench='Y',
          TableSculpting='Y', Brewery='R', HiTechResearchBench='Q', MultiAnalyzer='q', CommsConsole='k',
          PokerTable='P', ChessTable='h', PartySpot='p', HC_SlotMachineRed='$', HC_SlotMachineGreen='$',
          HC_SlotMachineBlue='$', SculptureLarge='a', FirefoamPopper='f', WindTurbine='w', OrbitalTradeBeacon='o',
          ButcherSpot='x', LongRangeMineralScanner='m', PodLauncher='L', TransportPod='L', FloodLight='*')

def draw(P, occ, path, x0=92, x1=164, z0=88, z1=164, sc=13, cond=None, zones=True):
    img = Image.new('RGB', ((x1 - x0) * sc, (z1 - z0) * sc), (95, 80, 55))
    d = ImageDraw.Draw(img)
    def rc(x, z): return ((x - x0) * sc, (z1 - 1 - z) * sc, (x - x0 + 1) * sc - 1, (z1 - z) * sc - 1)
    for (x, z), f in P.floors.items():
        d.rectangle(rc(x, z), fill=COL.get(f, (140, 140, 140)))
    if zones:
        zc = {'freezer': (120, 190, 255), 'store_main': (255, 200, 120), 'store_apparel': (255, 150, 200), 'guestfood': (120, 255, 120)}
        for n, cells in P.zones.items():
            for c in cells:
                r = rc(*c); d.rectangle((r[0] + 3, r[1] + 3, r[2] - 3, r[3] - 3), outline=zc.get(n, (255, 0, 0)))
    if cond:
        for c in cond:
            r = rc(*c); d.rectangle((r[0] + 5, r[1] + 5, r[2] - 5, r[3] - 5), fill=(240, 220, 0))
    for c in P.walls:
        d.rectangle(rc(*c), fill=(70, 70, 75))
    for c in P.doors:
        d.rectangle(rc(*c), fill=(255, 140, 0))
    for o in P.objs:
        ch = CH.get(o['d'], '?')
        for c in footprint(o):
            r = rc(*c)
            col = (40, 40, 200) if o['d'] in ('SolarGenerator', 'Battery') else (255, 255, 255)
            if o['d'] in ('Cooler',): col = (0, 220, 255)
            if o['d'] in ('Heater',): col = (255, 90, 40)
            if o['d'] == 'Turret_MiniTurret': col = (255, 0, 0)
            if o['d'] in ('Bed', 'BedGuest'):
                col = (255, 120, 220) if o.get('role') != 'prisoner' else (255, 60, 60)
            if o['d'] in ('Bed',) and o.get('role') == 'medical': col = (120, 255, 120)
            d.rectangle((r[0] + 1, r[1] + 1, r[2] - 1, r[3] - 1), outline=col)
            d.text((r[0] + 3, r[1] + 1), ch, fill=col)
    for x in range(x0, x1, 5): d.text(((x - x0) * sc + 1, 0), str(x), fill=(0, 255, 255))
    for z in range(z0, z1, 5): d.text((0, (z1 - 1 - z) * sc), str(z), fill=(0, 255, 255))
    img.save(path)

if __name__ == '__main__':
    P = build()
    occ, probs = analyse(P)
    print('walls', len(P.walls), 'doors', len(P.doors), 'objs', len(P.objs))
    for p in probs[:80]: print(p)
    print(len(probs), 'problems')
    draw(P, occ, 'plan.png')
