from nnsim.module import Module, HWError
from nnsim.reg import Reg
from nnsim.channel import Channel


class PE(Module):
    def instantiate(self, loc_x, loc_y,
            ifmap_chn, weight_chn,
            out_chn):
        # PE identifier (immutable)
        self.loc_x = loc_x
        self.loc_y = loc_y
        #  self.is_first = self.loc_x == 0 and self.loc_y == 0

        self.stat_type = 'aggregate'
        self.raw_stats = {'pe_nz_mac' : 0, 'pe_z_mac': 0}

        # IO channels
        self.ifmap_chn = ifmap_chn
        self.weight_chn = weight_chn
        self.out_chn = out_chn

        # PE controller state (set by configure)
        self.input_size = None
        self.accumulator = 0
        self.cnt = 0

    def configure(self, input_size):
        self.input_size = input_size
        self.accumulator = 0
        self.cnt = 0

    def tick(self):
        if self.cnt == 0:
            if self.weight_chn.valid():
                self.accumulator = self.weight_chn.pop()
                self.cnt += 1
            return

        if self.ifmap_chn.valid() and self.weight_chn.valid() and self.cnt <= self.input_size:
            ifmap = self.ifmap_chn.pop()
            weight = self.weight_chn.pop()
            self.accumulator = self.accumulator + ifmap * weight
            if ifmap == 0 or weight == 0:
                self.raw_stats['pe_z_mac'] += 1
                # self.output_file.write('pe pe_{}_{} fire\n'.format(self.loc_x, self.loc_y));
            else:
                self.raw_stats['pe_nz_mac'] += 1
            self.output_file.write('pe pe_{}_{} fire\n'.format(self.loc_x, self.loc_y));
            self.cnt += 1

        if self.cnt == self.input_size + 1 and self.out_chn.vacancy():
            self.out_chn.push(self.accumulator)
            self.cnt = 0
