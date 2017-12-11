from nnsim.module import Module
from nnsim.ram import SRAM, RD, WR
from nnsim.channel import Channel

class IFMapGLB(Module):
    def instantiate(self, wr_chn, rd_chn, glb_depth, chn_per_word):
        self.wr_chn = wr_chn
        self.rd_chn = rd_chn
        self.chn_per_word = chn_per_word
        self.name = 'ifmap_glb'

        self.stat_type = 'show'
        self.raw_stats = {'size' : (glb_depth, chn_per_word), 'rd': 0, 'wr': 0}


        self.sram = SRAM(glb_depth, chn_per_word, name=self.name)
        self.last_read = Channel(3, name='last_read')

        self.image_size = (0, 0)
        self.filter_size = (0, 0)
        self.fmap_sets = 0
        self.full_fmap_sets = 0
        self.fmap_per_iteration = 0

        self.curr_set = 0
        self.fmap_idx = 0
        self.iteration = 0
        self.tile_in = 0
        self.tile_out = 0
        self.wr_done = False
        self.task_done = True

    def configure(self, image_size, filter_size, fmap_sets, full_fmap_sets, tiles_out, fmap_per_iteration):
        self.wr_done = False
        self.curr_set = 0
        self.fmap_idx = 0
        self.iteration = 0

        self.image_size = image_size
        self.filter_size = filter_size
        self.fmap_sets = fmap_sets
        self.full_fmap_sets = full_fmap_sets
        self.fmap_per_iteration = fmap_per_iteration
        self.tiles_out = tiles_out
        self.tile_in = 0
        self.tile_out = 0
        self.task_done = False

    def tick(self):
        num_iteration = self.filter_size[0]*self.filter_size[1]
        offset_x = (self.filter_size[0] - 1)//2
        offset_y = (self.filter_size[1] - 1)//2
        filter_x = self.iteration % self.filter_size[0] - offset_x
        filter_y = self.iteration // self.filter_size[0] - offset_y
        tiles_in = self.full_fmap_sets // self.fmap_sets

        if self.task_done:
            return

        if not self.wr_done:
            # Write to GLB
            if self.wr_chn.valid():
                data = self.wr_chn.pop()
                # print "ifmap_glb wr"
                # Write ifmap to glb
                # print "ifmap_to_glb: ", in_sets, self.fmap_idx, self.curr_set
                addr = self.full_fmap_sets*self.fmap_idx + self.curr_set
                self.curr_set += 1
                self.sram.request(WR, addr, data)
                self.raw_stats['wr'] += len(data)
                if self.curr_set == self.full_fmap_sets:
                    self.curr_set = 0
                    self.fmap_idx += 1
                if self.fmap_idx == self.fmap_per_iteration:
                    # Done initializing ifmaps and psums
                    # self.sram.dump()
                    self.fmap_idx = 0
                    self.wr_done = True
        else:
            did_read = False
            # Read from GLB and deal with SRAM latency
            if self.rd_chn.vacancy(1) and self.iteration < num_iteration and self.tile_in < tiles_in:
                fmap_x = self.fmap_idx % self.image_size[0]
                fmap_y = self.fmap_idx  // self.image_size[0]
                ifmap_x, ifmap_y = (fmap_x + filter_x, fmap_y + filter_y)
                if (ifmap_x < 0) or (ifmap_x >= self.image_size[0]) or \
                        (ifmap_y < 0) or (ifmap_y >= self.image_size[1]):
                    # print "ifmap req zero", self.iteration, self.fmap_idx
                    self.last_read.push(True)
                else:
                    fmap_idx = (ifmap_y*self.image_size[0]) + ifmap_x
                    addr = self.fmap_sets*(fmap_idx*tiles_in+self.tile_in) + self.curr_set
                    # print "ifmap req glb", self.iteration, self.fmap_idx
                    self.sram.request(RD, addr)
                    self.raw_stats['rd'] += self.chn_per_word
                    self.last_read.push(False)
                did_read = True
                self.curr_set += 1

                if self.curr_set == self.fmap_sets:
                    self.curr_set = 0
                    self.fmap_idx += 1
                if self.fmap_idx == self.fmap_per_iteration:
                    self.fmap_idx = 0
                    self.iteration += 1

            # Process the last read sent to the GLB SRAM
            if self.last_read.valid():
                is_zero = self.last_read.pop()
                data = [0]*self.chn_per_word if is_zero else \
                        [e for e in self.sram.response()]
                # print "ifmap rd glb", data
                self.rd_chn.push(data)
            elif not did_read:
                if self.iteration == num_iteration:
                    self.iteration = 0
                    self.tile_in += 1
                    if self.tile_in == tiles_in:
                        self.tile_in = 0
                        self.tile_out += 1
                        if self.tile_out == self.tiles_out:
                            self.tile_out = 0
                            self.task_done = True

