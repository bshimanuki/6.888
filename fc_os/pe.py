from nnsim.module import Module, HWError
from nnsim.reg import Reg
from nnsim.channel import Channel


class PE(Module):
    def instantiate(self, loc_x, loc_y,
            ifmap_chn, filter_chn,
            bias_chn, out_chn):
        # PE identifier (immutable)
        self.loc_x = loc_x
        self.loc_y = loc_y
        #  self.is_first = self.loc_x == 0 and self.loc_y == 1
        
        self.stat_type = 'aggregate'
        self.raw_stats = {'pe_mac' : 0}

        # IO channels
        self.ifmap_chn = ifmap_chn
        self.filter_chn = filter_chn
        self.bias_chn = bias_chn
        self.out_chn = out_chn

        # PE controller state (set by configure)
        self.fmap_per_iteration = 0
        self.fmap_idx = None

        self.bias = None

    def configure(self, output_iteration):
        self.output_iteration = output_iteration
        self.iteration = 0
        self.accumulator = 0
        self.bias = None
        self.cnt = 0

    def tick(self):
        if self.bias is None:
            if not self.bias_chn.valid():
                return
            self.bias = self.bias_chn.pop()
            self.accumulator = self.bias

        if self.iteration < self.output_iteration and self.ifmap_chn.valid() and self.filter_chn.valid():
            ifmap = self.ifmap_chn.pop()
            weight = self.filter_chn.pop()
            self.accumulator = self.accumulator + ifmap * weight
            self.raw_stats['pe_mac'] += 1
            self.iteration += 1
            #  if self.is_first:
                #  print("PE", ifmap, weight, self.accumulator)
            self.cnt += 1
            #  if self.cnt == 96:
                #  print("PE DONE")
            #  print(self.cnt)
        elif self.iteration < self.output_iteration and self.filter_chn.valid():
            print("waiting on input", self.cnt)

        if self.iteration == self.output_iteration and self.out_chn.vacancy():
            self.out_chn.push(self.accumulator)
            self.iteration = 0
            self.accumulator = self.bias
