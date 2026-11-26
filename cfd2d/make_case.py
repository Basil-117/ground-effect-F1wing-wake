"""Build a 2D OpenFOAM case (wing in ground effect) with a parametrised
'dirty-air' inlet: Gaussian velocity deficit + elevated turbulence.
Usage: python make_case.py <case_dir> <deficit D> <TI> <wake_centre_y [m]> <wake_sigma [m]> [upwash_deg]
Optional upwash angle theta adds a vertical velocity V = U tan(theta), faded to zero at the moving ground.
The top boundary is then open (fixed pressure, inletOutlet velocity) so the vertical mass flux can leave;
OPEN_TOP=1 uses the open top also without upwash (the campaign does, so all its runs share one top condition)."""
import sys, os, math, numpy as np
FINE = os.environ.get("NUMERICS", "default") == "robust"   # NUMERICS=robust: first-order turbulence, SIMPLE, low relaxation
END = int(os.environ.get("END_TIME", 2000))   # iterations; fine meshes need more (3000-6000)
case, D, TI, yc, sig = sys.argv[1], *map(float, sys.argv[2:6])
theta = math.radians(float(sys.argv[6])) if len(sys.argv) > 6 else 0.0
OPEN = bool(theta) or os.environ.get("OPEN_TOP") == "1"
Uinf, c, nu, H, z = 30.0, 0.2234, 1.5e-5, 5*0.2234, 0.01
Lt = float(os.environ.get("TURB_L", 0.05))   # turbulence length scale at inlet [m] (TURB_L=... to change)
hdr = lambda cls, obj, loc="": f"""FoamFile {{ version 2.0; format ascii; class {cls}; {('location "'+loc+'";') if loc else ''} object {obj}; }}\n"""
def W(path, txt):
    os.makedirs(os.path.dirname(os.path.join(case, path)), exist_ok=True)
    open(os.path.join(case, path), "w").write(txt)
# ---------------- inlet profile (boundaryData for timeVaryingMappedFixedValue) -----
y = np.linspace(0, H, 121)
U = Uinf*(1 - D*np.exp(-0.5*((y-yc)/sig)**2))
Tu = 0.005 + (TI-0.005)*np.exp(-0.5*((y-yc)/(1.5*sig))**2)   # TI peaks in wake
k = 1.5*(U*Tu)**2; om = np.sqrt(k)/(0.09**0.25*Lt)
P = [(-5*c, yi, zi) for zi in (0, z) for yi in y]
vec = lambda arr: f"{len(arr)}\n(\n" + "\n".join("(%g %g %g)" % tuple(a) for a in arr) + "\n)\n"
sca = lambda arr: f"{len(arr)}\n(\n" + "\n".join("%g" % a for a in arr) + "\n)\n"
W("constant/boundaryData/inlet/points", vec(P))
V = U*math.tan(theta)*(1 - np.exp(-y/0.05))                 # upwash, zero at the moving ground
W("constant/boundaryData/inlet/0/U", vec([(u,v,0) for u, v in zip(np.tile(U,2), np.tile(V,2))]))
W("constant/boundaryData/inlet/0/k", sca(np.tile(k,2)))
W("constant/boundaryData/inlet/0/omega", sca(np.tile(om,2)))
kin, omin = 1.5*(Uinf*0.005)**2, math.sqrt(1.5*(Uinf*0.005)**2)/(0.09**0.25*Lt)
# ---------------- fields ---------------------------------------------------------
mapped = "type timeVaryingMappedFixedValue; setAverage false;"
def field(name, cls, dims, internal, bcs):
    b = "\n".join(f"    {p} {{ {v} }}" for p, v in bcs.items())
    W(f"0/{name}", hdr(cls, name, "0") + f"dimensions {dims};\ninternalField uniform {internal};\nboundaryField\n{{\n{b}\n    frontAndBack {{ type empty; }}\n}}\n")
field("U","volVectorField","[0 1 -1 0 0 0 0]",f"({Uinf} 0 0)",{
 "inlet": mapped, "outlet":"type inletOutlet; inletValue uniform (0 0 0); value $internalField;",
 "top":(f"type inletOutlet; inletValue uniform ({Uinf} 0 0); value $internalField;" if OPEN else "type slip;"), "ground":f"type fixedValue; value uniform ({Uinf} 0 0);", "wing":"type noSlip;"})
