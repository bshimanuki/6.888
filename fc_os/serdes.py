from nnsim.module import Module
from nnsim.reg import Reg
from nnsim.simulator import Finish

import numpy as np

class InputSerializer(Module):
    def instantiate(self, arch_input_chn, arr_x, arr_y, chn_per_word):
        # PE static configuration (immutable)
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word

        self.arch_input_chn = arch_input_chn

        self.ifmap = None
        self.weights = None
        self.bias = None

        self.ifmap_done = True
        self.bias_done = True
        self.pass_done = True

        # State Counters
        self.curr_set = 0
        self.bset = 0
        self.wset = 0
        self.curr_i = 0
        self.curr_o = 0
        self.curr_batch = 0

    def configure(self, ifmap, weights, bias):
        self.ifmap = ifmap
        self.weights = weights
        self.bias = bias

        self.batch_size = ifmap.shape[0]
        self.input_size = ifmap.shape[1]
        self.output_size = bias.shape[0]

        self.ifmap_done = False
        self.bias_done = False
        self.pass_done = False

        # State Counters
        self.curr_set = 0
        self.bset = 0
        self.wset = 0
        self.curr_i = 0
        self.curr_o = 0
        self.curr_batch = 0

    def tick(self):
        if not self.ifmap_done:
            if self.arch_input_chn.vacancy():
                bmin = self.curr_batch + self.bset * self.chn_per_word
                bmax = bmin + self.chn_per_word
                if bmax > self.batch_size:
                    num_zeros = bmax - self.batch_size
                    if num_zeros > bmax - bmin:
                        data = [0] * (bmax - bmin)
                    else:
                        bmax = self.batch_size
                        data = np.array([ self.ifmap[b, self.curr_set] for b in range(bmin, bmax) ] + [0] * num_zeros)
                else:
                    data = np.array([self.ifmap[b, self.curr_set] for b in range(bmin, bmax)])
                self.arch_input_chn.push(data)

                self.bset += 1
                if self.bset == self.arr_y // self.chn_per_word:
                    self.bset = 0
                    self.curr_set += 1
                    if self.curr_set == self.input_size:
                        self.curr_set = 0
                        self.curr_batch += self.arr_y
                        if self.curr_batch >= self.batch_size:
                            self.curr_batch = 0
                            self.ifmap_done = True
        elif not self.pass_done:
            if self.arch_input_chn.vacancy():
                omin = self.curr_o + self.wset * self.chn_per_word
                omax = omin + self.chn_per_word
                if self.curr_i == 0:
                    if omax > self.output_size:
                        num_zeros = omax - self.output_size
                        if num_zeros > omax - omin:
                            data = [0] * (omax - omin)
                        else:
                            omax = self.output_size
                            data = np.array([ self.bias[o] for o in range(omin, omax) ] + [0] * num_zeros)
                    else:
                        data = np.array([self.bias[o] for o in range(omin, omax)])
                else:
                    curr_i = self.curr_i - 1
                    if omax > self.output_size:
                        num_zeros = omax - self.output_size
                        if num_zeros > omax - omin:
                            data = [0] * (omax - omin)
                        else:
                            omax = self.output_size
                            data = np.array([self.weights[curr_i, o] for o in range(omin, omax)] + [0] * num_zeros)
                    else:
                        data = np.array([self.weights[curr_i, o] for o in range(omin, omax)])
                self.arch_input_chn.push(data)

                self.wset += 1
                if self.wset == self.arr_x // self.chn_per_word:
                    self.wset = 0
                    self.curr_i += 1
                    if self.curr_i == self.input_size + 1:
                        self.curr_i = 0
                        self.curr_o += self.arr_x
                        if self.curr_o >= self.output_size:
                            self.curr_o = 0
                            self.pass_done = True


