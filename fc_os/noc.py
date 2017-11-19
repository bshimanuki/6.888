from nnsim.module import Module

class WeightsNoC(Module):
    def instantiate(self, rd_chn, wr_chns, chn_per_word):
        self.chn_per_word = chn_per_word
        self.name = 'weight_noc'

        self.stat_type = 'show'
        self.raw_stats = {'noc_multicast' : 0}

        self.rd_chn = rd_chn
        self.wr_chns = wr_chns

    def configure(self, arr_x, arr_y):
        self.arr_x = arr_x
        self.arr_y = arr_y

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
    def instantiate(self, rd_chn, wr_chns, arr_x, chn_per_word):
        self.arr_x = arr_x
        self.chn_per_word = chn_per_word
        self.name = 'ifmap_noc'

        self.stat_type = 'show'
        self.raw_stats = {'noc_multicast' : 0}

        self.rd_chn = rd_chn
        self.wr_chns = wr_chns

        self.ifmap_sets = 0

        self.curr_set = 0
        self.curr_filter = 0

    def configure(self, ifmap_sets):
        self.ifmap_sets = ifmap_sets

        self.curr_set = 0
        self.curr_filter = 0

    def tick(self):
        # Feed inputs to the PE array from the GLB
        if self.rd_chn.valid():
            # Dispatch ifmap read if space is available and not at edge
            ymin = self.curr_set*self.chn_per_word
            ymax = ymin + self.chn_per_word
            vacancy = True
            for y in range(ymin, ymax):
                for x in range(self.arr_x):
                    vacancy = vacancy and self.wr_chns[y][x].vacancy()

            if vacancy:
                data = self.rd_chn.pop()
                self.raw_stats['noc_multicast'] += len(data)
                # print "ifmap_to_pe", ymin, ymax, data
                for y in range(ymin, ymax):
                    for x in range(self.arr_x):
                        self.wr_chns[y][x].push(data[y-ymin])

                self.curr_set += 1
                if self.curr_set == self.ifmap_sets:
                    self.curr_set = 0

# only used to do the writes at the very beginning
class BiasNoC(Module):
    def instantiate(self, rd_chn, wr_chns, arr_x, arr_y):
        self.name = 'bias_noc'

        self.rd_chn = rd_chn
        self.wr_chns = wr_chns

        self.arr_x = arr_x
        self.arr_y = arr_y

    def configure(self):
        self.cur_biases = []
        self.done = False

    def tick(self):
        if self.done:
            return
        if self.rd_chn.valid():
            self.cur_biases = self.cur_biases + self.rd_chn.pop()
        if len(self.cur_biases) == self.arr_x:
            vacancy = True
            for i in range(self.arr_y):
                for j in range(self.arr_x):
                    vacancy = vacancy and self.wr_chns[i][j].vacancy()
            if vacancy:
                for i in range(self.arr_y):
                    for j in range(self.arr_x):
                        self.wr_chns[i][j].push(self.cur_biases[j])
                self.done = True
