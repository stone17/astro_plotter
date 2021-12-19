import matplotlib.pyplot as plt
from astropy.visualization import astropy_mpl_style
plt.style.use(astropy_mpl_style)

from astropy.utils.data import get_pkg_data_filename
from astropy.io import fits
import numpy as np
import os
from fast_histogram import histogram1d

import libs.image_debayer as image_debayer
import traceback

def main():
    img = IMAGE('..\\images\\IC 5146-2021-12-16_21-00-03_180.00s_Gain_200_-5.00c_offset_60_HFR_2.89_0000.fits')
    img.load()
    img.debayer()

    plt.figure()
    plt.grid(False)
    plt.imshow(img.data_cfa/np.max(img.data_cfa))
    plt.colorbar()
    plt.show()


class IMAGE():
    def __init__(self, path):
        self.path = path
        _, self.image_type = os.path.splitext(self.path)
        self.image_params = []
        self.data_mono = None
        self.data_cfa = None
        self.is_demosaiced = False

    #def __setattr__(self, attr, value):
    #    if attr in self.attributes:
    #        setattr(self, attr, value)
    #    else:
    #        super().__setattr__(attr, value)

    #def __getattr__(self, attr):
    #    if attr in self.attributes:
    #        return getattr(self, attr)

    def load(self):
        if self.image_type == '.fits':
            self.open_fits()
        else:
            print('Image type not supported {}'.format(self.image_type))

    def open_fits(self):
        try:
            fits.info(self.path)
        except Exception:
            traceback.print_exc()
            return

        with fits.open(self.path) as fn:
            for k in fn[0].header:
                super().__setattr__(k, fn[0].header[k])
                self.image_params.append([k, fn[0].header[k]])
        self.data_mono = fits.getdata(self.path, ext=0)
        self.histogram_mono = histogram1d(self.data_mono, range=[0, 2**self.BITPIX], bins=256)
        self.histogram_edges = np.linspace(0, 2**self.BITPIX, 256)
        self.clip_mono = self.get_clip(self.histogram_mono, self.histogram_edges, [0.01, 0.9])

    def debayer(self, method='bilinear'):
        if self.is_demosaiced:
            print('Image is already demosaiced!')
            return
        if self.data_mono is not None:
            if hasattr(self, 'BAYERPAT'):
                pattern = self.BAYERPAT
            else:
                pattern = 'RGGB'
            print('Demosaicing with {}'.format(pattern))
            self.data_cfa = image_debayer.debayer(self.data_mono, pattern)
            self.histogram_r = histogram1d(self.data_cfa[:,:,0], range=[0, 2**self.BITPIX], bins=256)
            self.histogram_g = histogram1d(self.data_cfa[:,:,1], range=[0, 2**self.BITPIX], bins=256)
            self.histogram_b = histogram1d(self.data_cfa[:,:,2], range=[0, 2**self.BITPIX], bins=256)
            self.clip_cfa = self.get_clip(self.histogram_g, self.histogram_edges, [0.1, 0.995])
            # simple grey-world WB
            r_mean = np.mean(self.data_cfa[:,:,0])
            g_mean = np.mean(self.data_cfa[:,:,1])
            b_mean = np.mean(self.data_cfa[:,:,2])
            self.data_cfa[:,:,0] /= (r_mean / g_mean)
            self.data_cfa[:,:,2] /= (b_mean / g_mean)
            self.is_demosaiced = True
        else:
            print('Image not loaded!')

    def get_clip(self, histogram, bin_edges, clip):
        depth = len(histogram)
        tsum = np.sum(histogram)
        psum = 0
        low_clip = clip[0]
        high_clip = clip[1]
        clip_idx = [0, depth]
        for i in range(depth):
            psum += histogram[i] / tsum
            if psum < low_clip:
                clip_idx[0] = bin_edges[i]
            if psum > high_clip:
                clip_idx[1] = bin_edges[i]
                break
        return clip_idx

if __name__ == "__main__":
    main()