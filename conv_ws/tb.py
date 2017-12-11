from nnsim.module import Module
from nnsim.channel import Channel
from .ws import WSArch
from .stimulus import Stimulus
import math

class WSArchTB(Module):
    @staticmethod
    def required_glb_depth(arr_x, arr_y, chn_per_word, image_size, filter_size, full_in_chn, full_out_chn):
        in_chn = arr_y
        out_chn = arr_x

        ceil_in_chn = int(math.ceil(float(full_in_chn) / in_chn)) * in_chn
        ceil_out_chn = int(math.ceil(float(full_out_chn) / out_chn)) * out_chn

        arr_x = out_chn
        arr_y = in_chn

        ifmap_glb_depth = image_size[0]*image_size[1]* \
                ceil_in_chn//chn_per_word
        psum_glb_depth = image_size[0]*image_size[1]* \
                out_chn//chn_per_word
        weight_glb_depth = filter_size[0]*filter_size[1]* \
                in_chn*out_chn//chn_per_word

        return ifmap_glb_depth, psum_glb_depth, weight_glb_depth

    def instantiate(self, arr_x, arr_y, chn_per_word, done_chn, ifmap_glb_depth, psum_glb_depth, weight_glb_depth):
        self.name = 'conv_tb'

        self.image_size = None
        self.filter_size = None
        self.full_in_chn = None
        self.full_out_chn = None

        self.ceil_in_chn = None
        self.ceil_out_chn = None

        self.in_chn = arr_y
        self.out_chn = arr_x
        self.done_chn = done_chn

        self.chn_per_word = chn_per_word

        self.arr_x = self.out_chn
        self.arr_y = self.in_chn

        self.input_chn = Channel(name='arch_input_chn')
        self.output_chn = Channel(name='arch_output_chn')

        self.stimulus = Stimulus(self.arr_x, self.arr_y, self.chn_per_word,
            self.input_chn, self.output_chn, self.done_chn)
        self.dut = WSArch(self.arr_x, self.arr_y, self.input_chn,
                self.output_chn, self.chn_per_word, ifmap_glb_depth,
                psum_glb_depth, weight_glb_depth)

    def configure(self, image_size, filter_size, full_in_chn, full_out_chn):
        self.image_size = image_size
        self.filter_size = filter_size
        self.full_in_chn = full_in_chn
        self.full_out_chn = full_out_chn

        self.ceil_in_chn = int(math.ceil(float(self.full_in_chn) / self.in_chn)) * self.in_chn
        self.ceil_out_chn = int(math.ceil(float(self.full_out_chn) / self.out_chn)) * self.out_chn

        ifmap, weights, bias = self.stimulus.configure(self.image_size, self.filter_size, self.full_in_chn, self.full_out_chn)
        self.dut.configure(self.image_size, self.filter_size, self.in_chn, self.out_chn, self.ceil_in_chn, self.ceil_out_chn)
        return ifmap, weights, bias

    def configure_fixed_image(self, image, filter_size, full_in_chn, full_out_chn):
        self.image_size = (image.shape[0], image.shape[1])
        self.filter_size = filter_size
        self.full_in_chn = full_in_chn
        self.full_out_chn = full_out_chn

        self.ceil_in_chn = int(math.ceil(float(self.full_in_chn) / self.in_chn)) * self.in_chn
        self.ceil_out_chn = int(math.ceil(float(self.full_out_chn) / self.out_chn)) * self.out_chn

        weights, bias = self.stimulus.configure_fixed_image(image, self.filter_size, self.full_in_chn, self.full_out_chn)
        self.dut.configure(self.image_size, self.filter_size, self.in_chn, self.out_chn, self.ceil_in_chn, self.ceil_out_chn)
        return weights, bias

    def configure_fixed(self, image, filter, bias):
        self.image_size = (image.shape[0], image.shape[1])
        self.filter_size = (filter.shape[0], filter.shape[1])
        self.full_in_chn = filter.shape[2]
        self.full_out_chn = filter.shape[3]

        self.ceil_in_chn = int(math.ceil(float(self.full_in_chn) / self.in_chn)) * self.in_chn
        self.ceil_out_chn = int(math.ceil(float(self.full_out_chn) / self.out_chn)) * self.out_chn

        self.stimulus.configure_fixed(image, filter, bias)
        self.dut.configure(self.image_size, self.filter_size, self.in_chn, self.out_chn, self.ceil_in_chn, self.ceil_out_chn)

    def get_output(self):
        return self.stimulus.deserializer.ofmap
