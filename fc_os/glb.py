from nnsim.module import Module
from nnsim.ram import SRAM, RD, WR
from nnsim.channel import Channel

class IFMapGLB(Module):
    def instantiate(self, wr_chn, rd_chn, glb_depth, chn_per_word, in_chn):
        self.wr_chn = wr_chn
        self.rd_chn = rd_chn
        self.chn_per_word = chn_per_word
        self.name = 'ifmap_glb'

        self.stat_type = 'show'
        self.raw_stats = {'size' : (glb_depth, chn_per_word), 'rd': 0, 'wr': 0}


        self.sram = SRAM(glb_depth, chn_per_word, nports=2)
        self.last_read = Channel(3)

        self.image_size = (0, 0)
        self.filter_size = (0, 0)
        self.fmap_sets = 0
        self.fmap_per_iteration = 0

        self.num_in_chn = in_chn

        self.curr_set = 0
        self.fmap_idx = 0
        self.iteration = 0
        self.cur_x = 0
        self.wr_done = False

    def configure(self, image_size, filter_size, fmap_sets, fmap_per_iteration):
        self.wr_done = False

        self.image_size = image_size
        self.filter_size = filter_size
        self.fmap_sets = fmap_sets
        self.fmap_per_iteration = fmap_per_iteration
        self.cur_x = 0
        self.cur_in_chn = 0
        self.cnt = 0

    def tick(self):
        num_iteration = self.filter_size[0]*self.filter_size[1]
        offset_x = (self.filter_size[0] - 1)//2
        filter_x = self.iteration % self.filter_size[0] - offset_x
        chn_jump = self.image_size[0] // self.chn_per_word
        max_cur_x = self.image_size[0] // self.chn_per_word


        if not self.wr_done:
            # Write to GLB
            if self.wr_chn.valid():
                data = self.wr_chn.pop()
                self.raw_stats['wr'] += len(data)
                # print "ifmap_glb wr"
                # Write ifmap to glb
                # print "ifmap_to_glb: ", in_sets, self.fmap_idx, self.curr_set
                addr = self.fmap_sets*self.fmap_idx + self.curr_set
                self.curr_set += 1
                self.sram.request(WR, addr, data)
                #  print(addr, data)
                if self.curr_set == self.fmap_sets:
                    self.curr_set = 0
                    self.fmap_idx += 1
                if self.fmap_idx == self.fmap_per_iteration:
                    # Done initializing ifmaps and psums
                    # self.sram.dump()
                    self.fmap_idx = 0
                    self.wr_done = True
        else:
            # Read from GLB and deal with SRAM latency
            if self.rd_chn.vacancy(1) and self.cur_x < max_cur_x:
                fmap_x = (self.cur_x * self.chn_per_word) % self.image_size[0]

                ifmap_x_start = fmap_x + filter_x
                ifmap_x_end = ifmap_x_start + self.chn_per_word

                addr = self.cur_x + chn_jump * self.cur_in_chn

                self.sram.request(RD, addr)

                if ifmap_x_start < 0:
                    pass
                elif filter_x < 0:
                    self.sram.request(RD, addr - 1, port=1)
                elif ifmap_x_end > self.image_size[0]:
                    pass
                elif filter_x > 0:
                    self.sram.request(RD, addr + 1, port=1)
                    pass
                else:
                    pass
                self.last_read.push((filter_x, ifmap_x_start, ifmap_x_end, addr))
                #  print(addr, data, push_data)
                self.iteration += 1

                if self.iteration == num_iteration:
                    self.iteration = 0
                    self.cur_in_chn += 1
                if self.cur_in_chn == self.num_in_chn:
                    self.cur_in_chn = 0
                    self.cur_x += 1
                    #  if self.cur_x == max_cur_x:
                        #  print("DONE")

            if self.last_read.valid():
                filter_x, ifmap_x_start, ifmap_x_end, addr = self.last_read.pop()
                data = self.sram.response()
                self.raw_stats['rd'] += len(data)
                if ifmap_x_start < 0:
                    push_data = [0] * (-ifmap_x_start) + [e for e in data[:ifmap_x_start]]
                elif filter_x < 0:
                    old_data = self.sram.response(port=1)
                    self.raw_stats['rd'] += len(old_data)
                    push_data = [e for e in old_data[filter_x:]] + [e for e in data[:filter_x]]
                elif ifmap_x_end > self.image_size[0]:
                    diff = ifmap_x_end - self.image_size[0]
                    push_data = [e for e in data[diff:]] + [0 for i in range(diff)]
                elif filter_x > 0:
                    new_data = self.sram.response(port=1)
                    self.raw_stats['rd'] += len(new_data)
                    push_data = [e for e in data[filter_x:]] + [new_data[i] for i in range(filter_x)]
                else:
                    push_data = [e for e in data]
                #  print("IF", push_data, data, addr)
                self.rd_chn.push(push_data)
                #  print("IF", self.cnt)
                self.cnt += 1


class WeightsGLB(Module):
    def instantiate(self, wr_chn, rd_chn, glb_depth, chn_per_word):
        self.wr_chn = wr_chn
        self.rd_chn = rd_chn
        self.name = 'weight_glb'

        self.chn_per_word = chn_per_word
        self.sram = SRAM(glb_depth, chn_per_word)

        self.stat_type = 'show'
        self.raw_stats = {'size' : (glb_depth, chn_per_word), 'rd': 0, 'wr': 0}

        self.last_read = Channel(3)

    def configure(self, num_iteration, filter_size):
        self.num_iteration = num_iteration
        self.iteration = 0
        self.addr = 0
        self.filter_size = filter_size
        self.rd_data = []
        self.rd_done = False
        self.cnt = 0

    def tick(self):
        if not self.rd_done:
            if self.wr_chn.valid():
                self.rd_data = self.rd_data + self.wr_chn.pop()
                if len(self.rd_data) == self.chn_per_word:
                    self.sram.request(WR, self.addr, self.rd_data)
                    self.raw_stats['wr'] += len(self.rd_data)
                    #  print(self.addr, self.rd_data)
                    self.rd_data = []
                    self.addr += 1
                    if self.addr == self.filter_size:
                        self.rd_done = True
                        self.addr = 0
        elif self.iteration < self.num_iteration and self.rd_chn.vacancy():
            self.sram.request(RD, self.addr)
            self.last_read.push(self.addr)
            self.addr += 1
            if self.addr == self.filter_size:
                self.addr = 0
                #  print(self.iteration)
                self.iteration += 1

        if self.last_read.valid():
            addr = self.last_read.pop()
            data = [e for e in self.sram.response()]
            self.raw_stats['rd'] += len(data)
            self.rd_chn.push([e for e in self.sram.response()])
            self.cnt += 1