class PSumGLB(Module):
    def instantiate(self, dram_wr_chn, noc_wr_chn, rd_chn, glb_depth, chn_per_word):
        self.dram_wr_chn = dram_wr_chn
        self.noc_wr_chn = noc_wr_chn
        self.rd_chn = rd_chn
        self.chn_per_word = chn_per_word
        self.name = 'psum_glb'

        self.stat_type = 'show'
        self.raw_stats = {'size' : (glb_depth, chn_per_word), 'rd': 0, 'wr': 0}

        self.sram = SRAM(glb_depth, chn_per_word, nports=2, name=self.name)
        self.last_read = Channel(3, name='last_read')

        self.filter_size = (0, 0)
        self.fmap_sets = 0
        self.fmap_per_iteration = 0

        self.rd_set = 0
        self.fmap_rd_idx = 0
        self.iteration = 0

        self.wr_set = 0
        self.fmap_wr_idx = 0
        self.wr_iteration = 1
        self.wr_done = False

    def configure(self, filter_size, fmap_sets, fmap_per_iteration):
        self.wr_done = False

        self.filter_size = filter_size
        self.fmap_sets = fmap_sets
        self.fmap_per_iteration = fmap_per_iteration

        self.rd_set = 0
        self.fmap_rd_idx = 0
        self.iteration = 0

        self.wr_set = 0
        self.fmap_wr_idx = 0
        self.wr_iteration = 1
        self.wr_done = False

    def tick(self):
        num_iteration = self.filter_size[0]*self.filter_size[1]

        if not self.wr_done:
            # Write to GLB
            if self.dram_wr_chn.valid():
                data = self.dram_wr_chn.pop()
                # print "psum_glb wr"
                # Write ifmap to glb
                # print "ifmap_to_glb: ", in_sets, self.fmap_idx, self.curr_set
                addr = self.fmap_sets*self.fmap_wr_idx + self.wr_set
                self.wr_set += 1
                self.sram.request(WR, addr, data, port=0)
                self.raw_stats['wr'] += len(data)
                if self.wr_set == self.fmap_sets:
                    self.wr_set = 0
                    self.fmap_wr_idx += 1
                if self.fmap_wr_idx == self.fmap_per_iteration:
                    # Done initializing ifmaps and psums
                    # self.sram.dump()
                    self.fmap_wr_idx = 0
                    self.wr_done = True
        else:
            # Read from GLB and deal with SRAM latency
            # print self.rd_chn.vacancy(1), self.rd_chn.rd_ptr.rd(), self.rd_chn.wr_ptr.rd()
            did_read = False
            for _ in range(1):
                if self.rd_chn.vacancy(1) and self.iteration < num_iteration:
                    addr = self.fmap_sets*self.fmap_rd_idx + self.rd_set
                    wr_addr = self.fmap_sets*self.fmap_wr_idx + self.wr_set
                    if self.wr_iteration < num_iteration and self.iteration == self.wr_iteration and addr == wr_addr:
                        break
                    # print "psum req glb", self.iteration, self.fmap_rd_idx, self.rd_set
                    self.sram.request(RD, addr, port=0)
                    self.raw_stats['rd'] += self.chn_per_word
                    self.last_read.push(False)
                    did_read = True
                    self.rd_set += 1

                    if self.rd_set == self.fmap_sets:
                        self.rd_set = 0
                        self.fmap_rd_idx += 1
                    if self.fmap_rd_idx == self.fmap_per_iteration:
                        self.fmap_rd_idx = 0
                        self.iteration += 1

            # Process the last read sent to the GLB SRAM
            if self.last_read.valid():
                is_zero = self.last_read.pop()
                data = [0]*self.chn_per_word if is_zero else \
                        [e for e in self.sram.response()]
                self.rd_chn.push(data)
                # print "psum rd glb", data
            elif not did_read:
                if self.iteration == num_iteration and self.wr_iteration == num_iteration:
                    self.iteration = 0
                    self.wr_iteration = 1
                    self.wr_done = False

            if self.noc_wr_chn.valid():
                # print "psum_to_glb: ", self.fmap_wr_idx, self.wr_set
                data = self.noc_wr_chn.pop()
                addr = self.fmap_sets*self.fmap_wr_idx + self.wr_set
                # print "psum wr glb", self.fmap_wr_idx, self.wr_set, data
                self.wr_set += 1
                self.sram.request(WR, addr, data, port=1)
                self.raw_stats['wr'] += len(data)
                if self.wr_set == self.fmap_sets:
                    self.wr_set = 0
                    self.fmap_wr_idx += 1
                if self.fmap_wr_idx == self.fmap_per_iteration:
                    # Done initializing ifmaps and psums
                    # self.sram.dump()
                    self.fmap_wr_idx = 0
                    self.wr_iteration += 1

