  #  coding: utf-8
"""随机选择10个事件并将其横截面画出"""

import matplotlib.pyplot as plt
import pandas as pd
import random
import numpy as np
from scipy.spatial.distance import cdist

SEED = 666
#read the data
signals = pd.read_csv("/home/wangkaipu/IHEP/data/signals.csv")
backgrounds = pd.read_csv("/home/wangkaipu/IHEP/data/backgrounds.csv")
max_event_id_all = max(max(signals.event_id), max(backgrounds.event_id))
r_max = max(max(backgrounds.r), max(signals.r))
r_min = min(min(backgrounds.r), min(signals.r))
r_sig = signals.r
r_bkg = backgrounds.r
r_c = list(r_sig)
r_c.extend(list(r_bkg))
rho_bins = len(np.unique(r_c))

class Cylinder(object):
    """
    define the cylindrical array of points read in from positional information.
    It returns a flat enumerator of the points in the array.

    param:
    r_max the maxmanal radius of the geometry
    r_min  the minmainal radius of the geometry
    rho_bins the bins alang by the radius
    wire_x  the x of a point
    wire_y   the y of a point
    layer_ID  which layer the point layies
    arc_res  the gap between bins alang by the layer
    n_by_layer  the number of point on each layer
    n_points  the number of all the points
    """
    def __init__(self,r_max=None,r_min=None,rho_bins=None,point_x=None,point_y=None,layerID=None,arc_res=0):
        self.r_max=r_max
        self.r_min=r_min
        self.rho_bins=rho_bins
        self.arc_res=arc_res
        self.point_x = point_x
        self.point_y = point_y
        self.point_layers = layerID
        _,self.n_by_layer = np.unique(layerID,return_counts=True)
        self.first_point = self._get_first_point(self.n_by_layer)
        self.n_points = sum(self.n_by_layer)

    def _get_first_point(self,n_by_layer):
        """
        Returns the point_id of the first point in each layer
        :param
        n_by_layer: the number of points in each layer

        :return:numpy array of first point in each layer
        """
        first_point = np.zeros(len(n_by_layer),dtype = int)
        for i in range(len(n_by_layer)):
            first_point[i] = sum(n_by_layer[:i])
        return first_point

    def get_rhos_and_phis(self):
        """
        Returns the positionos of each point in radial system

        :return:pair of numpy.arrays of shape [n_points],
         - first one contains rho's(radii)
         - second one contains phi's(angles)
        """
        #the distance between layers
        drho = (self.r_max - self.r_min) / (self.rho_bins - 1)
        #a array of radii on each layer
        r_track_cent = [self.r_min + drho * n for n in range(self.rho_bins)]
        if self.arc_res==0:
             self.arc_res = drho
        n_by_layer = [int(2 * np.pi * r_track_cent[n] / self.arc_res) for n in range(self.rho_bins)]
        #the phi between two bins which are on the same layer
        dphi_by_layer = [self.arc_res / r_track_cent[n] for n in range(self.rho_bins)]
        rho_by_points = []
        phi_by_layer = []
        for i in range(self.rho_bins):
            point_phi_n = [dphi_by_layer[i] * n for n in range(n_by_layer[i])]
            a = np.ones((len(point_phi_n), 1), dtype='float')
            rho_by_points.extend(a * r_track_cent[i])
            phi_by_layer.extend(point_phi_n)
        return rho_by_points,phi_by_layer

    def get_points_rho_and_phi(self):
        rs = []
        phis = []
        for point_x,point_y in zip(self.point_x,self.point_y):
            if point_x == 0:
                if point_y > 0:
                    phi = np.pi / 2
                else:
                    phi = 3 * np.pi / 2
            elif point_x < 0:
                phi = np.arctan(point_y / point_x) + np.pi
            else:
                phi = np.arctan(point_y / point_x)
            r = np.sqrt(point_x ** 2 + point_y ** 2)
            rs.append(r)
            phis.append(phi)
        return rs,phis


