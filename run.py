from nnsim.simulator import run_tb
from meta_tb import MetaArchTB, Conv, FC, ReLU, Pool

if __name__ == "__main__":
    layers = [
        Conv(image_size=(8, 8),
             filter_size=(3, 3),
             in_chn=3,
             out_chn=6,
             name='conv1',
             activations=(ReLU('name=relu1'),Pool(dh=2,dw=2,name='pool'))
             ),
        Conv(image_size=(4, 4),
             filter_size=(3, 3),
             in_chn=6,
             out_chn=2,
             name='conv2',
             activations=(ReLU('name=relu2'),)
             ),
        FC(input_size=32,
           output_size=11,
           name='fc1',
           activations=(ReLU('name=relu3'),)
           ),
        FC(input_size=11,
           output_size=3,
           name='fc2',
           activations=(ReLU('name=relu4'),)
           ),
    ]

    tb = MetaArchTB(arr_x=8,
                    arr_y=4,
                    chn_per_word=4,
                    layers=layers,
                    batch_size=2
                    )
    run_tb(tb, verbose=False)
