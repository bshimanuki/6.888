from nnsim.module import Module
from nnsim.ram import SRAM, RD, WR
from nnsim.reg import Reg
from nnsim.channel import Channel

class GLB(Module):
    def instantiate(self, wr_chn, rd_chn, glb_depth, width, chn_per_word, name):
        self.wr_chn = wr_chn
        self.rd_chn = rd_chn
        self.chn_per_word = chn_per_word
        self.width = width
        self.name = name

        self.stat_type = 'show'
        self.raw_stats = {'size' : (glb_depth, width), 'rd': 0, 'wr': 0}

        self.sram = SRAM(glb_depth, width, nports=2, name='fc_glb')
        self.last_read = Channel(3, name='last_read')

        self.curr_data = Reg([])
        self.wr_done = False
        self.pass_done = False

        self.size = None
        self.passes = None

        self.curr_i = 0
        self.curr_pass = 0

    def configure(self, size, passes, batch_size):
        self.wr_done = False
        self.pass_done = False
        self.curr_data.reset()

        self.size = size
        self.passes = passes
        self.batch_size = batch_size

        self.curr_i = 0
        self.curr_b = 0
        self.curr_pass = 0

    def tick(self):
        if not self.wr_done:
            # Write to GLB
            if self.wr_chn.valid():
                data = self.wr_chn.pop()
                curr_data = self.curr_data.rd()
                curr_data = curr_data + data
                if len(curr_data) == self.width:
                    self.raw_stats['wr'] += len(curr_data)
                    # print "ifmap_glb wr"
                    addr = self.curr_i
                    self.curr_i += 1
                    self.sram.request(WR, addr, curr_data)
                    self.curr_data.wr([])
                    if self.curr_i == self.size:
                        self.curr_i = 0
                        # Done initializing ifmaps and psums
                        # self.sram.dump()
                        self.wr_done = True
                else:
                    self.curr_data.wr(curr_data)
        else:
            # Read from GLB and deal with SRAM latency
            if self.rd_chn.vacancy(1) and not self.pass_done:
                addr = self.curr_b * self.size // self.batch_size + self.curr_i
                self.sram.request(RD, addr)
                self.last_read.push(True)

                self.curr_i += 1
                if self.curr_i == self.size * self.width // self.batch_size:
                    self.curr_i = 0
                    self.curr_pass += 1
                    if self.curr_pass == self.passes:
                        self.curr_pass = 0
                        self.curr_b += self.width
                        if self.curr_b >= self.batch_size:
                            self.curr_b = 0
                            self.pass_done = True

            if self.last_read.valid():
                self.last_read.pop()
                data = self.sram.response()
                self.raw_stats['rd'] += len(data)
                push_data = [e for e in data]
                self.rd_chn.push(push_data)
