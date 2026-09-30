from render import *
import collections
SOLID={'Table2x2c','Bed','BedGuest','Shelf','FermentingBarrel','Battery','SolarGenerator','Grave','Turret_MiniTurret','ElectricSmithy','TableMachining','DrugLab','ElectricSmelter','BiofuelRefinery','ElectricTailoringBench','HandTailoringBench','TableSculpting','Brewery','HiTechResearchBench','FueledStove','TableButcher','PokerTable','WindTurbine','HC_SlotMachineRed','HC_SlotMachineGreen','HC_SlotMachineBlue','SculptureLarge','ChessTable','MultiAnalyzer','CommsConsole','LongRangeMineralScanner','Heater','StandingLamp','Cooler','Vent','FirefoamPopper','OrbitalTradeBeacon'}
def reach(P):
    occ,_=analyse(P)
    bl=set()
    for c,ids in occ.items():
        for i in ids:
            if P.objs[i]['d'] in SOLID and P.objs[i]['d'] not in('Cooler','Vent'): bl.add(c)
    solid=set(P.walls)|bl
    start=(123,92); seen={start}; q=[start]
    while q:
        x,z=q.pop()
        for dx,dz in((1,0),(-1,0),(0,1),(0,-1)):
            n=(x+dx,z+dz)
            if n in seen or n in solid: continue
            if not(85<=n[0]<=175 and 85<=n[1]<=170): continue
            seen.add(n); q.append(n)
    return seen,solid
if __name__=='__main__':
    P=build(); seen,solid=reach(P)
    un=[c for c in P.floors if c not in seen and c not in solid]
    print('unreachable floor cells',len(un))
    rows=collections.defaultdict(list)
    for c in un: rows[c[1]].append(c[0])
    for z in sorted(rows): print(z,sorted(rows[z]))
    for (x,z) in P.doors:
        horiz=((x-1,z) in P.walls or (x+1,z) in P.walls)
        a,b=((x,z+1),(x,z-1)) if horiz else ((x+1,z),(x-1,z))
        if a in solid or b in solid: print('door blocked',(x,z),a in solid,b in solid)
    # zone cells reachable & not solid
    for n,cells in P.zones.items():
        bad=[c for c in cells if c in solid or c not in seen]
        print('zone',n,len(cells),'bad',len(bad),bad[:5])
