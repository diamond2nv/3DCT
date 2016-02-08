
"""
Establishes a correlation based on the 3D rigid body transformation 
(rotation, scale and translation) when marker positions are specified
as 3D coordinates in the initial system and 2D coordinates (z component
is missing) in the final system.

Once the coordinate system transformation is established, coordinates of
any object of interest in the initial system can be transformed to the 
final system.

Typically the initial (3D) system is a light micrroscopy (confocal) image
and the final (2D) is a ion beam image.

Requires the following coordinates:
  - marker coordinates in the initial (3D) system
  - corresponding marker coordinates in the final (2D) system
  - coordinates of objects of interest in the original system

These coordinates have to be saved in a file, in a table where rows represent
individual points (markers and objects of interest) and (some of) columns
contain x, y and z coordinates.

It is not necessary, but it is recommended to use ImageJ / Fuji to generate
these coordinates. What follows is the procedure which is compatible with
the default values in the File format sectin of the Parameters (below):

  1) (optional) Set to pixels: ImageJ / Image / Properties: Units = pix; 
     x width = y width = 1

  2) Open measurement options by Analyze / Set measurements

  3) Set measurements: mean grey and stack position are sufficient; 
     display label, add to overlay, decimal places=1 are useful

  4) To store selected points to ROI (useful): Edit / Options / Point tool 
     (or double click on point tool): Auto measure, add to ROI, label

  5) Activate point tool

  6) For each point (markers in both systems and objects of interest): Click 
     on a point (if auto measure was not set need Ctrl-M to put it in 
     the results; shift-click might also work)

  7) When ROI manager opens or Analyze / Tools / ROI manager check 
     ROI manager / More / Options / Associate ... with slices in order that 
     points are shown only on the corresponding slices 

  8) Save results: Results / File / Save as. The name of this file

  9) Save ROIs (in zip format) : ROI manager / More / Save

Steps 4, 7 and 9 are useful because they allow saving ROIs and retrieving 
them at alater point, but are not strictly necessary. Picks saved at ROIs 
can be displayed on the image at a later point but it's hard to read the 
pick coordinates. On the contrary, the coordinates are easily accessible 
in the results file, but it is difficult to display the picks on
the same or on another image.
 

# Author: Vladan Lucic (Max Planck Institute for Biochemistry)
# $Id: 3d-2d_correlation.py 1213 2015-07-01 13:59:08Z vladan $
"""

__version__ = "$Revision: 1213 $"


import os
import numpy as np
import scipy as sp

import pyto
import pyto.scripts.common as common
from pyto.geometry.rigid_3d import Rigid3D


##################################################################
#
# Parameters
#
#################################################################

##################################################################
#
# Markers
#

# initial (3D) markers file name 
markers_3d_file = 'picks.dat'

# rows where 3D markers are; rows numbered from 0, top (info) row skipped
#marker_3d_rows = [3, 7, 10, 11, 12, 17, 20, 21]
marker_3d_rows = [3, 7, 10, 11, 12, 17, 21]

# final (2D) markers file name
markers_2d_file = markers_3d_file

# rows where 2D markers are, rows numbered from 0, top (info) row skipped
#marker_2d_rows = [6, 8, 9, 13, 14, 16, 18, 19]
marker_2d_rows = [6, 8, 9, 13, 14, 16, 19]

##################################################################
#
# Spots to be correlated
#

# spots (3D) file name
spots_3d_file = markers_3d_file

# rows where spots are, rows numbered from 0, top (info) row skipped
spot_3d_rows = [20]

##################################################################
#
# Results
#

# results file name
results_file = 'correlation.dat'

##################################################################
#
# Initial conditions and optimization
#

# do multiple optimization runs with different initial rotation (True / False)
random_rotations = True

# initial rotation specified by Euler angles:
#   phi, theta, psi, extrinsic, 'X' or 'ZXZ' mode in degrees
# uncomment one of the following
#rotation_init = None            # use default rotation
#rotation_init = [23, 45, 67]   # specified rotation angles
rotation_init = 'gl2'            # use 2d affine to get initial rotation

# restrict random initial rotations to a neighborhood of the initial rotation
# used if rotation_init is is specified by angles or it is '2d'
# should be < 0.5, value 0.1 roughly corresponds to 15 deg
restrict_rotations = 0.1   

# optimze of fix fluorescence to ib magnification 
# uncomment one of the following
scale = None    # optimize 
#scale = 150.   # fixed scale, no optimization

# do multiple optimization runs with different initial scale (True / False)
random_scale = True

# initial value for fluorescence to ib magnification, used only if scale=None
#scale_init = 1.               # specified value
scale_init = 'gl2'            # use 2d transform to get init scale

# number of optimization runs, each run has different initial values;
# first run has initial conditions specified by rotation_init and scale_init
# (uncomment one of the following)
#ninit = 1    # one run only (two runs if rotation_init is '2d') 
ninit = 10    # multiple runs, random_rotations or random_scale should be True

##################################################################
#
# File format related
#

# comment symbol
comments=None

# number of top rows to skip
skiprows=1

# filed delimiter
delimiter='\t'

# x, y and z coordinate columns, in this order
usecols=[3, 4, 5]

# alternative (more flexible) form to specify columns
# not implemented yet
dtype = {
    'names' : ('id', 'label', 'density', 'x', 'y', 'z'), 
    'formats' : ('i', 'a40', 'f', 'f', 'f', 'i')}
