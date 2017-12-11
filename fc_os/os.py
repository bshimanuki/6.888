from nnsim.module import Module, ModuleList
from nnsim.reg import Reg
from nnsim.channel import Channel

from .pe import PE
from .serdes import InputDeserializer, OutputSerializer
from .glb import GLB
from .noc import IFMapNoC, WeightsNoC

class OSArch(Module):
    def instantiate(self, arr_x, arr_y,
            input_chn, output_chn,
            chn_per_word,
            ifmap_glb_depth, weight_glb_depth):
        # PE static configuration (immutable)
        self.name = 'chip'
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word

        self.stat_type = 'show'

        # Instantiate DRAM IO channels
        self.input_chn = input_chn
        self.output_chn = output_chn

        # Instantiate input deserializer and output serializer
        self.ifmap_wr_chn = Channel(name='ifmap_wr_chn')
        self.weights_wr_chn = Channel(name='weights_wr_chn')
        self.bias_wr_chn = Channel(name='bias_wr_chn')
        self.deserializer = InputDeserializer(self.input_chn, self.ifmap_wr_chn,
                self.weights_wr_chn, self.bias_wr_chn, arr_x, arr_y,
                chn_per_word)

        # Instantiate GLB and GLB channels
        self.ifmap_rd_chn = Channel(3, name='ifmap_rd_chn')
        self.ifmap_glb = GLB(self.ifmap_wr_chn, self.ifmap_rd_chn,
                ifmap_glb_depth, self.arr_y, chn_per_word, name='ifmap_glb')


        self.weights_rd_chn = Channel(name='weights_rd_chn')
        self.weights_glb = GLB(self.weights_wr_chn, self.weights_rd_chn, weight_glb_depth, self.arr_x, self.chn_per_word, name='weight_glb')

        # PE Array and local channel declaration
        self.pe_array = ModuleList()
        self.pe_ifmap_chns = ModuleList()
        self.pe_weight_chns = ModuleList()
        self.pe_bias_chns = ModuleList()
        self.pe_out_chns = ModuleList()

        # Actual array instantiation
        for y in range(self.arr_y):
            self.pe_array.append(ModuleList())
            self.pe_ifmap_chns.append(ModuleList())
            self.pe_weight_chns.append(ModuleList())
            self.pe_out_chns.append(ModuleList())
            for x in range(self.arr_x):
                self.pe_ifmap_chns[y].append(Channel(32, name='pe_ifmap_chns_{}_{}'.format(x, y)))
                self.pe_weight_chns[y].append(Channel(32, name='pe_filter_chns_{}_{}'.format(x, y)))
                self.pe_out_chns[y].append(Channel(32, name='pe_psum_chns_{}_{}'.format(x, y)))
                self.pe_array[y].append(
                    PE(x, y,
                        self.pe_ifmap_chns[y][x],
                        self.pe_weight_chns[y][x],
                        self.pe_out_chns[y][x],
                    )
                )

        # Setup NoC to deliver weights, ifmaps and psums
        self.weight_noc = WeightsNoC(self.weights_rd_chn, self.pe_weight_chns, self.arr_x, self.arr_y)
        self.ifmap_noc = IFMapNoC(self.ifmap_rd_chn, self.pe_ifmap_chns, self.arr_x, self.arr_y)

        self.serializer = OutputSerializer(self.output_chn, self.pe_out_chns, self.arr_x, self.arr_y, chn_per_word)



    def configure(self, batch_size, input_size, output_size):
        self.deserializer.configure(batch_size, input_size, output_size)
        self.ifmap_glb.configure(batch_size * input_size // self.arr_y,
                                 output_size // self.arr_x,
                                 batch_size)
        self.weights_glb.configure((input_size+1) * output_size // self.arr_x,
                                   batch_size // self.arr_y,
                                   self.arr_x)

        self.weight_noc.configure()
        self.ifmap_noc.configure()

        for y in range(self.arr_y):
            for x in range(self.arr_x):
                self.pe_array[y][x].configure(input_size)
