"""New base layout. Pure geometry + object list. No save I/O here."""
from geom import rect

# ---------------------------------------------------------------- constants
X0, X1, Z0, Z1 = 114, 159, 107, 156      # main compound outer walls
YX0, YX1, YZ0, YZ1 = 100, 114, 111, 136  # west power yard walls (shares x=114)
WALL = 'BlocksGranite'
DOOR = 'Steel'

SIZES = {
    'Bed': (1, 2), 'BedGuest': (1, 2), 'DiningChair': (1, 1), 'Table2x2c': (2, 2),
    'Shelf': (2, 1), 'Heater': (1, 1), 'Cooler': (2, 1), 'Vent': (1, 1),
    'SolarGenerator': (4, 4), 'Battery': (1, 1), 'Turret_MiniTurret': (1, 1),
    'StandingLamp': (1, 1), 'FermentingBarrel': (1, 1), 'Wall': (1, 1), 'Door': (1, 1),
    'FirefoamPopper': (1, 1), 'PowerConduit': (1, 1), 'Grave': (1, 2),
    'FueledStove': (3, 1), 'TableButcher': (3, 1), 'ElectricSmithy': (3, 1),
    'TableMachining': (3, 1), 'DrugLab': (3, 1), 'ElectricSmelter': (3, 1),
    'BiofuelRefinery': (3, 2), 'ElectricTailoringBench': (3, 1), 'HandTailoringBench': (3, 1),
    'TableSculpting': (3, 1), 'Brewery': (3, 1), 'HiTechResearchBench': (3, 1),
    'MultiAnalyzer': (1, 1), 'CommsConsole': (1, 1), 'OrbitalTradeBeacon': (1, 1),
    'PokerTable': (2, 2), 'ChessTable': (2, 1), 'PartySpot': (1, 1),
    'HC_SlotMachineRed': (1, 1), 'HC_SlotMachineGreen': (1, 1), 'HC_SlotMachineBlue': (1, 1),
    'SculptureLarge': (2, 2), 'ButcherSpot': (1, 1), 'LongRangeMineralScanner': (2, 2),
    'FloodLight': (1, 1), 'WindTurbine': (5, 2), 'PodLauncher': (1, 1), 'TransportPod': (2, 1),
    'CM_BasicManagerStation': (3, 1), 'CMR_ManagingSpot': (1, 1), 'HorseshoesPin': (2, 1),
}

# defs that need a power connection (consumer / connector)
POWERED = {'Heater', 'Cooler', 'StandingLamp', 'ElectricSmithy', 'TableMachining', 'DrugLab',
           'ElectricSmelter', 'BiofuelRefinery', 'ElectricTailoringBench', 'HiTechResearchBench',
           'MultiAnalyzer', 'CommsConsole', 'HC_SlotMachineRed', 'HC_SlotMachineGreen',
           'HC_SlotMachineBlue', 'Turret_MiniTurret', 'FloodLight', 'LongRangeMineralScanner'}


class Plan:
    def __init__(self):
        self.walls = {}          # (x,z) -> stuff
        self.doors = {}          # (x,z) -> stuff
        self.floors = {}         # (x,z) -> terrain def name
        self.roof = set()
        self.objs = []           # dicts
        self.zones = {}          # name -> set(cells)
        self.areas = {}          # name -> set(cells)
        self.conduits = set()    # extra forced conduit cells
        self.notes = []

    # ---- walls
    def hline(self, z, x0, x1):
        for x in range(x0, x1 + 1):
            self.walls[(x, z)] = WALL

    def vline(self, x, z0, z1):
        for z in range(z0, z1 + 1):
            self.walls[(x, z)] = WALL

    def open(self, cells):
        for c in cells:
            self.walls.pop(c, None)
            self.doors.pop(c, None)

    def door(self, x, z):
        self.walls.pop((x, z), None)
        self.doors[(x, z)] = DOOR

    def floor(self, x0, x1, z0, z1, name):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.floors[(x, z)] = name

    def add(self, d, x, z, rot=0, **kw):
        o = dict(d=d, pos=(x, z), rot=rot)
        o.update(kw)
        self.objs.append(o)
        return o


