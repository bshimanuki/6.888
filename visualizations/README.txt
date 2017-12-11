Make sure to use python 3!

This directory contains the spatial visualizer and temporal visualizer for 6888 nnsim.
Both are described in much more detail in our final paper submission.

The entry point for the spatial visualizer is gui.py.
To see ws_2d visualized:
cd 6.888/visualizations/
rm log.txt
python ws_2d_log_gen.py
cd spatial_visualizer
python gui.py ../log.txt ws_2d_pos.txt

To see meta_tb visualized:
cd 6.888/
rm log.txt
python run.py
cd visualizations/spatial_visualizer/
python gui.py ../../log.txt meta_tb_pos.txt

TEMPORAL VISUALIZER
open google chrome and go to "about://tracing"
load trace.json in temporal_visualizer folder