def plot_add_circle(x, y, radius, color="green", lw=1,center_weight=None, spread=0, l_alpha=0.8,
                    s_alpha=0.025, fill=False, edgecolor='g',**kwargs):
    """
    Add a circle to our plot

    :param x:        x location of circle centre
    :param y:        y location of circle centre
    :param radius:   radius of circle
    :param color:    color of circle
    :param lw:       line width of circle
    :param spread:   spread of circle, symmetric
    :param l_alpha:  overall normalization on weight of line
    :param s_alpha:  overall normalization on weight of spread
    """
    ## TODO check gca() usage here
    if center_weight!=None:
        lw=center_weight
    plot_circle = plt.Circle((x, y), radius, transform=plt.gca().transData._b,
                             color=color, fill=fill, alpha=l_alpha, lw=lw, edgecolor=edgecolor,**kwargs)
    plt.gca().add_artist(plot_circle)

CDC_R_MAX = 80
CDC_R_MIN = 50
R_MAX = 39
R_MEAN = 33
R_MIN = 28
TRK_RHO_SGMA = 3
TRGT_RHO = 10
RHO_BINS = 20


# divide potential track center area into small bins
class Houghspace(object):
    def __init__(self):
        # signals.r.max,signals.r.min = 80.199996,53.0
        self.r_max = R_MAX
        self.r_min = R_MIN
        self.trk_rho_sgma = TRK_RHO_SGMA
        self.r_mean = R_MEAN

        self.r_max_center = CDC_R_MAX - R_MIN
        self.r_min_center = CDC_R_MIN - R_MAX  # max(r_max - trgt_rho, cdc_rho_min - r_max)

        self.rho_bins = RHO_BINS
        self.n_layer = np.arange(RHO_BINS)
        self.r_by_layer = np.zeros(self.rho_bins, dtype="float")
        self.n_by_layer = np.zeros(self.rho_bins, dtype="int")
        self.rho_gap = (self.r_max_center - self.r_min_center) / (self.rho_bins - 1)
        self.arc_gap = self.rho_gap

        # assign values of r,n to each layer
        self.r_by_layer = [self.r_min_center + self.n_layer[n] * self.rho_gap for n in self.n_layer]
        self.n_by_layer = [int(2 * np.pi * self.r_by_layer[n] / self.arc_gap) for n in self.n_layer]

        # assign values of r,phi to each point
        self.n_points = np.arange(np.sum(self.n_by_layer))
        self.rho_points = np.zeros(np.sum(self.n_by_layer), dtype="float")
        self.phi_points = np.zeros(np.sum(self.n_by_layer), dtype="float")

        self.rho_points = np.repeat(self.r_by_layer, self.n_by_layer)

        self.n_first = np.zeros(self.rho_bins, dtype="int")
        for i in self.n_layer:
            self.n_first[i] = np.sum(self.n_by_layer[:i])
        self.n_points_on_layer = self.n_points - np.repeat(self.n_first, self.n_by_layer)
        self.phi_points = self.n_points_on_layer * self.arc_gap / self.rho_points

        # assign values of x,y to each point
        self.x_points = self.rho_points * np.cos(self.phi_points)
        self.y_points = self.rho_points * np.sin(self.phi_points)
        self.xy_points = np.column_stack((self.x_points, self.y_points))

hough=Houghspace()
XY_NAME = ['xe0', 'ye0']


