from nnsim.module import Module
from nnsim.channel import Channel
from .os import OSArch
from .stimulus import Stimulus
import math

class OSArchTB(Module):
    @staticmethod
    def required_glb_depth(arr_x, arr_y, chn_per_word, batch_size, input_size, output_size):
        ceil_batch = int(math.ceil(float(batch_size) / arr_y)) * arr_y
        ceil_output = int(math.ceil(float(output_size) / arr_x)) * arr_x

        ifmap_glb_depth = ceil_batch * input_size // arr_y
        psum_glb_depth = 0
        weight_glb_depth = (input_size+1) * ceil_output // arr_x

        return ifmap_glb_depth, psum_glb_depth, weight_glb_depth

    def instantiate(self, arr_x, arr_y, chn_per_word, done_chn, ifmap_glb_depth, psum_glb_depth, weight_glb_depth):
        self.name = 'fc_tb'
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word

        self.batch_size = None
        self.input_size = None
        self.output_size = None

        self.ceil_batch = None
        self.ceil_output = None

        self.input_chn = Channel(name='arch_input_chn')
        self.output_chn = Channel(name='arch_output_chn')
        self.done_chn = done_chn

        self.stimulus = Stimulus(self.arr_x, self.arr_y, self.chn_per_word,
            self.input_chn, self.output_chn, self.done_chn)
        self.dut = OSArch(self.arr_x, self.arr_y, self.input_chn,
                self.output_chn, self.chn_per_word, ifmap_glb_depth,
                weight_glb_depth)

    def configure(self, batch_size, input_size, output_size):
        self.batch_size = batch_size
        self.input_size = input_size
        self.output_size = output_size

        self.ceil_batch = int(math.ceil(float(self.batch_size) / self.arr_y)) * self.arr_y
        self.ceil_output = int(math.ceil(float(self.output_size) / self.arr_x)) * self.arr_x

        ifmap, weights, bias = self.stimulus.configure(self.batch_size, self.input_size, self.output_size)
        self.dut.configure(self.ceil_batch, self.input_size, self.ceil_output)

        return ifmap, weights, bias

    def configure_fixed_image(self, image, output_size):
        self.batch_size = image.shape[0]
        self.input_size = image.shape[1]
        self.output_size = output_size

        self.ceil_batch = int(math.ceil(float(self.batch_size) / self.arr_y)) * self.arr_y
        self.ceil_output = int(math.ceil(float(self.output_size) / self.arr_x)) * self.arr_x

        weights, bias = self.stimulus.configure_fixed_image(image, self.output_size)
        self.dut.configure(self.ceil_batch, self.input_size, self.ceil_output)

        return weights, bias

    def configure_fixed(self, image, weights, bias):
        self.batch_size = image.shape[0]
        self.input_size = image.shape[1]
        self.output_size = bias.shape[0]

        self.ceil_batch = int(math.ceil(float(self.batch_size) / self.arr_y)) * self.arr_y
        self.ceil_output = int(math.ceil(float(self.output_size) / self.arr_x)) * self.arr_x

        self.stimulus.configure_fixed(image, weights, bias)
        self.dut.configure(self.ceil_batch, self.input_size, self.ceil_output)

    def get_output(self):
        return self.stimulus.deserializer.ofmap