field("p","volScalarField","[0 2 -2 0 0 0 0]","0",{
 "inlet":"type zeroGradient;", "outlet":"type fixedValue; value uniform 0;", "top":("type fixedValue; value uniform 0;" if OPEN else "type slip;"),
 "ground":"type zeroGradient;", "wing":"type zeroGradient;"})
for n, v, wf in (("k",kin,"kqRWallFunction"),("omega",omin,"omegaWallFunction")):
    field(n,"volScalarField","[0 2 -2 0 0 0 0]" if n=="k" else "[0 0 -1 0 0 0 0]",f"{v:g}",{
     "inlet": mapped, "outlet":f"type inletOutlet; inletValue uniform {v:g}; value $internalField;",
     "top":(f"type inletOutlet; inletValue uniform {v:g}; value $internalField;" if OPEN else "type slip;"), "ground":f"type {wf}; value $internalField;", "wing":f"type {wf}; value $internalField;"})
field("nut","volScalarField","[0 2 -1 0 0 0 0]","0",{
 "inlet":"type calculated; value uniform 0;","outlet":"type calculated; value uniform 0;","top":("type calculated; value uniform 0;" if OPEN else "type slip;"),
 "ground":"type nutUSpaldingWallFunction; value uniform 0;","wing":"type nutUSpaldingWallFunction; value uniform 0;"})
# ---------------- constant ---------------------------------------------------------
W("constant/transportProperties", hdr("dictionary","transportProperties")+f"transportModel Newtonian;\nnu {nu};\n")
W("constant/turbulenceProperties", hdr("dictionary","turbulenceProperties")+"simulationType RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs off; }\n")
# ---------------- system -----------------------------------------------------------
W("system/controlDict", hdr("dictionary","controlDict")+f"""application simpleFoam; startFrom startTime; startTime 0;
stopAt endTime; endTime {END}; deltaT 1; writeControl timeStep; writeInterval 500; purgeWrite 0;
writeFormat ascii; timeFormat general; runTimeModifiable true;
// NOTE: add forceCoeffs/yPlus function objects here on a working OpenFOAM build
""")
def NUM(txt):   # numerics: original settings on the default mesh, robust ones on wall-resolved meshes
    v = dict(TURB="upwind", LIM="0.33", NNO="2", CONS="no", RU="0.5", RT="0.4", RP="0.3") if FINE else \
        dict(TURB="limitedLinear 1", LIM="0.5", NNO="1", CONS="yes", RU="0.7", RT="0.6", RP="0.5")
    for k, val in v.items(): txt = txt.replace("{" + k + "}", val)
    return txt
W("system/fvSchemes", NUM(hdr("dictionary","fvSchemes")+"""ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; grad(U) cellLimited Gauss linear 1; grad(k) cellLimited Gauss linear 1; grad(omega) cellLimited Gauss linear 1; }
divSchemes { default none; div(phi,U) bounded Gauss linearUpwind grad(U);
  div(phi,k) bounded Gauss {TURB}; div(phi,omega) bounded Gauss {TURB};
  div((nuEff*dev2(T(grad(U))))) Gauss linear; }
laplacianSchemes { default Gauss linear limited {LIM}; }
interpolationSchemes { default linear; }
snGradSchemes { default limited {LIM}; }
wallDist { method meshWave; }
"""))
W("system/fvSolution", NUM(hdr("dictionary","fvSolution")+"""solvers {
  p { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.05; }
  "(U|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.1; }
}
SIMPLE { nNonOrthogonalCorrectors {NNO}; consistent {CONS};
  residualControl { p 1e-5; U 1e-6; "(k|omega)" 1e-6; } }
relaxationFactors { equations { U {RU}; ".*" {RT}; } fields { p {RP}; } }
"""))
W("system/decomposeParDict", hdr("dictionary","decomposeParDict")+"numberOfSubdomains 2;\nmethod simple;\nsimpleCoeffs { n (2 1 1); delta 0.001; }\n")
print("case written:", case, f"D={D} TI={TI} yc={yc} sigma={sig} upwash={math.degrees(theta):.1f} deg open_top={OPEN}")