# perform Hough Transform
class HoughTransform(object):

    def __init__(self, data_sig, data_bak, y_pre=1, xy_name=XY_NAME):
        hf = Houghspace()
        r_max = hf.r_max
        r_min = hf.r_min
        trk_rho_sgma = hf.trk_rho_sgma

        xy_sig = data_sig[xy_name]
        xy_bak = data_bak[xy_name]
        xy_hits = np.concatenate((xy_sig, xy_bak), axis=0)

        n_of_points = np.sum(hf.n_by_layer)



        weight = np.transpose([y_pre])
        vt_points = np.zeros(n_of_points)

        # vote on track centers/points
        dist = cdist(xy_hits, hf.xy_points)
        result = np.where(dist <= r_max + trk_rho_sgma, dist, 0)
        result = np.where(result >= r_min - trk_rho_sgma, 1, 0)
        vote_table = result * weight

        self.vt_points_sig = np.sum(result[:len(data_sig)], axis=0)  # ##################
        max_vpon_sig = np.amax(self.vt_points_sig)
        min_vpon_sig = np.amin(self.vt_points_sig)
        self.vt_points_sig = (self.vt_points_sig - min_vpon_sig) / (max_vpon_sig - min_vpon_sig)  # normalized

        vt_points = vote_table.sum(axis=0)
        max_vpon = np.amax(vt_points)
        min_vpon = np.amin(vt_points)
        # print(max_vpon, min_vpon)
        vt_points = (vt_points - min_vpon) / (max_vpon - min_vpon) * 15
        self.vt_points = vt_points / 15  # normalized

        # vote on signals and backgrounds
        wet_points = np.exp(vt_points)
        self.vt_hits = np.sum(result * wet_points, axis=1)
        vt_max = np.amax(self.vt_hits)
        vt_min = np.amin(self.vt_hits)
        self.vt_hits = (self.vt_hits - vt_min) / (vt_max - vt_min)  # normalized
        self.vt_sigs = self.vt_hits[:len(data_sig)]
        self.vt_baks = self.vt_hits[len(data_sig):]

event_id = random.randint(0, max_event_id_all)
sub_signals = signals[signals.event_id == event_id]
sub_backgrounds = backgrounds[backgrounds.event_id == event_id]
houghtransfrom = HoughTransform(sub_signals, sub_backgrounds)
vt_sig = houghtransfrom.vt_sigs
vt_bak = houghtransfrom.vt_baks
vresult_sig = houghtransfrom.vt_points_sig
vresult = houghtransfrom.vt_points

