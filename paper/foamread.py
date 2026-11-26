import re, os, numpy as np
def body(path):
    t = open(path).read(); t = re.sub(r'/\*.*?\*/', '', t, flags=re.S); t = re.sub(r'//.*', '', t)
    return t[t.index('}', t.index('FoamFile')) + 1:]
def lst(t, start=0):
    m = re.search(r'(\d+)\s*\(', t[start:]); i = start + m.end(); depth = 1; j = i
    while depth: j += 1; depth += {'(': 1, ')': -1}.get(t[j], 0)
    return t[i:j]
def mesh(case):
    pm = os.path.join(case, 'constant/polyMesh')
    P = np.array([list(map(float, p.split())) for p in re.findall(r'\(([^()]+)\)', lst(body(pm + '/points')))])
    F = [list(map(int, f.split())) for f in re.findall(r'\d+\s*\(([^()]+)\)', lst(body(pm + '/faces')))]
    own = np.array(lst(body(pm + '/owner')).split(), int)
    b = body(pm + '/boundary'); pat = {}
    for name, blk in re.findall(r'(\w+)\s*\{([^}]*)\}', b):
        n = re.search(r'nFaces\s+(\d+)', blk); s = re.search(r'startFace\s+(\d+)', blk)
        if n and s: pat[name] = (int(s.group(1)), int(n.group(1)))
    return P, F, own, pat
def field(case, tm, name, vector):
    b = body(os.path.join(case, tm, name)); k = b.index('internalField'); s = lst(b, k)
    return np.array([list(map(float, x.split())) for x in re.findall(r'\(([^()]+)\)', s)]) if vector else np.array(s.split(), float)
def slice2d(case):
    """polygons (x,y) of the z=min frontAndBack faces and their owner cells"""
    P, F, own, pat = mesh(case); st, n = pat['frontAndBack']; z0 = P[:, 2].min()
    polys, cells = [], []
    for i in range(st, st + n):
        v = P[F[i]]
        if abs(v[:, 2].max() - z0) < 1e-9: polys.append(v[:, :2]); cells.append(own[i])
    walls = {k: [P[F[i]][:, :2] for i in range(s, s + m)] for k, (s, m) in pat.items() if k in ('wing',)}
    return polys, np.array(cells), walls
