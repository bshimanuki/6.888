from nnsim.module import Module
from nnsim.channel import Channel
from .os import OSArch
from .stimulus import Stimulus
import math

class OSArchTB(Module):
    def instantiate(self):
        self.name = 'tb'
        self.batch_size = 8
        self.input_size = 8
        self.output_size = 16

        self.chn_per_word = 4

        self.arr_x = 8
        self.arr_y = 4

        self.ceil_batch = int(math.ceil(float(self.batch_size) / self.arr_y)) * self.arr_y
        self.ceil_output = int(math.ceil(float(self.output_size) / self.arr_x)) * self.arr_x

        self.input_chn = Channel()
        self.output_chn = Channel()

        ifmap_glb_depth = self.ceil_batch * self.input_size \
                // self.arr_y
        weight_glb_depth = (self.input_size+1) * self.ceil_output \
                // self.arr_x

        self.stimulus = Stimulus(self.arr_x, self.arr_y, self.chn_per_word,
            self.input_chn, self.output_chn)
        self.dut = OSArch(self.arr_x, self.arr_y, self.input_chn,
                self.output_chn, self.chn_per_word, ifmap_glb_depth,
                weight_glb_depth)

        self.configuration_done = False

    def tick(self):
        if not self.configuration_done:
            self.stimulus.configure(self.batch_size, self.input_size, self.output_size)
            self.dut.configure(self.ceil_batch, self.input_size, self.ceil_output)
            self.configuration_done = True


if __name__ == "__main__":
    from nnsim.simulator import run_tb
    os_tb = OSArchTB()
    run_tb(os_tb, verbose=False)
