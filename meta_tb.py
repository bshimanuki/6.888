from nnsim.module import Module
from nnsim.channel import Channel
from nnsim.simulator import Finish
from conv_ws.tb import WSArchTB
from fc_os.tb import OSArchTB

class Conv(object):
    def __init__(self, image_size, filter_size, in_chn, out_chn):
        self.image_size = image_size
        self.filter_size = filter_size
        self.in_chn = in_chn
        self.out_chn = out_chn

class FC(object):
    def __init__(self, batch_size, input_size, output_size):
        self.batch_size = batch_size
        self.input_size = input_size
        self.output_size = output_size

class MetaArchTB(Module):
    def instantiate(self, arr_x, arr_y, chn_per_word, layers):
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word
        self.layers = layers

        self.started = False
        self.done_chn = Channel()

        self.ifmap_glb_depth = 0
        self.psum_glb_depth = 0
        self.weights_glb_depth = 0

        for layer in self.layers:
            if isinstance(layer, Conv):
                ifmap_glb_depth, psum_glb_depth, weights_glb_depth = WSArchTB.required_glb_depth(self.arr_x, self.arr_y, self.chn_per_word, layer.image_size, layer.filter_size, layer.in_chn, layer.out_chn)
            elif isinstance(layer, FC):
                ifmap_glb_depth, psum_glb_depth, weights_glb_depth = OSArchTB.required_glb_depth(self.arr_x, self.arr_y, self.chn_per_word, layer.batch_size, layer.input_size, layer.output_size)
            else:
                raise Exception('layer not valid')
            self.ifmap_glb_depth = max(self.ifmap_glb_depth, ifmap_glb_depth)
            self.psum_glb_depth = max(self.psum_glb_depth, psum_glb_depth)
            self.weights_glb_depth = max(self.weights_glb_depth, weights_glb_depth)

        self.conv_tb = WSArchTB(self.arr_x, self.arr_y, self.chn_per_word, self.done_chn, self.ifmap_glb_depth, self.psum_glb_depth, self.weights_glb_depth)
        self.fc_tb = OSArchTB(self.arr_x, self.arr_y, self.chn_per_word, self.done_chn, self.ifmap_glb_depth, self.psum_glb_depth, self.weights_glb_depth)

        self.layer_step = 0

    def tick(self):
        if not self.started or self.done_chn.valid():
            self.started = True
            if self.done_chn.valid():
                valid = self.done_chn.pop()
                if not valid:
                    raise Finish('Validation Failed')
            if self.layer_step == len(self.layers):
                raise Finish('Success')

            layer = self.layers[self.layer_step]
            self.layer_step += 1
            if isinstance(layer, Conv):
                self.conv_tb.configure(layer.image_size, layer.filter_size, layer.in_chn, layer.out_chn)
            elif isinstance(layer, FC):
                self.fc_tb.configure(layer.batch_size, layer.input_size, layer.output_size)
            else:
                raise Exception('layer not valid')