def putout(hough=hough,signals=sub_signals,backgrounds=sub_backgrounds,trackcenter=False,circlebysig=False,circlebytrackcenter=False,
           tkctrbywt=False,backgrounds_=True,backgroundsbywt=False,signals_=True,signalsbywt=False,vt_sig=vt_sig,vt_bak=vt_bak,
           vresult_sig=vresult_sig,vresult=vresult,max_event_id=max_event_id_all,sub_data=True,min_event_id=0,out=False):






    # draw the cells

    vrslt_nom = (vresult - np.min(vresult)) / (np.max(vresult) - np.min(vresult)) * 30
    vrslt_nom = np.exp(vrslt_nom)
    vrslt_nom = (vrslt_nom - min(vrslt_nom)) / (max(vrslt_nom) - min(vrslt_nom))*15
    vrslt_nom_sig = (vresult_sig - np.min(vresult_sig)) / (np.max(vresult_sig) - np.min(vresult_sig))
    vrslt_nom_sig = np.exp(vrslt_nom_sig)
    vrslt_nom_sig = (vrslt_nom_sig - np.amin(vrslt_nom_sig)) / (np.amax(vrslt_nom_sig) - np.amin(vrslt_nom_sig)) * 15


    min_vt = min(np.amin(vt_sig),np.amin(vt_bak))
    max_vt = max(np.amax(vt_sig),np.amax(vt_bak))
    vt_sig_nom = (vt_sig - min_vt) / (max_vt - min_vt)*8
    vt_bak_nom = (vt_bak - min_vt) / (max_vt - min_vt)*8

    vt_bak_nom = np.exp(vt_bak_nom)
    vt_sig_nom = np.exp(vt_sig_nom)
    max_ = max(np.amax(vt_sig_nom),np.amax(vt_bak_nom))
    min_ = min(np.amin(vt_sig_nom),np.amin(vt_bak_nom))
    vt_bkg_nom = (vt_bak_nom - min_) / (max_ - min_) * 25
    vt_sig_nom = (vt_sig_nom - min_) / (max_ - min_) * 25


    for _ in range(1):
        if out:
            random.seed(SEED)

            event_id = random.choice(backgrounds.event_id)
            sub_signals = signals[signals.event_id == event_id]
            sub_backgrounds = backgrounds[backgrounds.event_id == event_id]
        else:

            sub_signals = signals
            sub_backgrounds = backgrounds

        # draw the wirecells
        track = Cylinder(r_max=r_max, r_min=r_min, rho_bins=rho_bins)
        rho_by_points, phi_by_points = track.get_rhos_and_phis()
        fig = plt.figure(figsize=(8, 8))
        axs = fig.add_subplot(111, projection='polar')
        axs.scatter(phi_by_points, rho_by_points, s=1, c='g', alpha=0.3, marker='.')

        # draw the trackcenters
        if trackcenter:
            axs.scatter(hough.phi_points, hough.rho_points, s=1, c='y', alpha=1, marker='.', zorder=10)

        # draw the circles centered by the signals
        if circlebysig:
            x_s = list(sub_signals.xe0)
            y_s = list(sub_signals.ye0)
            for i in range(len(x_s)):
                plot_add_circle(x_s[i], y_s[i], hough.r_by_layer[10],center_weight=vrslt_nom_sig[i])

        # draw the trackcenters by weight
        if tkctrbywt:
            axs.scatter(hough.phi_points, hough.rho_points, s=vrslt_nom, c='y', alpha=1, marker='o', zorder=10)

        # draw the circles centered by trackcenters which are  weighted
        if circlebytrackcenter:
            for i in range(len(hough.x_points)):
                plot_add_circle(hough.x_points[i], hough.y_points[i], hough.r_by_layer[10],
                                    center_weight=vrslt_nom[i])

        # draw backgrounds first
        if backgrounds_ or backgroundsbywt:
            track = Cylinder(point_x=sub_backgrounds.xe0, point_y=sub_backgrounds.ye0)
            r_bkg0, phi_bkg0 = track.get_points_rho_and_phi()
            track = Cylinder(point_x=sub_backgrounds.xe1, point_y=sub_backgrounds.ye1)
            r_bkg1, phi_bkg1 = track.get_points_rho_and_phi()
            if backgrounds_:
                r_bkg = [r_bkg0, r_bkg1]
                phi_bkg = [phi_bkg0, phi_bkg1]
                axs.plot(phi_bkg, r_bkg, '-', c='r', lw=1, alpha=0.5)
            if backgroundsbywt:
                axs.scatter(phi_bkg0, r_bkg0, s=15, c='', alpha=0.3, edgecolors='r',
                            marker='o', zorder=10)
                axs.scatter(phi_bkg0, r_bkg0, s=vt_bkg_nom, c='r', alpha=1, marker='.', zorder=10)



        # draw the signals
        if signals_ or signalsbywt:
            track = Cylinder(point_x=sub_signals.xe0, point_y=sub_signals.ye0)
            r_sig0, phi_sig0 = track.get_points_rho_and_phi()
            track = Cylinder(point_x=sub_signals.xe1, point_y=sub_signals.ye1)
            r_sig1, phi_sig1 = track.get_points_rho_and_phi()
            if signals_:
                r_sig = [r_sig0, r_sig1]
                phi_sig = [phi_sig0, phi_sig1]
                axs.plot(phi_sig, r_sig, '-', c='b', lw=1, alpha=0.5)
            if signalsbywt:
                axs.scatter(phi_sig0, r_sig0, s=15, c='', alpha=0.3, edgecolors='b',
                            marker='o', zorder=10)
                axs.scatter(phi_sig0, r_sig0, s=vt_sig_nom, c='b', alpha=1, marker='.', zorder=10)

        axs.grid(True, linestyle="--", alpha=0.5)
        axs.set_rgrids([0, 50, 83])
        axs.set_rlim(0, 83)
        plt.show()
        plt.close()
        pass


putout()

