from nnsim.module import Module

class WeightsNoC(Module):
    def instantiate(self, rd_chn, wr_chns, arr_x, arr_y):
        self.name = 'weight_noc'
        self.stat_type = 'show'
        self.raw_stats = {'noc_multicast' : 0}

        self.rd_chn = rd_chn
        self.wr_chns = wr_chns

        self.arr_x = arr_x
        self.arr_y = arr_y

    def configure(self):
        pass

    def tick(self):
        # Dispatch filters to PE columns. (PE is responsible for pop)
        if self.rd_chn.valid():
            vacancy = True
            for y in range(self.arr_y):
                for x in range(self.arr_x):
                    vacancy = vacancy and self.wr_chns[y][x].vacancy()
            if vacancy:
                data = self.rd_chn.pop()
                self.raw_stats['noc_multicast'] += len(data)
                # print "filter_to_pe: ", self.curr_filter, data
                for y in range(self.arr_y):
                    for x in range(self.arr_x):
                        self.wr_chns[y][x].push(data[x])

class IFMapNoC(Module):
    def instantiate(self, rd_chn, wr_chns, arr_x, arr_y):
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.name = 'ifmap_noc'

        self.stat_type = 'show'
        self.raw_stats = {'noc_multicast' : 0}

        self.rd_chn = rd_chn
        self.wr_chns = wr_chns

    def configure(self):
        pass

    def tick(self):
        # Feed inputs to the PE array from the GLB
        if self.rd_chn.valid():
            # Dispatch ifmap read if space is available and not at edge
            vacancy = True
            for y in range(self.arr_y):
                for x in range(self.arr_x):
                    vacancy = vacancy and self.wr_chns[y][x].vacancy()

            if vacancy:
                data = self.rd_chn.pop()
                self.raw_stats['noc_multicast'] += len(data)
                # print "ifmap_to_pe", ymin, ymax, data
                for y in range(self.arr_y):
                    for x in range(self.arr_x):
                        self.wr_chns[y][x].push(data[y])
