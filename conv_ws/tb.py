from nnsim.module import Module
from nnsim.channel import Channel
from .ws import WSArch
from .stimulus import Stimulus

class WSArchTB(Module):
    def instantiate(self):
        self.name = 'tb'
        self.image_size = (4, 4)
        self.filter_size = (3, 3)
        self.full_in_chn = 8
        self.full_out_chn = 16
        self.in_chn = 4
        self.out_chn = 8
        self.chn_per_word = 4

        self.arr_x = self.out_chn
        self.arr_y = self.in_chn

        self.input_chn = Channel()
        self.output_chn = Channel()

        ifmap_glb_depth = self.image_size[0]*self.image_size[1]* \
                self.full_in_chn//self.chn_per_word
        psum_glb_depth = self.image_size[0]*self.image_size[1]* \
                self.out_chn//self.chn_per_word
        weights_glb_depth = self.filter_size[0]*self.filter_size[1]* \
                self.in_chn*self.out_chn//self.chn_per_word

        self.stimulus = Stimulus(self.arr_x, self.arr_y, self.chn_per_word,
            self.input_chn, self.output_chn)
        self.dut = WSArch(self.arr_x, self.arr_y, self.input_chn,
                self.output_chn, self.chn_per_word, ifmap_glb_depth,
                psum_glb_depth, weights_glb_depth)

        self.configuration_done = False

    def tick(self):
        if not self.configuration_done:
            self.stimulus.configure(self.image_size, self.filter_size, self.full_in_chn, self.full_out_chn)
            self.dut.configure(self.image_size, self.filter_size, self.in_chn, self.out_chn, self.full_in_chn, self.full_out_chn)
            self.configuration_done = True