fmt = ('%4i', '%s', '%9.3f', '%7.1f', '%7.1f', '%7.1f')


#####################################################################
#
# Functions
#
#####################################################################

# ToDo pick rows by order or by index

# print transformation params
def write_results(
        transf, res_file_name, spots_3d, spots_2d, 
        markers_3d, transformed_3d, markers_2d):
    """
    """

    # open results file
    res_file = open(res_file_name, 'w')
    
    # header top
    header = common.make_top_header()

    # extract eulers in degrees
    eulers = transf.extract_euler(r=transf.q, mode='x', ret='one') 
    eulers = eulers * 180 / np.pi

    # correlation parameters
    header.extend([
        "#",
        "# Transformation parameters",
        "#",
        "#   - rotation (Euler phi, theta psi): [%6.3f, %6.3f, %6.3f]" \
            % (eulers[0], eulers[1], eulers[2]),
        "#   - scale = %6.3f" % transf.s_scalar,
        "#   - translation = [%6.3f, %6.3f, %6.3f]" \
             % (transf.d[0], transf.d[1], transf.d[2]),
        "#   - rms error (in 2d pixels) = %6.2f" % transf.rmsError
        ])

    # check success
    if transf.optimizeResult['success']:
        header.extend([
            "#   - optimization successful"])
    else:
        header.extend([
            "#",
            "# ERROR: Optimization failed (status %d)" \
                % transf.optimizeResult['status'],
            "#   Repeat run with changed initial values and / or "
            + "increased ninit"])

    # write header
    for line in header:
        res_file.write(line + os.linesep)

    # prepare marker lines
    table = ([
        "#",
        "#",
        "# Transformation of initial (3D) markers",
        "#",
        "#  Initial (3D) markers      Transformed initial"
         + "     Final (2D) markers "])
    out_vars = [markers_3d[0,:], markers_3d[1,:], markers_3d[2,:], 
                transformed_3d[0,:], transformed_3d[1,:], transformed_3d[2,:],
                markers_2d[0,:], markers_2d[1,:]]
    out_format = '  %6.0f %6.0f %6.0f     %7.2f %7.2f %7.2f     %7.2f %7.2f  '
    ids = range(markers_3d.shape[1])
    res_tab_markers = pyto.io.util.arrayFormat(
        arrays=out_vars, format=out_format, indices=ids, prependIndex=False)
    table.extend(res_tab_markers)

    # prepare data lines
    table.extend([
        "#",
        "#",
        "# Correlation of 3D spots to 2D",
        "#",
        "#       Spots (3D)             Correlated spots"])
    out_vars = [spots_3d[0,:], spots_3d[1,:], spots_3d[2,:], 
                spots_2d[0,:], spots_2d[1,:], spots_2d[2,:]]
    out_format = '  %6.0f %6.0f %6.0f     %7.2f %7.2f %7.2f '
    ids = range(spots_3d.shape[1])
    res_tab_spots = pyto.io.util.arrayFormat(
        arrays=out_vars, format=out_format, indices=ids, prependIndex=False)
    table.extend(res_tab_spots)

    # write data table
    for line in table:
        res_file.write(line + os.linesep)


#####################################################################
#
# Main
#
#####################################################################


def main():

    # read fluo markers 
    mark_3d_all = np.loadtxt(
        markers_3d_file, delimiter=delimiter, 
        comments=comments, skiprows=skiprows, usecols=usecols)
    mark_3d = mark_3d_all[marker_3d_rows].transpose()

    # alternative 
    #mark_3d = np.loadtxt(
    #    markers_3d_file, delimiter=delimiter, comments=comments, 
    #    skiprows=skiprows, usecols=usecols, dtype=dtype)
    
    # read ib markers 
    mark_2d_whole = np.loadtxt(
        markers_2d_file, delimiter=delimiter, 
        comments=comments, skiprows=skiprows, usecols=usecols)
    mark_2d = mark_2d_whole[marker_2d_rows][:,:2].transpose()

    # convert Eulers in degrees to Caley-Klein params
    if (rotation_init is not None) and (rotation_init != 'gl2'):
        rotation_init_rad = rotation_init * np.pi / 180
        einit = Rigid3D.euler_to_ck(angles=rotation_init_rad, mode='x')
    else:
        einit = rotation_init

    # establish correlation
    transf = pyto.geometry.Rigid3D.find_32(
        x=mark_3d, y=mark_2d, scale=scale, 
        randome=random_rotations, einit=einit, einit_dist=restrict_rotations, 
        randoms=random_scale, sinit=scale_init, ninit=ninit)

    # read fluo spots 
    spots_3d = np.loadtxt(
        spots_3d_file, delimiter=delimiter, 
        comments=comments, skiprows=skiprows, usecols=usecols)
    spots_3d = spots_3d[spot_3d_rows].transpose()

    # correlate spots
    spots_2d = transf.transform(x=spots_3d)

    # transform markers
    transf_3d = transf.transform(x=mark_3d)

    # calculate translation if rotation center is not at (0,0,0)
    rotation_center = [2, 3, 4]
    modified_translation = transf.recalculate_translation(
        rotation_center=rotation_center)
    #print 'modified_translation: ', modified_translation

    # write transformation params and correlation
    write_results(
        transf=transf, res_file_name=results_file, 
        spots_3d=spots_3d, spots_2d=spots_2d,
        markers_3d=mark_3d, transformed_3d=transf_3d, markers_2d=mark_2d)

    return transf


# run if standalone
if __name__ == '__main__':
    main()