def adjust(cx,cz,sx,sz,rot):
    if rot in (1,3): sx,sz=sz,sx
    if rot==1:
        if sz%2==0: cz-=1
    elif rot==2:
        if sx%2==0: cx-=1
        if sz%2==0: cz-=1
    elif rot==3:
        if sx%2==0: cx-=1
    return cx,cz,sx,sz
def rect(cx,cz,size,rot=0):
    sx,sz=size
    cx,cz,sx,sz=adjust(cx,cz,sx,sz,rot)
    x0=cx-(sx-1)//2; z0=cz-(sz-1)//2
    return [(x,z) for x in range(x0,x0+sx) for z in range(z0,z0+sz)]
