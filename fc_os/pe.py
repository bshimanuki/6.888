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
        #  self.is_first = self.loc_x == 0 and self.loc_y == 1
        
        self.stat_type = 'aggregate'
        self.raw_stats = {'pe_mac' : 0}

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
            self.raw_stats['pe_mac'] += 1
            #  if self.is_first:
                #  print("PE", ifmap, weight, self.accumulator)
            self.cnt += 1
            #  if self.cnt == 96:
                #  print("PE DONE")
            #  print(self.cnt)

        if self.cnt == self.input_size + 1 and self.out_chn.vacancy():
            self.out_chn.push(self.accumulator)
            self.cnt = 0
