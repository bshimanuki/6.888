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
        self.tile_in = 0
        self.tile_out = 0
        self.tile_ins = 0
        self.tile_outs = 0

        self.image_size = (0, 0)
        self.filter_size = (0, 0)

        self.ifmap_done = True
        self.psum_done = True
        self.pass_done = Reg(False)

        # State Counters
        self.curr_set = 0
        self.curr_filter = 0
        self.iteration = 0
        self.fmap_idx = 0

    def configure(self, ifmap, weights, bias, image_size, filter_size, tile_ins, tile_outs):
        self.ifmap = ifmap
        self.weights = weights
        self.bias = bias

        self.image_size = image_size
        self.filter_size = filter_size

        self.tile_in = 0
        self.tile_out = 0
        self.tile_ins = tile_ins
        self.tile_outs = tile_outs

        self.ifmap_done = False
        self.psum_done = False
        self.pass_done.wr(False)

    def tick(self):
        if self.pass_done.rd():
            return

        full_in_sets = self.tile_ins*self.arr_y//self.chn_per_word
        in_sets = self.arr_y//self.chn_per_word
        out_sets = self.arr_x//self.chn_per_word
        fmap_per_iteration = self.image_size[0]*self.image_size[1]
        num_iteration = self.filter_size[0]*self.filter_size[1]

        if not self.psum_done:
            for _ in range(1):
                if self.arch_input_chn.vacancy():
                    # print "input append"

                    x = self.fmap_idx % self.image_size[0]
                    y = self.fmap_idx // self.image_size[0]

                    if not self.ifmap_done:
                        cmin = self.curr_set*self.chn_per_word
                        cmax = cmin + self.chn_per_word
                        # Write ifmap to glb
                        if cmax > len(self.ifmap[x, y]):
                            num_zeros = cmax - len(self.ifmap[x, y])
                            cmax = len(self.ifmap[x, y])
                            data = np.array([ self.ifmap[x, y, c] for c in range(cmin, cmax) ] + [0] * num_zeros)
                        else:
                            data = np.array([ self.ifmap[x, y, c] for c in range(cmin, cmax) ])
                    else:
                        cmin = self.tile_out*self.arr_x + self.curr_set*self.chn_per_word
                        cmax = cmin + self.chn_per_word
                        # Write bias to glb
                        if cmax > len(self.bias):
                            num_zeros = cmax - len(self.bias)
                            cmax = len(self.bias)
                            data = np.array([ self.bias[c] for c in range(cmin, cmax) ] + [0] * num_zeros)
                        else:
                            data = np.array([ self.bias[c] for c in range(cmin, cmax) ])
                    self.arch_input_chn.push(data)
                    self.curr_set += 1

                    if not self.ifmap_done:
                        if self.curr_set == full_in_sets:
                            self.curr_set = 0
                            self.fmap_idx += 1
                    else:
                        if self.curr_set == out_sets:
                            self.curr_set = 0
                            self.fmap_idx += 1
                    if self.fmap_idx == fmap_per_iteration:
                        self.fmap_idx = 0
                        if not self.ifmap_done:
                            self.ifmap_done = True
                        else:
                            self.psum_done = True
                            # print "---- Wrote inputs and biases ----"
        else:
            f_x = self.iteration % self.filter_size[0]
            f_y = self.iteration // self.filter_size[0]

            # Push filters to PE columns. (PE is responsible for pop)
            if self.arch_input_chn.vacancy() and self.tile_out < self.tile_outs:
                cmin = self.tile_in*self.arr_y + self.curr_set*self.chn_per_word
                cmax = cmin + self.chn_per_word
                filter_out = self.tile_out * self.arr_x + self.curr_filter
                if filter_out >= len(self.weights[f_x, f_y, cmin]):
                    data = np.array([0] * (cmax - cmin))
                elif cmax > len(self.weights[f_x, f_y]):
                    num_zeros = cmax - len(self.weights[f_x, f_y])
                    cmax = len(self.weights[f_x, f_y])
                    data = np.array([self.weights[f_x, f_y, c, filter_out] \
                            for c in range(cmin, cmax) ] + [0] * num_zeros)
                else:
                    data = np.array([self.weights[f_x, f_y, c, filter_out] \
                            for c in range(cmin, cmax) ])

                self.arch_input_chn.push(data)
                self.curr_set += 1
                if self.curr_set == in_sets:
                    self.curr_set = 0
                    self.curr_filter += 1
                if self.curr_filter == self.arr_x:
                    self.curr_filter = 0
                    # print "---- Wrote weights iteration: %d ----" % self.iteration
                    self.iteration += 1
                if self.iteration == num_iteration:
                    self.iteration = 0
                    self.tile_in += 1
                    if self.tile_in == self.tile_ins:
                        self.tile_in = 0
                        self.psum_done = False
                        self.tile_out += 1
                        if self.tile_out == self.tile_outs:
                            # print "---- Wrote all weights ----"
                            self.pass_done.wr(True)


