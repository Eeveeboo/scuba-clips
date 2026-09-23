"""The hardware this kit fits: your hoses and your webbing.

Edit these to match your own kit; the models read them and nothing else in
the project does. Sizes are in millimetres, and a webbing entry is
[width, thickness].

This module holds plain assignments only: no functions, no geometry.
Importing it runs nothing. See docs/CONVENTIONS.md.
"""

from typing import Final

# The three left-side hoses of a rig, bundled by the combo clip.
hose_inflator_tube_dia: Final = 27  # BCD inflator tube
hose_lpi_dia: Final = 12.5  # LPI hose, first stage to the inflator
hose_hp_spg_dia: Final = 8  # HP hose, first stage to the SPG

# The regulator end of the MP hose, held by the octi clip.
hose_reg_fitting_dia: Final = 18.5  # MP hose fitting on the regulator
hose_mp_dia: Final = 12.5  # MP hose, first stage to the regulator

# Held by the webbing side clip. Deliberately 12, not the 12.5 MP figure: that
# fit is looser, and changing it changes the part.
hose_side_clip_dia: Final = 12

# The webbing the clips slide onto.
webbing_shoulder_size: Final = [50, 3]  # shoulder webbing, [width, thickness]
webbing_hip_size: Final = [37.5, 5]  # hip webbing, [width, thickness]
