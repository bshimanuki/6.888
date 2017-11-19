from nnsim.module import Module, ModuleList
from nnsim.reg import Reg
from nnsim.channel import Channel

from .pe import PE
from .serdes import InputDeserializer, OutputSerializer
from .glb import IFMapGLB, WeightsGLB
from .noc import IFMapNoC, WeightsNoC, BiasNoC

class WSArch(Module):
    def instantiate(self, arr_x, arr_y,
            input_chn, output_chn,
            chn_per_word,
            ifmap_glb_depth, weight_glb_depth, in_chn):
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
        self.ifmap_wr_chn = Channel()
        self.weights_wr_chn = Channel()
        self.bias_wr_chn = Channel()
        self.deserializer = InputDeserializer(self.input_chn, self.ifmap_wr_chn,
                self.weights_wr_chn, self.bias_wr_chn, arr_x, arr_y,
                chn_per_word)

        # Instantiate GLB and GLB channels
        self.ifmap_rd_chn = Channel(3)
        self.ifmap_glb = IFMapGLB(self.ifmap_wr_chn, self.ifmap_rd_chn,
                ifmap_glb_depth, chn_per_word, in_chn)


        self.weights_rd_chn = Channel()
        self.weights_glb = WeightsGLB(self.weights_wr_chn, self.weights_rd_chn, weight_glb_depth, arr_x)

        # PE Array and local channel declaration
        self.pe_array = ModuleList()
        self.pe_ifmap_chns = ModuleList()
        self.pe_filter_chns = ModuleList()
        self.pe_bias_chns = ModuleList()
        self.pe_out_chns = ModuleList()

        # Actual array instantiation
        for y in range(self.arr_y):
            self.pe_array.append(ModuleList())
            self.pe_ifmap_chns.append(ModuleList())
            self.pe_filter_chns.append(ModuleList())
            self.pe_bias_chns.append(ModuleList())
            self.pe_out_chns.append(ModuleList())
            for x in range(self.arr_x):
                self.pe_ifmap_chns[y].append(Channel(32))
                self.pe_filter_chns[y].append(Channel(32))
                self.pe_bias_chns[y].append(Channel(32))
                self.pe_out_chns[y].append(Channel(32))
                self.pe_array[y].append(
                    PE(x, y,
                        self.pe_ifmap_chns[y][x],
                        self.pe_filter_chns[y][x],
                        self.pe_bias_chns[y][x],
                        self.pe_out_chns[y][x]
                    )
                )

        # Setup NoC to deliver weights, ifmaps and psums
        self.filter_noc = WeightsNoC(self.weights_rd_chn, self.pe_filter_chns, self.arr_x)
        self.ifmap_noc = IFMapNoC(self.ifmap_rd_chn, self.pe_ifmap_chns, self.arr_x, self.chn_per_word)
        self.bias_noc = BiasNoC(self.bias_wr_chn, self.pe_bias_chns, self.arr_x, self.arr_y)

        self.serializer = OutputSerializer(self.output_chn, self.pe_out_chns, self.arr_x, self.arr_y, chn_per_word)



    def configure(self, image_size, filter_size, in_chn, out_chn):
        in_sets = self.arr_y//self.chn_per_word
        out_sets = self.arr_x//self.chn_per_word
        fmap_per_iteration = image_size[0]*image_size[1]
        num_iteration = filter_size[0]*filter_size[1]

        self.deserializer.configure(image_size)
        self.ifmap_glb.configure(image_size, filter_size, in_sets, fmap_per_iteration)
        self.weights_glb.configure(image_size[0] / self.chn_per_word, num_iteration * in_chn)

        self.filter_noc.configure(self.arr_x, self.arr_y)
        self.ifmap_noc.configure(in_sets)
        self.bias_noc.configure()

        for y in range(self.arr_y):
            for x in range(self.arr_x):
                self.pe_array[y][x].configure(filter_size[0] * in_chn)
