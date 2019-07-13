import os
import cv2
import numpy as np
import configargparse
import sys
import time
from det_track import Detector

def parse_arguments(cliargs=None):

    default_config = os.path.join('config.ini')
    
    # parse arguments
    parser = configargparse.ArgumentParser(
        default_config_files=[default_config], description='detector and tracker parameters')
    parser.add_argument( "--input"   ,type=str, help="path to video",required=True)
    parser.add_argument( "--visualization"   ,type=bool, help="displays live visualized output detections and tracking in a visdom",default=False)
    parser.add_argument( "--zones"   ,type=str, help="path to zones files")
    parser.add_argument( "--stats"   ,type=bool, help="set true for computing zones information like count and dwell",default=False)
    parser.add_argument( "--threshold"   ,type=int, help="Area in pixel to which the less sized box are removed as noise",default=100)
    parser.add_argument( "--mode"   ,type=int, help="modes changes with the processing size of the image 0-original 1-640*480, 2-480*320, 3-320*240, ",default=2)
    parser.add_argument( "--output"   ,type=str, help="csv output file name",default="./data/stats.json")


    if cliargs is None:
        args, unknown = parser.parse_known_args()

    else:
        args, unknown = parser.parse_known_args(cliargs)
    
    return args

if __name__=="__main__":
    
    args = parse_arguments(sys.argv)

    det = Detector(args)
    det.open(args)

    det.detect(args)
    
