from nnsim.module import Module
from nnsim.channel import Channel
from nnsim.simulator import Finish
from conv_ws.tb import WSArchTB
from fc_os.tb import OSArchTB

import numpy as np

class Layer(object):
    def __init__(self, activations):
        self.activations = activations

    def activation(self, x):
        for a in self.activations:
            x = a(x)
        return x

    def new_shape(self, shape):
        for a in self.activations:
            shape = a.new_shape(shape)
        return shape

class Conv(Layer):
    def __init__(self, image_size, filter_size, in_chn, out_chn, name, activations=()):
        super(Conv, self).__init__(activations)
        self.image_size = image_size
        self.filter_size = filter_size
        self.in_chn = in_chn
        self.out_chn = out_chn
        self.name = name

class FC(Layer):
    def __init__(self, input_size, output_size, name, activations=()):
        super(FC, self).__init__(activations)
        self.input_size = input_size
        self.output_size = output_size
        self.name = name

class Activation(object):
    '''Acts on the entire nd array (entire batch).'''
    def __init__(self, func, name):
        self.func = func
        self.name = name

    def __call__(self, x):
        return self.func(x)

    def new_shape(self, shape):
        '''Return output shape given input shape.'''
        return shape

class Pool(Activation):
    def __init__(self, dh, dw, name):
        self.name = name
        self.dh = dh
        self.dw = dw

    def __call__(self, x):
        return x.reshape((
            x.shape[0],
            x.shape[1]//self.dh, self.dh,
            x.shape[2]//self.dw, self.dw,
            x.shape[3]
        )).max(axis=(2,4))

    def new_shape(self, shape):
        return (
            shape[0],
            shape[1]//self.dh,
            shape[2]//self.dw,
            shape[3]
        )

class ReLU(Activation):
    def __init__(self, name):
        super(ReLU, self).__init__(self.relu, name)

    def relu(self, x):
        return np.maximum(x, 0)

