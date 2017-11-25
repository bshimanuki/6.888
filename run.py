from nnsim.simulator import run_tb
from meta_tb import MetaArchTB, Conv, FC

if __name__ == "__main__":
    layers = [
        Conv(image_size=(5, 4),
             filter_size=(3, 3),
             in_chn=3,
             out_chn=9,
             ),
        Conv(image_size=(4, 4),
             filter_size=(3, 3),
             in_chn=5,
             out_chn=8,
             ),
        FC(batch_size=3,
           input_size=7,
           output_size=11,
           ),
        FC(batch_size=11,
           input_size=3,
           output_size=3,
           ),
    ]

    tb = MetaArchTB(arr_x=8,
                    arr_y=4,
                    chn_per_word=4,
                    layers=layers,
                    )
    run_tb(tb, verbose=False)
