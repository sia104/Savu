# Copyright 2014 Diamond Light Source Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. module:: spectrum_crop
   :platform: Unix
   :synopsis: A plugin to crop a spectra

.. moduleauthor:: Aaron D. Parsons <scientificsoftware@diamond.ac.uk>
"""

import logging
from savu.plugins.base_filter import BaseFilter
from savu.plugins.driver.cpu_plugin import CpuPlugin
from savu.plugins.utils import register_plugin#,dawn_compatible
import numpy as np
import savu.test.test_utils as tu
from scipy.interpolate import griddata


@register_plugin
class ListToProjections(BaseFilter, CpuPlugin):
    """
    Converts a list of points into a 2D projection

    :param step_size_x: step size in the interp, None if minimum chosen. Default: None.
    :param step_size_y: step size in the interp, None if minimum chosen. Default: None.

    """

    def __init__(self):
        logging.debug("interpolating projections")
        super(ListToProjections, self).__init__("ListToProjections")
        
    def pre_process(self):
        # assume all the projections are on the same axes
        in_datasets, _out_datasets = self.get_datasets()
        positions = in_datasets[0].meta_data.get_meta_data("xy")
        self.setup_grids(positions)

        
    def filter_frames(self, data):
        meshgridx, meshgridy = self.meshgrids
        data = data[0]
        print 'data',data.shape
        print 'meshgrid',np.prod(meshgridx.shape)
        print 'self.x',self.x.shape
        op = griddata((self.x, self.y),data, (meshgridx, meshgridy),fill_value=0)
        print 'op',op.shape
        return op

    def setup(self):
        logging.debug('setting up the interpolation')
        in_dataset, out_datasets = self.get_datasets()
        in_pData, out_pData = self.get_plugin_datasets()
        
        inshape = in_dataset[0].get_shape()

        in_datasets, _out_datasets = self.get_datasets()

        positions = in_datasets[0].meta_data.get_meta_data("xy")

        self.setup_grids(positions)
        out_projection_shape = self.meshgrids[0].shape
        in_pData[0].plugin_data_setup('PROJECTION', self.get_max_frames())
        proj_in_core_dirs= np.array(in_pData[0].get_core_directions())

        if len(proj_in_core_dirs)>1:
            raise IndexError("This plugin won't work since there are more than 1 core direction for the projection")
        
        outshape = list(inshape)
        proj_in_core_dirs = proj_in_core_dirs[0]
        outshape[proj_in_core_dirs] = out_projection_shape[0]
        outshape.insert(proj_in_core_dirs+1,out_projection_shape[1])
        
        axis_labels = in_datasets[0].get_axis_labels()
        axis_labels = [ix.keys()[0]+'.'+ix[ix.keys()[0]] for ix in axis_labels]
        axis_labels[proj_in_core_dirs] = 'x.microns'
        axis_labels.insert(proj_in_core_dirs+1,'y.microns')
        proj_out_core_dirs = (proj_in_core_dirs, proj_in_core_dirs+1)
        print proj_out_core_dirs
        allDimsOut = range(len(outshape))
        proj_out_slice_dirs = list(set(allDimsOut)-set(list(proj_out_core_dirs)))

        
        reshaped_projections = out_datasets[0]
        reshaped_projections.create_dataset(shape=tuple(outshape), axis_labels=axis_labels)
        reshaped_projections.add_pattern("PROJECTION", core_dir=proj_out_core_dirs, slice_dir=proj_out_slice_dirs)
        in_patterns = in_datasets[0].get_data_patterns()
        for pattern in in_patterns.keys():
            if pattern != "PROJECTION":
                core_dir = in_patterns[pattern]['core_dir']
                slice_dir = list(set(allDimsOut)-set(core_dir))
                dim_info = {'core_dir': core_dir, 'slice_dir': slice_dir}
                reshaped_projections.add_pattern(pattern, **dim_info)
        print outshape
        out_pData[0].plugin_data_setup('PROJECTION', self.get_max_frames())
#     
    def setup_grids(self,positions):
        x = positions[0,:]
        y = positions[1,:]
        self.x = x
        self.y = y
        if self.parameters['step_size_x'] is not None:
            self.step_size_x = self.parameters['step_size_x']
        else:
            abs_diff_x = abs(np.diff(x))
            abs_diff_x_masked = abs_diff_x[abs_diff_x>0.1]
            self.step_size_x = min(abs_diff_x_masked)
            
        if self.parameters['step_size_y'] is not None:
            self.step_size_y = self.parameters['step_size_y']
        else:
            abs_diff_y = abs(np.diff(y))
            abs_diff_y_masked = abs_diff_y[abs_diff_y>0.1]
            self.step_size_y = min(abs_diff_y_masked)
        
        min_x = np.min(x)
        max_x = np.max(x)
        min_y = np.min(y)
        max_y = np.max(y)
        nptsx  = (max_x - min_x) / self.step_size_x
        nptsy  = (max_y - min_y) / self.step_size_y
        grid_x = np.arange(min_x, max_x, (max_x-min_x)/ (nptsx))
        grid_y = np.arange(min_y, max_y, (max_y-min_y)/ (nptsy))
        self.meshgrids = np.meshgrid(grid_x, grid_y) 


    def get_max_frames(self):
        """
        This filter processes 1 frame at a time
        """
        return 1

    def get_plugin_pattern(self):
        return 'PROJECTION'

    def nOutput_datasets(self):
        return 1