class InputDeserializer(Module):
    def instantiate(self, arch_input_chn, ifmap_chn, weights_chn, bias_chn, psum_chn,
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
        self.psum_chn = psum_chn

        self.image_size = (0, 0)
        self.filter_size = (0, 0)

        self.fmap_idx = 0
        self.curr_set = 0
        self.tile_ins = 0
        self.tile_in = 0
        self.tile_outs = 0
        self.tile_out = 0
        self.ifmap_done = False

    def configure(self, image_size, filter_size, full_in_sets, tile_ins, tile_outs):
        self.image_size = image_size
        self.filter_size = filter_size

        self.fmap_idx = 0
        self.curr_set = 0
        self.ifmap_done = False
        self.full_in_sets = full_in_sets
        self.tile_ins = tile_ins
        self.tile_in = 0
        self.tile_outs = tile_outs
        self.tile_out = 0

    def tick(self):
        # in_sets = self.arr_y//self.chn_per_word
        in_sets = self.full_in_sets
        out_sets = self.arr_x//self.chn_per_word
        psets = self.arr_x * self.arr_y // self.chn_per_word
        fmap_per_iteration = self.image_size[0]*self.image_size[1]
        weights_per_iteration = self.filter_size[0]*self.filter_size[1]

        source_chn = self.arch_input_chn
        if self.fmap_idx < fmap_per_iteration:
            if not self.ifmap_done:
                target_chn = self.ifmap_chn
                target_str = 'ifmap'
            else:
                target_chn = self.bias_chn
                target_str = 'psum'
                if self.tile_in > 0:
                    source_chn = self.psum_chn
        else:
            target_chn = self.weights_chn
            target_str = 'weights'

        if source_chn.valid():
            if target_chn.vacancy():
                # print "des to ", target_str
                data = [e for e in source_chn.pop()]
                self.raw_stats['dram_rd'] += len(data)
                target_chn.push(data)
                self.curr_set += 1
                if self.fmap_idx < fmap_per_iteration:
                    if not self.ifmap_done:
                        if self.curr_set == in_sets:
                            self.curr_set = 0
                            self.fmap_idx += 1
                        if self.fmap_idx == fmap_per_iteration:
                            self.fmap_idx = 0
                            self.ifmap_done = True
                    else:
                        if self.curr_set == out_sets:
                            self.curr_set = 0
                            self.fmap_idx += 1
                else:
                    if self.curr_set == psets:
                        self.curr_set = 0
                        self.fmap_idx += 1
                        if self.fmap_idx == fmap_per_iteration + weights_per_iteration:
                            self.fmap_idx = 0
                            self.tile_in += 1
                            if self.tile_in == self.tile_ins:
                                self.tile_in = 0
                                self.tile_out += 1
                                if self.tile_out == self.tile_outs:
                                    self.tile_out = 0

class OutputSerializer(Module):
    def instantiate(self, arch_output_chn, arr_chn, psum_chn, arr_x, arr_y, chn_per_word):
        self.arch_output_chn = arch_output_chn
        self.arr_chn = arr_chn
        self.psum_chn = psum_chn

        self.chn_per_word = chn_per_word
        self.arr_x = arr_x
        self.arr_y = arr_y

        self.stat_type = 'aggregate'
        self.raw_stats = {'dram_wr' : 0}

        self.image_size = (0, 0)
        self.tile_in = 0
        self.tile_out = 0
        self.tile_ins = 0
        self.tile_outs = 0

        self.ofmap = None
        self.reference = None

        self.curr_set = 0
        self.fmap_idx = 0


    def configure(self, image_size, tile_ins, tile_outs):
        self.image_size = image_size
        self.tile_in = 0
        self.tile_out = 0
        self.tile_ins = tile_ins
        self.tile_outs = tile_outs

    def tick(self):
        out_sets = self.arr_x//self.chn_per_word
        fmap_per_iteration = self.image_size[0]*self.image_size[1]

        if self.arr_chn.valid() and self.psum_chn.vacancy() and self.arch_output_chn.vacancy():
            data = [e for e in self.arr_chn.pop()]

            if self.tile_in < self.tile_ins - 1:
                self.psum_chn.push(data)
            else:
                self.raw_stats['dram_wr'] += len(data)
                self.arch_output_chn.push(data)

            self.curr_set += 1
            if self.curr_set == out_sets:
                self.curr_set = 0
                self.fmap_idx += 1
            if self.fmap_idx == fmap_per_iteration:
                self.fmap_idx = 0
                self.tile_in += 1
                if self.tile_in == self.tile_ins:
                    self.tile_in = 0
                    self.tile_out += 1
                    if self.tile_out == self.tile_outs:
                        self.tile_out = 0


class OutputDeserializer(Module):
    def instantiate(self, arch_output_chn, arr_x, arr_y, chn_per_word):
        # PE static configuration (immutable)
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word

        self.arch_output_chn = arch_output_chn

        self.tile_in = 0
        self.tile_out = 0
        self.tile_ins = 0
        self.tile_outs = 0

        self.ofmap = None
        self.reference = None

        self.image_size = (0, 0)

        self.curr_set = 0
        self.fmap_idx = 0
        
        self.pass_done = Reg(False)

    def configure(self, ofmap, reference, image_size, tile_ins, tile_outs):
        self.ofmap = ofmap
        self.reference = reference

        self.image_size = image_size

        self.tile_out = 0
        self.tile_outs = tile_outs

        self.curr_set = 0
        self.fmap_idx = 0

        self.pass_done.wr(False)

    def tick(self):
        if self.pass_done.rd():
            return

        out_sets = self.arr_x//self.chn_per_word
        fmap_per_iteration = self.image_size[0]*self.image_size[1]

        if self.arch_output_chn.valid():
            data = [e for e in self.arch_output_chn.pop()]

            x = self.fmap_idx % self.image_size[0]
            y = self.fmap_idx // self.image_size[0]

            if self.curr_set < out_sets:
                cmin = self.tile_out*self.arr_x + self.curr_set*self.chn_per_word
                cmax = min(cmin + self.chn_per_word, len(self.ofmap[x, y]))
                for c in range(cmin, cmax):
                    self.ofmap[x, y, c] = data[c-cmin]
            self.curr_set += 1

            if self.curr_set == out_sets:
                self.curr_set = 0
                self.fmap_idx += 1
            if self.fmap_idx == fmap_per_iteration:
                self.fmap_idx = 0
                self.tile_out += 1
                if self.tile_out == self.tile_outs:
                    self.tile_out = 0
                    self.pass_done.wr(True)
                    if np.all(self.ofmap == self.reference):
                        raise Finish("Success")
                    else:
                        #  print(self.ofmap)
                        #  print(self.reference)
                        #  print(self.ofmap-self.reference)
                        raise Finish("Validation Failed")