class MetaArchTB(Module):
    def instantiate(self, arr_x, arr_y, chn_per_word, layers, batch_size):
        self.arr_x = arr_x
        self.arr_y = arr_y
        self.chn_per_word = chn_per_word
        self.layers = layers
        self.batch_size = batch_size

        self.name = 'meta'

        self.started = False
        self.done_chn = Channel()

        self.ifmap_glb_depth = 0
        self.psum_glb_depth = 0
        self.weights_glb_depth = 0

        use_conv = False
        use_fc = False

        self.conv_tb = None
        self.fc_tb = None

        cur_image_size = None
        cur_in_chn = None
        is_conv = False

        num_convs = 0
        num_fc = 0

        for layer in self.layers:
            if isinstance(layer, Conv):
                if cur_image_size is None:
                    pass
                elif cur_image_size != layer.image_size or cur_in_chn != layer.in_chn:
                    raise Exception('Invalid conv image size for %s: %s %s' % (layer.name, (cur_image_size, cur_in_chn), (layer.image_size, layer.in_chn)))
                ifmap_glb_depth, psum_glb_depth, weights_glb_depth = WSArchTB.required_glb_depth(self.arr_x, self.arr_y, self.chn_per_word, layer.image_size, layer.filter_size, layer.in_chn, layer.out_chn)
                use_conv = True
                output_shape = layer.new_shape((self.batch_size,) + layer.image_size + (layer.out_chn,))
                cur_image_size = output_shape[1:3]
                cur_in_chn = output_shape[3]
                is_conv = True
                num_convs += 1
            elif isinstance(layer, FC):
                if cur_image_size is None:
                    pass
                elif not is_conv and cur_image_size != layer.input_size:
                    raise Exception('Invalid fc dimension transition for ' + layer.name)
                elif is_conv and cur_image_size[0] * cur_image_size[1] * cur_in_chn != layer.input_size:
                    raise Exception('Invalid conv to fc dimension transition to ' + layer.name)
                ifmap_glb_depth, psum_glb_depth, weights_glb_depth = OSArchTB.required_glb_depth(self.arr_x, self.arr_y, self.chn_per_word, self.batch_size, layer.input_size, layer.output_size)
                use_fc = True
                _, cur_image_size = layer.new_shape((self.batch_size, layer.output_size))
                is_conv = False
                num_fc += 1
            else:
                raise Exception('layer not valid')
            self.ifmap_glb_depth = max(self.ifmap_glb_depth, ifmap_glb_depth)
            self.psum_glb_depth = max(self.psum_glb_depth, psum_glb_depth)
            self.weights_glb_depth = max(self.weights_glb_depth, weights_glb_depth)

        if use_conv:
            self.conv_tb = WSArchTB(self.arr_x, self.arr_y, self.chn_per_word, self.done_chn, self.ifmap_glb_depth, self.psum_glb_depth, self.weights_glb_depth)
        if use_fc:
            self.fc_tb = OSArchTB(self.arr_x, self.arr_y, self.chn_per_word, self.done_chn, self.ifmap_glb_depth, self.psum_glb_depth, self.weights_glb_depth)

        self.layer_step = 0
        self.batch_step = 0
        self.conv_inputs = [None] * self.batch_size
        self.fc_input = None

        self.conv_weights = [None] * num_convs
        self.conv_bias = [None] * num_convs

        self.fc_weights = [None] * num_fc
        self.fc_bias = [None] * num_fc

        self.cur_conv = 0
        self.cur_fc = 0

    def tick(self):
        if not self.started or self.done_chn.valid():
            self.started = True
            old_layer = self.layers[self.layer_step]

            if self.done_chn.valid():
                valid = self.done_chn.pop()
                if not valid:
                    raise Finish('Validation Failed')
                if isinstance(old_layer, Conv):
                    self.conv_inputs[self.batch_step] = self.conv_tb.get_output()
                    self.batch_step += 1
                    if self.batch_step == self.batch_size:
                        self.conv_inputs = [batch for batch in old_layer.activation(np.array(self.conv_inputs))]
                        self.batch_step = 0
                        self.layer_step += 1
                        self.cur_conv += 1
                else:
                    self.fc_input = self.fc_tb.get_output()
                    self.fc_input = old_layer.activation(self.fc_input)
                    self.layer_step += 1
                    self.cur_fc += 1
                if self.layer_step == len(self.layers):
                    raise Finish('Success')

            layer = self.layers[self.layer_step]

            # handle conv to fc transition
            if isinstance(layer, FC) and self.fc_input is None and self.conv_inputs[0] is not None:
                if self.name != None:
                    self.output_file.write("FC MODE\n")
                self.fc_input = np.zeros((self.batch_size, layer.input_size)).astype(np.int64)
                for i in range(self.batch_size):
                    self.fc_input[i] = self.conv_inputs[i].reshape(layer.input_size)

            if isinstance(layer, Conv):
                if self.name != None:
                    self.output_file.write("CONV MODE\n")
                if self.conv_inputs[self.batch_step] is None:
                    _, weights, bias = self.conv_tb.configure(layer.image_size, layer.filter_size, layer.in_chn, layer.out_chn)
                    self.conv_weights[self.cur_conv] = weights
                    self.conv_bias[self.cur_conv] = bias
                elif self.conv_weights[self.cur_conv] is None or self.conv_bias[self.cur_conv] is None:
                    weights, bias = self.conv_tb.configure_fixed_image(self.conv_inputs[self.batch_step], layer.filter_size, layer.in_chn, layer.out_chn)
                    self.conv_weights[self.cur_conv] = weights
                    self.conv_bias[self.cur_conv] = bias
                else:
                    self.conv_tb.configure_fixed(self.conv_inputs[self.batch_step], self.conv_weights[self.cur_conv], self.conv_bias[self.cur_conv])

            elif isinstance(layer, FC):
                if self.fc_input is None:
                    _, weights, bias = self.fc_tb.configure(self.batch_size, layer.input_size, layer.output_size)
                    self.fc_weights[self.cur_fc] = weights
                    self.fc_bias[self.cur_fc] = bias
                elif self.fc_weights[self.cur_fc] is None or self.fc_bias[self.cur_fc] is None:
                    weights, bias = self.fc_tb.configure_fixed_image(self.fc_input, layer.output_size)
                    self.fc_weights[self.cur_fc] = weights
                    self.fc_bias[self.cur_fc] = bias
                else:
                    self.fc_tb.configure_fixed(self.fc_input, self.fc_weights[self.cur_fc], self.fc_bias[self.cur_fc])
            else:
                raise Exception('layer not valid')
