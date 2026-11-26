"""Integrate pressure force on the 'wing' patch (workaround: function objects
are broken in the Ubuntu openfoam-1912 package). Prints time, Cl (pressure), Cd (pressure).
Usage: python forces.py <case>"""
import sys, os, re, numpy as np
case = sys.argv[1]; Uinf, c, z = 30.0, 0.2234, 0.01
def body(path):
    t = open(path).read(); t = re.sub(r'/\*.*?\*/', '', t, flags=re.S); t = re.sub(r'//.*', '', t)
    return t[t.index('}', t.index('FoamFile'))+1:]
def lst(t, start=0):
    m = re.search(r'(\d+)\s*\(', t[start:]); i = start + m.end(); depth = 1; j = i
    while depth: j += 1; depth += {'(':1, ')':-1}.get(t[j], 0)
    return int(m.group(1)), t[i:j]
pm = os.path.join(case, 'constant/polyMesh')
_, s = lst(body(pm+'/points')); P = np.array(re.findall(r'\(([^()]+)\)', s), dtype=object)
P = np.array([list(map(float, p.split())) for p in P])
_, s = lst(body(pm+'/faces')); F = [list(map(int, f.split())) for f in re.findall(r'\d+\s*\(([^()]+)\)', s)]
b = body(pm+'/boundary'); m = re.search(r'wing\s*\{([^}]*)\}', b).group(1)
n = int(re.search(r'nFaces\s+(\d+)', m).group(1)); st = int(re.search(r'startFace\s+(\d+)', m).group(1))
Sf = []
for f in F[st:st+n]:
    v = P[f]; a = np.zeros(3)
    for i in range(1, len(v)-1): a += 0.5*np.cross(v[i]-v[0], v[i+1]-v[0])
    Sf.append(a)
Sf = np.array(Sf)
_, s_ = lst(body(pm+'/owner')); own = np.array(s_.split(), int)[st:st+n]
times = sorted([d for d in os.listdir(case) if re.fullmatch(r'\d+(\.\d+)?', d) and d != '0'], key=float)
for tm in times:
    pb = body(os.path.join(case, tm, 'p'))            # zeroGradient wall: face p = owner-cell p
    _, s = lst(pb, pb.index('internalField')); p = np.array(s.split(), float)[own]
    Fp = (p[:, None]*Sf).sum(0); q = 0.5*Uinf**2*c*z
    print(f"{tm} Cl={Fp[1]/q:.4f} Cd_p={Fp[0]/q:.4f}")
