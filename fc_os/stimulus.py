from scipy.signal import correlate2d
import numpy as np

from nnsim.module import Module
from .serdes import InputSerializer, OutputDeserializer

def fc(x, W, b):
    # print x.shape, W.shape, b.shape
    return np.dot(x, W) + b[None,...]

class Stimulus(Module):
    def instantiate(self, arr_x, arr_y, chn_per_word, input_chn, output_chn, done_chn):
        # PE static configuration (immutable)
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word

        self.input_chn = input_chn
        self.output_chn = output_chn
        self.done_chn = done_chn

        self.serializer = InputSerializer(self.input_chn, self.arr_x,
            self.arr_y, self.chn_per_word)
        self.deserializer = OutputDeserializer(self.output_chn, self.done_chn, self.arr_x,
            self.arr_y, self.chn_per_word)

    def configure(self, batch_size, input_size, output_size):
        # Test data
        ifmap = np.random.normal(0, 10, (batch_size, input_size)).astype(np.int64)
        weights = np.random.normal(0, 10, (input_size, output_size)).astype(np.int64)
        bias = np.random.normal(0, 10, output_size).astype(np.int64)
        ofmap = np.zeros((batch_size, output_size)).astype(np.int64)

        # Reference Output
        reference = fc(ifmap, weights, bias)
        #  print(reference)

        self.serializer.configure(ifmap, weights, bias)
        self.deserializer.configure(ofmap, reference)