class WeightsGLB(Module):
    def instantiate(self, wr_chn, rd_chn, glb_depth, chn_per_word):
        self.wr_chn = wr_chn
        self.rd_chn = rd_chn
        self.chn_per_word = chn_per_word
        self.name = 'weight_glb'

        self.stat_type = 'show'
        self.raw_stats = {'size' : (glb_depth, chn_per_word), 'rd': 0, 'wr': 0}

        self.sram = SRAM(glb_depth, chn_per_word, name=self.name)
        self.last_read = Channel(3, name='last_read')

        self.filter_size = (0, 0)
        self.in_sets = 0
        self.out_sets = 0

        self.curr_set = 0
        self.fmap_idx = 0
        self.iteration = 0
        self.tile = 0
        self.wr_done = False

    def configure(self, filter_size, in_sets, out_sets):
        self.wr_done = False

        self.filter_size = filter_size
        self.in_sets = in_sets
        self.out_sets = out_sets
        self.tile = 0
        self.stuff = []

    def tick(self):
        num_iteration = self.filter_size[0]*self.filter_size[1]

        if not self.wr_done:
            # Write to GLB
            if self.wr_chn.valid():
                data = self.wr_chn.pop()
                # print "ifmap_glb wr"
                # Write ifmap to glb
                # print "ifmap_to_glb: ", in_sets, self.fmap_idx, self.curr_set
                addr = self.in_sets*(self.out_sets*self.iteration+self.fmap_idx) + self.curr_set
                self.stuff.append(data)
                self.curr_set += 1
                self.sram.request(WR, addr, data)
                self.raw_stats['wr'] += len(data)
                if self.curr_set == self.in_sets:
                    self.curr_set = 0
                    self.fmap_idx += 1
                if self.fmap_idx == self.out_sets:
                    # Done initializing ifmaps and psums
                    # self.sram.dump()
                    self.fmap_idx = 0
                    self.iteration += 1
                    if self.iteration == num_iteration:
                        self.iteration = 0
                        self.wr_done = True
        else:
            did_read = False
            # Read from GLB and deal with SRAM latency
            if self.rd_chn.vacancy(1) and self.iteration < num_iteration:
                addr = self.in_sets*(self.out_sets*self.iteration+self.fmap_idx) + self.curr_set
                # print "ifmap req glb", self.iteration, self.fmap_idx
                self.sram.request(RD, addr)
                self.raw_stats['rd'] += self.chn_per_word
                self.last_read.push(False)
                did_read = True
                self.curr_set += 1

                if self.curr_set == self.in_sets:
                    self.curr_set = 0
                    self.fmap_idx += 1
                if self.fmap_idx == self.out_sets:
                    self.fmap_idx = 0
                    self.iteration += 1

            # Process the last read sent to the GLB SRAM
            if self.last_read.valid():
                is_zero = self.last_read.pop()
                data = [0]*self.chn_per_word if is_zero else \
                        [e for e in self.sram.response()]
                # print "ifmap rd glb", data
                self.rd_chn.push(data)
            elif not did_read:
                if self.iteration == num_iteration:
                    self.iteration = 0
                    self.wr_done = False
