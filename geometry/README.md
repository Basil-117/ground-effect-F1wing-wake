# Wing geometry (not included)

The scripts need the Zerihan (2001) wing coordinates, which are not redistributed here because the thesis is
under the University of Southampton Thesis Licence. Transcribe them from the thesis
(J. Zerihan, *An investigation into the aerodynamics of wings in ground effect*, PhD thesis, University of
Southampton, 2001, eprints.soton.ac.uk/426058) into these files, one row per point, `surface,x_c,y_c`:

| file | source | rows |
|---|---|---|
| `zerihan_single_element.csv` | Table 2 (single element at the reference incidence of 1 deg) | `suction` and `pressure` surfaces, leading edge to trailing edge |
| `zerihan_double_main.csv` | Table 3 (main element, reference incidence 14.1 deg) | same format |
| `zerihan_double_flap.csv` | Table 4 (flap) | same format |

Header and row format (values from the thesis table):
```
surface,x_c,y_c
suction,<x/c>,<y/c>
...
pressure,<x/c>,<y/c>
```