class InputDeserializer(Module):
    def instantiate(self, arch_input_chn, ifmap_chn, weights_chn, bias_chn,
            arr_x, arr_y, chn_per_word):
        self.chn_per_word = chn_per_word
        self.arr_x = arr_x
        self.arr_y = arr_y

        self.stat_type = 'aggregate'
        self.raw_stats = {'dram_rd' : 0}

        self.arch_input_chn = arch_input_chn
        self.ifmap_chn = ifmap_chn
        self.weights_chn = weights_chn
        self.bias_chn = bias_chn

        self.ifmap_done = False
        self.bias_done = False
        self.pass_done = False

        self.input_size = None
        self.output_size = None
        self.batch_size = None

        # State Counters
        self.curr_set = 0
        self.bset = 0
        self.wset = 0
        self.curr_i = 0
        self.curr_o = 0
        self.curr_batch = 0


    def configure(self, batch_size, input_size, output_size):
        self.input_size = input_size
        self.output_size = output_size
        self.batch_size = batch_size

        self.ifmap_done = False
        self.bias_done = False
        self.pass_done = False

        # State Counters
        self.curr_set = 0
        self.bset = 0
        self.wset = 0
        self.curr_i = 0
        self.curr_o = 0
        self.curr_batch = 0

    def tick(self):
        if not self.ifmap_done:
            target_chn = self.ifmap_chn
            target_str = 'ifmap'
        else:
            target_chn = self.weights_chn
            target_str = 'weights'

        if self.arch_input_chn.valid():
            if target_chn.vacancy():
                #  print ("des to ", target_str)
                data = [e for e in self.arch_input_chn.pop()]
                self.raw_stats['dram_rd'] += len(data)
                target_chn.push(data)

                if not self.ifmap_done:
                    if self.arch_input_chn.vacancy():
                        self.bset += 1
                        if self.bset == self.arr_y // self.chn_per_word:
                            self.bset = 0
                            self.curr_set += 1
                            if self.curr_set == self.input_size:
                                self.curr_set = 0
                                self.curr_batch += self.arr_y
                                if self.curr_batch >= self.batch_size:
                                    self.curr_batch = 0
                                    self.ifmap_done = True
                elif not self.pass_done:
                    if self.arch_input_chn.vacancy():
                        self.wset += 1
                        if self.wset == self.arr_x // self.chn_per_word:
                            self.wset = 0
                            self.curr_i += 1
                            if self.curr_i == self.input_size + 1:
                                self.curr_i = 0
                                self.curr_o += self.arr_x
                                if self.curr_o >= self.output_size:
                                    self.curr_o = 0
                                    self.pass_done = True

class OutputSerializer(Module):
    def instantiate(self, arch_output_chn, pe_out_chn, arr_x, arr_y, chn_per_word):
        self.arch_output_chn = arch_output_chn
        self.pe_out_chn = pe_out_chn

        self.stat_type = 'aggregate'
        self.raw_stats = {'dram_wr' : 0}

        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word

        self.input_size = None
        self.output_size = None
        self.batch_size = None

        # State Counters
        self.curr_x = 0
        self.curr_y = 0

    def configure(self, input_size, output_size, batch_size):
        self.input_size = input_size
        self.output_size = output_size
        self.batch_size = batch_size

        # State Counters
        self.curr_x = 0
        self.curr_y = 0

    def tick(self):
        valid = True

        start = self.curr_y * self.chn_per_word
        end = start + self.chn_per_word
        for i in range(start, end):
            valid = valid and self.pe_out_chn[i][self.curr_x].valid()

        if valid and self.arch_output_chn.vacancy():
            data = [self.pe_out_chn[i][self.curr_x].pop() for i in range(start, end)]
            #  print(data)
            self.arch_output_chn.push(data)
            self.raw_stats['dram_wr'] += len(data)

            self.curr_y += self.chn_per_word
            if self.curr_y == self.arr_y:
                self.curr_y = 0
                self.curr_x += 1
                if self.curr_x == self.arr_x:
                    self.curr_x = 0

class OutputDeserializer(Module):
    def instantiate(self, arch_output_chn, done_chn, arr_x, arr_y, chn_per_word):
        # PE static configuration (immutable)
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word

        self.arch_output_chn = arch_output_chn
        self.done_chn = done_chn

        self.ofmap = None
        self.reference = None

        self.batch_size = None
        self.output_size = None

        self.curr_set = 0
        self.curr_batch = 0
        self.curr_o = 0

        self.pass_done = True

    def configure(self, ofmap, reference):
        self.ofmap = ofmap
        self.reference = reference

        self.batch_size = ofmap.shape[0]
        self.output_size = ofmap.shape[1]

        self.curr_set = 0
        self.curr_batch = 0
        self.curr_o = 0

        self.pass_done = False

    def tick(self):
        if self.pass_done:
            return

        if self.arch_output_chn.valid():
            #  print(self.fmap_idx, self.curr_set)
            data = [e for e in self.arch_output_chn.pop()]

            ymin = self.curr_batch + self.curr_set * self.chn_per_word
            ymax = min(self.curr_batch + self.chn_per_word, self.batch_size)
            for y in range(ymin, ymax):
                if self.curr_o < self.output_size:
                    self.ofmap[y, self.curr_o] = data[y-ymin]

            self.curr_set += 1
            if self.curr_set == self.arr_y // self.chn_per_word:
                self.curr_set = 0
                self.curr_o += 1
                if self.curr_o >= self.output_size:
                    self.curr_o = 0
                    self.curr_batch += self.arr_y
                    if self.curr_batch >= self.batch_size:
                        self.curr_batch = 0

                        self.pass_done = True
                        if np.all(self.ofmap == self.reference):
                            self.done_chn.push(True)
                        else:
                            print(self.ofmap)
                            print(self.reference)
                            print(self.ofmap-self.reference)
                            self.done_chn.push(False)
