import os

import colour
import numpy as np

from colour_demosaicing import (
    EXAMPLES_RESOURCES_DIRECTORY,
    demosaicing_CFA_Bayer_bilinear,
    demosaicing_CFA_Bayer_Malvar2004,
    demosaicing_CFA_Bayer_Menon2007,
    mosaicing_CFA_Bayer)

#colour.plotting.colour_style()

#colour.utilities.describe_environment();


def debayer(img, pattern='RGGB', method='bilinear'):
    if method=='bilinear':
        return demosaicing_CFA_Bayer_bilinear(img, pattern)
    elif method == 'malvar':
        return demosaicing_CFA_Bayer_Malvar2004(img)
    elif method == 'menon':
        demosaicing_CFA_Bayer_Menon2007(img)
    else:
        print('Debayer: Unknown method {}'.format(img))
        return None