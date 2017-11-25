from nnsim.module import Module
from nnsim.channel import Channel
from nnsim.simulator import Finish
from conv_ws.tb import WSArchTB
from fc_os.tb import OSArchTB

import numpy as np

class Conv(object):
    def __init__(self, image_size, filter_size, in_chn, out_chn, name):
        self.image_size = image_size
        self.filter_size = filter_size
        self.in_chn = in_chn
        self.out_chn = out_chn
        self.name = name

class FC(object):
    def __init__(self, input_size, output_size, name):
        self.input_size = input_size
        self.output_size = output_size
        self.name = name

class MetaArchTB(Module):
    def instantiate(self, arr_x, arr_y, chn_per_word, layers, batch_size):
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word
        self.layers = layers
        self.batch_size = batch_size

        self.started = False
        self.done_chn = Channel()

        self.ifmap_glb_depth = 0
        self.psum_glb_depth = 0
        self.weights_glb_depth = 0

        use_conv = False
        use_fc = False

        self.conv_tb = None
        self.fc_tb = None

        cur_image_size = None
        cur_in_chn = None
        is_conv = False

        for layer in self.layers:
            if isinstance(layer, Conv):
                if cur_image_size is None:
                    pass
                elif cur_image_size != layer.image_size or cur_in_chn != layer.in_chn:
                    raise Exception('Invalid conv image size for ' + layer.name)
                ifmap_glb_depth, psum_glb_depth, weights_glb_depth = WSArchTB.required_glb_depth(self.arr_x, self.arr_y, self.chn_per_word, layer.image_size, layer.filter_size, layer.in_chn, layer.out_chn)
                use_conv = True
                cur_image_size = layer.image_size
                cur_in_chn = layer.out_chn
                is_conv = True
            elif isinstance(layer, FC):
                if cur_image_size is None:
                    pass
                elif not is_conv and cur_image_size != layer.input_size:
                    raise Exception('Invalid fc dimension transition for ' + layer.name)
                elif is_conv and cur_image_size[0] * cur_image_size[1] * cur_in_chn != layer.input_size:
                    raise Exception('Invalid conv to fc dimension transition to ' + layer.name)
                ifmap_glb_depth, psum_glb_depth, weights_glb_depth = OSArchTB.required_glb_depth(self.arr_x, self.arr_y, self.chn_per_word, self.batch_size, layer.input_size, layer.output_size)
                use_fc = True
                cur_image_size = layer.output_size
                is_conv = False
            else:
                raise Exception('layer not valid')
            self.ifmap_glb_depth = max(self.ifmap_glb_depth, ifmap_glb_depth)
            self.psum_glb_depth = max(self.psum_glb_depth, psum_glb_depth)
            self.weights_glb_depth = max(self.weights_glb_depth, weights_glb_depth)

        if use_conv:
            self.conv_tb = WSArchTB(self.arr_x, self.arr_y, self.chn_per_word, self.done_chn, self.ifmap_glb_depth, self.psum_glb_depth, self.weights_glb_depth)
        if use_fc:
            self.fc_tb = OSArchTB(self.arr_x, self.arr_y, self.chn_per_word, self.done_chn, self.ifmap_glb_depth, self.psum_glb_depth, self.weights_glb_depth)

        self.layer_step = 0
        self.batch_step = 0
        self.conv_inputs = [None] * self.batch_size
        self.fc_input = None

    # (TODO): Pluggable conv filter and fc weights
    def tick(self):
        if not self.started or self.done_chn.valid():
            self.started = True
            layer = self.layers[self.layer_step]
            if self.done_chn.valid():
                valid = self.done_chn.pop()
                if not valid:
                    raise Finish('Validation Failed')
                if isinstance(layer, Conv):
                    self.conv_inputs[self.batch_step] = self.conv_tb.get_output()
                    self.batch_step += 1
                    if self.batch_step == self.batch_size:
                        self.batch_step = 0
                        self.layer_step += 1
                else:
                    self.fc_input = self.fc_tb.get_output()
                    self.layer_step += 1
            if self.layer_step == len(self.layers):
                raise Finish('Success')

            layer = self.layers[self.layer_step]

            # handle conv to fc transition
            if isinstance(layer, FC) and self.fc_input is None and self.conv_inputs[0] is not None:
                self.fc_input = np.zeros((self.batch_size, layer.input_size)).astype(np.int64)
                for i in range(self.batch_size):
                    self.fc_input[i] = self.conv_inputs[i].reshape(layer.input_size)

            if isinstance(layer, Conv):
                if self.conv_inputs[self.batch_step] is None:
                    self.conv_tb.configure(layer.image_size, layer.filter_size, layer.in_chn, layer.out_chn)
                else:
                    self.conv_tb.configure_fixed(self.conv_inputs[self.batch_step], layer.filter_size, layer.in_chn, layer.out_chn)
            elif isinstance(layer, FC):
                if self.fc_input is None:
                    self.fc_tb.configure(self.batch_size, layer.input_size, layer.output_size)
                else:
                    self.fc_tb.configure_fixed(self.fc_input, layer.output_size)
            else:
                raise Exception('layer not valid')