def front(rot):
    return {0: (0, -1), 1: (-1, 0), 2: (0, 1), 3: (1, 0)}[rot]


def build():
    P = Plan()

    # ------------------------------------------------------------ walls
    for z in (107, 122, 126, 135, 148, 156):
        P.hline(z, X0, X1)
    P.vline(X0, Z0, Z1)
    P.vline(X1, Z0, Z1)

    # gate in the south wall (3 wide, open, killbox entrance)
    P.open([(123, 107), (124, 107), (125, 107)])

    # ---- Band 1: guest wing / industrial wing
    P.vline(134, 108, 121)
    P.vline(146, 108, 121)
    P.hline(118, 115, 130)                # hall | dorms
    for x in (118, 122, 126, 130):
        P.vline(x, 119, 121)
    P.hline(115, 135, 145)                # machine shop | tailoring
    P.hline(114, 147, 158)                # research | brewery

    # ---- Band 2: dining | kitchen | V | freezer
    P.vline(128, 127, 134)
    P.vline(135, 127, 147)
    P.vline(138, 127, 147)

    # ---- North wing: rows of rooms along corridor z141..142
    P.hline(140, 115, 158)
    P.hline(143, 115, 158)
    for z0, z1 in ((136, 139), (144, 147)):
        for x in (118, 122, 126, 130):    # colonist rooms
            P.vline(x, z0, z1)
        P.vline(148, z0, z1)              # hospital | prison
        for x in (152, 156):              # prison cells
            P.vline(x, z0, z1)

    # V column (x136..137) runs z127..147 through all horizontal walls
    for z in (126, 135, 140, 143):
        P.open([(136, z), (137, z)])
    # corridor passes through V walls
    for z in (141, 142):
        P.open([(135, z), (138, z)])
    # passage hall -> spine
    P.open([(131, 118), (132, 118), (133, 118)])

    # ---- west power yard
    P.vline(YX0, YZ0, YZ1)
    P.hline(YZ0, YX0, X0)
    P.hline(YZ1, YX0, X0)

    # ---- killbox corridor outside the south gate
    for z in range(93, 107):
        P.walls[(122, z)] = WALL
        P.walls[(126, z)] = WALL
    P.walls[(122, 107)] = WALL
    P.walls[(126, 107)] = WALL

    # ------------------------------------------------------------ doors
    doors = [
        # guest wing
        (116, 118), (120, 118), (124, 118), (128, 118),   # dorms <- hall
        (132, 122),                                        # passage -> spine
        # industrial
        (139, 115), (139, 122),                            # machine shop<-tailoring<-spine
        (152, 114), (152, 122),                            # research<-brewery<-spine
        # band 2
        (121, 126), (128, 131), (135, 131), (138, 131),
        (159, 133),                                        # freezer -> fields
        # north wing rooms
        (116, 140), (120, 140), (124, 140), (128, 140), (132, 140),
        (116, 143), (120, 143), (124, 143), (128, 143), (132, 143),
        (143, 140), (143, 143),                            # hospital wards
        (150, 140), (154, 140), (157, 140),                # prison cells south row
        (150, 143), (154, 143), (157, 143),                # prison cells north row
        # warehouse
        (136, 148), (137, 148),
        # yard
        (114, 125),
    ]
    for d in doors:
        P.door(*d)

    # ------------------------------------------------------------ floors & roof
    F = P.floor
    F(115, 133, 108, 117, 'TileMarble')          # guest hall
    F(115, 117, 119, 121, 'WoodPlankFloor')      # dorms
    F(119, 121, 119, 121, 'WoodPlankFloor')
    F(123, 125, 119, 121, 'WoodPlankFloor')
    F(127, 129, 119, 121, 'WoodPlankFloor')
    F(131, 133, 118, 121, 'Concrete')            # passage
    F(135, 145, 108, 114, 'Concrete')            # machine shop
    F(135, 145, 116, 121, 'Concrete')            # tailoring
    F(147, 158, 108, 113, 'Concrete')            # research
    F(147, 158, 115, 121, 'Concrete')            # brewery
    F(115, 158, 123, 125, 'Concrete')            # spine
    F(115, 127, 127, 134, 'TileMarble')          # dining
    F(129, 134, 127, 134, 'SterileTile')         # kitchen
    F(136, 137, 127, 147, 'Concrete')            # V
    F(139, 158, 127, 134, 'SterileTile')         # freezer
    F(115, 134, 141, 142, 'Concrete')            # corridor
    F(139, 158, 141, 142, 'Concrete')
    for x in (115, 119, 123, 127):               # colonist rooms
        for z0, z1 in ((136, 139), (144, 147)):
            F(x, x + 2, z0, z1, 'WoodPlankFloor')
    for z0, z1 in ((136, 139), (144, 147)):
        F(131, 134, z0, z1, 'WoodPlankFloor')
        F(139, 147, z0, z1, 'SterileTile')       # hospital
        F(149, 151, z0, z1, 'Concrete')          # prison
        F(153, 155, z0, z1, 'Concrete')
        F(157, 158, z0, z1, 'Concrete')
    F(115, 158, 149, 155, 'Concrete')            # warehouse
    for x in range(X0, X1 + 1):
        for z in range(Z0, Z1 + 1):
            P.roof.add((x, z))

    # ------------------------------------------------------------ helpers
    def lamp(x, z):
        P.add('StandingLamp', x, z)

    def heater(x, z, t=19):
        P.add('Heater', x, z, target=t)

    def cooler(x, z, rot, t=24):
        P.add('Cooler', x, z, rot, target=t)

    def vent(x, z):
        P.add('Vent', x, z)

    def table_with_chairs(x, z, sides='tblr'):
        P.add('Table2x2c', x, z, stuff='WoodLog')
        if 't' in sides:
            P.add('DiningChair', x, z + 2, 2, stuff='WoodLog'); P.add('DiningChair', x + 1, z + 2, 2, stuff='WoodLog')
        if 'b' in sides:
            P.add('DiningChair', x, z - 1, 0, stuff='WoodLog'); P.add('DiningChair', x + 1, z - 1, 0, stuff='WoodLog')
        if 'l' in sides:
            P.add('DiningChair', x - 1, z, 1, stuff='WoodLog'); P.add('DiningChair', x - 1, z + 1, 1, stuff='WoodLog')
        if 'r' in sides:
            P.add('DiningChair', x + 2, z, 3, stuff='WoodLog'); P.add('DiningChair', x + 2, z + 1, 3, stuff='WoodLog')

    # ------------------------------------------------------------ GUEST HALL
    for z, src in zip((112, 114, 116), ('HC_SlotMachineRed', 'HC_SlotMachineGreen', 'HC_SlotMachineBlue')):
        P.add(src, 115, z, 3, move=src)
    P.add('PokerTable', 118, 113, 0, move='PokerTable')
    P.add('ChessTable', 118, 110, 0, move='ChessTable')
    P.add('PartySpot', 121, 110, 0, move='PartySpot')
    P.add('SculptureLarge', 116, 109, 0, move='SculptureLarge')
    table_with_chairs(128, 113, 'tblr')
    table_with_chairs(128, 109, 'blr')
    # bar shelves along the east wall of the hall (x133, z108..117), vertical
    P.add('Shelf', 133, 109, 1, move='Shelf', idx=0, filt=['SmokeleafJoint'])
    P.add('Shelf', 133, 111, 1, move='Shelf', idx=1, filt=['Beer'])
    P.add('Shelf', 133, 113, 1, move='Shelf', idx=2, filt=['MealSimple', 'MealFine', 'Pemmican', 'Chocolate'])
    P.add('Shelf', 133, 115, 1, new='Shelf', filt=['Beer'], prio='Critical')
    P.add('Shelf', 133, 117, 1, new='Shelf', filt=['MealSimple', 'MealFine'], prio='Critical')
    # alcove guest beds along hall north wall
    for x in (117, 119, 121):
        P.add('BedGuest', x, 116, 0, new='BedGuest')
    for x, z in ((121, 112), (131, 111), (125, 116), (119, 108)):
        lamp(x, z)
    heater(123, 117); heater(131, 109, 19)
    cooler(114, 114, 1); cooler(114, 116, 1)
    cooler(118, 107, 0); cooler(130, 107, 0)
    # gate guards inside the gate
    P.add('Turret_MiniTurret', 122, 108, 0, new='Turret')
    P.add('Turret_MiniTurret', 126, 108, 0, new='Turret')

    # dorms: 3 guest beds each
    dorm_x = (115, 119, 123, 127)
    for i, x0 in enumerate(dorm_x):
        for k in range(3):
            P.add('BedGuest', x0 + k, 120, 0, new='BedGuest')
        lamp(x0, 119)
        vent(x0 + 2, 118)
        vent(x0 + 2, 122)
    lamp(131, 120)

    # ------------------------------------------------------------ INDUSTRIAL
    # machine shop x135..145 z108..114
    P.add('ElectricSmithy', 137, 114, 0, move='ElectricSmithy')
    P.add('TableMachining', 141, 114, 0, move='TableMachining')
    P.add('DrugLab', 144, 114, 0, move='DrugLab')
    P.add('ElectricSmelter', 137, 108, 2, move='ElectricSmelter')
    P.add('BiofuelRefinery', 142, 109, 2, move='BiofuelRefinery')
    heater(135, 111); cooler(138, 107, 0)
    lamp(139, 111); lamp(144, 111); P.add('FirefoamPopper', 140, 111, 0, move='FirefoamPopper', idx=0)
    # tailoring x135..145 z116..121
    P.add('ElectricTailoringBench', 137, 121, 0, move='ElectricTailoringBench')
    P.add('HandTailoringBench', 141, 121, 0, move='HandTailoringBench')
    P.add('TableSculpting', 142, 116, 2, move='TableSculpting')
    heater(135, 118); vent(144, 122)
    lamp(138, 118); lamp(143, 119); P.add('FirefoamPopper', 140, 118, 0, move='FirefoamPopper', idx=1)
    # research x147..158 z108..113
    P.add('HiTechResearchBench', 150, 108, 2, move='HiTechResearchBench', idx=0)
    P.add('HiTechResearchBench', 155, 108, 2, move='HiTechResearchBench', idx=1)
    P.add('MultiAnalyzer', 152, 110, 0, move='MultiAnalyzer')
    P.add('CommsConsole', 158, 109, 1, move='CommsConsole')
    P.add('LongRangeMineralScanner', 157, 112, 2, move='LongRangeMineralScanner')
    P.add('CM_BasicManagerStation', 149, 113, 0, move='CM_BasicManagerStation')
    P.add('CMR_ManagingSpot', 147, 111, 0, move='CMR_ManagingSpot')
    heater(148, 112); cooler(152, 107, 0)
    lamp(153, 112); lamp(157, 110); P.add('FirefoamPopper', 148, 109, 0, move='FirefoamPopper', idx=2)
    # brewery x147..158 z115..121
    P.add('Brewery', 149, 121, 0, move='Brewery')
    cols = [148, 149, 151, 152, 154, 155, 157, 158]
    slots = [(x, z) for z in range(116, 120) for x in cols]
    for i, (x, z) in enumerate(slots[:26]):
        P.add('FermentingBarrel', x, z, 0, move='FermentingBarrel', idx=i)
    heater(153, 117, 18); vent(156, 122); lamp(150, 118); lamp(156, 118)
    P.add('FirefoamPopper', 158, 121, 0, move='FirefoamPopper', idx=3)

    # ------------------------------------------------------------ BAND 2
    # dining x115..127 z127..134
    table_with_chairs(117, 130)
    table_with_chairs(122, 130)
    P.add('ChessTable', 126, 132, 0, new='ChessTable')
    P.add('PartySpot', 125, 129, 0, new='PartySpot')
    heater(116, 127); heater(126, 127)
    cooler(114, 130, 1)
    lamp(120, 128); lamp(120, 133); lamp(125, 131)
    vent(119, 126)
    # kitchen x129..134 z127..134
    P.add('FueledStove', 130, 134, 0, move='FueledStove')
    P.add('FueledStove', 133, 134, 0, new='FueledStove')
    P.add('TableButcher', 131, 127, 2, move='TableButcher')
    P.add('ButcherSpot', 134, 128, 2, move='ButcherSpot')
    lamp(132, 130); vent(133, 126); P.add('FirefoamPopper', 131, 131, 0, move='FirefoamPopper', idx=4)
    # V corridor lamps
    for z in (129, 133, 138, 145):
        lamp(136, z)
    # freezer x139..158 z127..134
    for z in (127, 129, 131):
        cooler(159, z, 3, t=-5)
    cooler(150, 126, 0, t=-5); cooler(154, 126, 0, t=-5)
    for x in (143, 150, 157):
        lamp(x, 130)

    # ------------------------------------------------------------ SPINE
    heater(120, 123); heater(129, 123); heater(146, 123); heater(156, 123)
    cooler(159, 123, 3); cooler(114, 124, 1)
    for x in (118, 126, 136, 146, 154):
        lamp(x, 125)

    # ------------------------------------------------------------ NORTH WING
    # colonist rooms
    rooms = [(115, 117), (119, 121), (123, 125), (127, 129), (131, 134)]
    for k, (a, b) in enumerate(rooms):
        for row, (z0, z1, dz) in enumerate(((136, 139, 136), (144, 147, 146))):
            P.add('Bed', b - 0 if b - a == 2 else b - 1, dz, 0, role='colonist', slot=row * 5 + k)
            lamp(a, z1 if row == 0 else z0)
            vent(b if k < 4 else 133, 140 if row == 0 else 143)
    heater(118, 141); heater(131, 141); heater(145, 141); heater(155, 141)
    cooler(114, 142, 1); cooler(159, 141, 3)
    for x in (122, 129, 142, 152):
        lamp(x, 142)
    # hospital: 4 beds per ward
    for x in (140, 142, 144, 146):
        P.add('Bed', x, 136, 0, role='medical')
        P.add('Bed', x, 146, 0, role='medical')
    vent(144, 140); vent(144, 143)
    for x, z in ((141, 139), (145, 139), (141, 144), (145, 144)):
        lamp(x, z)
    heater(139, 139); heater(139, 144)
    # prison: 6 cells
    for x0 in (149, 153, 157):
        P.add('Bed', x0, 136, 0, role='prisoner')
        P.add('Bed', x0, 146, 0, role='prisoner')
        lx = min(x0 + 2, 158)
        lamp(lx, 139); lamp(lx, 144)
    for x in (149, 153, 158):
        vent(x, 140); vent(x, 143)

    # ------------------------------------------------------------ WAREHOUSE
    for x in range(118, 158, 8):
        lamp(x, 155)
    P.add('OrbitalTradeBeacon', 145, 152, 0, move='OrbitalTradeBeacon')
    P.add('Heater', 128, 149, 0, target=12)

    # ------------------------------------------------------------ POWER YARD
    for (x, z) in [(106, 113), (106, 117), (106, 121), (106, 125), (106, 129), (106, 133),
                   (110, 113), (110, 117), (110, 121), (110, 129)]:
        P.add('SolarGenerator', x, z, 0, move='SolarGenerator')
    for i, z in enumerate(range(117, 125)):
        P.add('Battery', 113, z, 0, move='Battery' if i < 3 else None, new='Battery' if i >= 3 else None)
    P.add('Battery', 112, 124, 0, new='Battery')
    P.conduits.update({(114, 123), (114, 124), (114, 125), (115, 123), (115, 124), (115, 125)})
    graves = [(102, 113), (102, 115), (102, 117), (102, 119)]
    for i, (x, z) in enumerate(graves):
        P.add('Grave', x, z, 2, move='Grave', idx=i)
    for i, z in enumerate((118, 124, 130)):
        P.add('WindTurbine', 96, z, 3, move='WindTurbine', idx=i)
    lamp(104, 135); lamp(112, 135)
    P.add('HorseshoesPin', 110, 141, 0, move='HorseshoesPin')

    # ------------------------------------------------------------ KILLBOX
    for z in (96, 99, 102, 105):
        P.add('Turret_MiniTurret', 122, z, 0, new='Turret', replaces_wall=True)
        P.add('Turret_MiniTurret', 126, z, 0, new='Turret', replaces_wall=True)
    for z in range(93, 107):
        P.conduits.add((122, z)); P.conduits.add((126, z))
    P.conduits.update({(122, 107), (126, 107)})

    # east killbox around the farm door (159,133): corridor z132..134, x160..174
    for x in range(161, 175):
        P.walls[(x, 131)] = WALL
        P.walls[(x, 135)] = WALL
    for x in (163, 166, 169, 172):
        P.add('Turret_MiniTurret', x, 131, 0, new='Turret', replaces_wall=True)
        P.add('Turret_MiniTurret', x, 135, 0, new='Turret', replaces_wall=True)
    for x in range(160, 175):
        P.conduits.add((x, 131)); P.conduits.add((x, 135))
    P.conduits.update({(160, 131), (160, 135)})

    # launch pad (outside, north)
    P.add('PodLauncher', 119, 160, 0, move='PodLauncher')
    P.add('TransportPod', 120, 160, 0, move='TransportPod')
    P.add('FloodLight', 118, 158, 0, move='FloodLight', idx=0)
    P.add('FloodLight', 158, 158, 0, move='FloodLight', idx=1)

    # ------------------------------------------------------------ zones (stockpile cells)
    Zs = P.zones
    Zs['freezer'] = {(x, z) for x in range(139, 159) for z in range(127, 135)}
    for c in [(139, 131), (158, 133), (158, 134), (158, 132), (140, 131)]:
        Zs['freezer'].discard(c)
    Zs['store_apparel'] = {(x, z) for x in range(115, 129) for z in range(149, 156)}
    Zs['store_main'] = {(x, z) for x in range(130, 158) for z in range(149, 156)}
    for c in [(136, 149), (137, 149), (145, 152)] + [(x, 155) for x in range(118, 158, 8)]:
        Zs['store_main'].discard(c)
    Zs['store_main'] -= {(x, 155) for x in range(118, 158, 8)}
    Zs['store_apparel'] = {c for c in Zs['store_apparel']}
    P.areas['shop'] = {(x, z) for x in (132, 133) for z in range(108, 118)}
    P.zones['guestfood'] = {(132, 113)}
    P.areas['guest'] = ({(x, z) for x in range(115, 134) for z in range(108, 118)}
                        | {(x, z) for x in range(115, 134) for z in range(118, 122)}
                        | {(x, z) for x in range(123, 126) for z in range(93, 108)})
    solid_cells = set()
    for o in P.objs:
        if o['d'] not in ('PartySpot', 'DiningChair'):
            solid_cells.update(rect(o['pos'][0], o['pos'][1], SIZES.get(o['d'], (1, 1)), o['rot']))
    for n in P.zones:
        P.zones[n] = {c for c in P.zones[n] if c not in solid_cells and c not in P.walls and c not in P.doors}
    return P


if __name__ == '__main__':
    P = build()
    print(len(P.walls), len(P.doors), len(P.objs))
