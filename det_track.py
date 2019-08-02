import numpy as np
import os
import cv2
import numpy as np
import json

import visdom

from util import COLORS_10, draw_bboxes, non_max_suppression

import time
import datetime
import pandas as pd
import cv2
from sort import *

from stats.heatmap import add_heat
from stats.count import *

from shapely.geometry.polygon import Polygon
from rest_api.routes import do_count_rest



cv2.setNumThreads(1)    

class Detector(object):
    def __init__(self, args,cam_uuid):
        self.vdo = cv2.VideoCapture()
        
        # self.vdo.set(cv2.CAP_PROP_FPS,100)
        self.frame_count = 0
        self.vis = visdom.Visdom()
        self.bgs = cv2.createBackgroundSubtractorMOG2()
        self.track = Sort()
        self.cam_uuid = cam_uuid
         
        if args.zones != None:
            zone_path = "./data/" + self.cam_uuid + "_zone.json"
            if os.path.isfile(args.zones):
                with open(args.zones, mode='r') as zone_json:
                    self.zones = json.loads(zone_json.read())
                    (self.dwell, self.count,self.lines) = read_zones(self.zones)
                    with open(zone_path, 'w') as outfile:
                        json.dump(self.zones, outfile)
        else:
            self.zones = None
            self.dwell = None
            self.count = None
            self.lines = None

            

    
    def update_zone(self):
        zone_path = "./data/" + self.cam_uuid + "_zone.json"
        if os.path.isfile(zone_path):
            with open(zone_path, mode='r') as zone_json:
        # default_location = "./data/zone.json"
        # if os.path.isfile(default_location):
            # with open(default_location, mode='r') as zone_json:
                self.zones = json.loads(zone_json.read())

    def open(self, args):
        if "rtsp" not in args.input:
            assert os.path.isfile(args.input), "Error: path error"
        self.vdo.open(args.input)
        self.im_width = int(self.vdo.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.im_height = int(self.vdo.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.area = 0, 0, self.im_width, self.im_height
        if args.mode == 1:
            self.im_width = 640
            self.im_height = 480
        elif args.mode == 2:    
            self.im_width = 480
            self.im_height = 320
        elif args.mode == 3:
            self.im_width = 320
            self.im_height = 240
        # if args.zones != None:
        #     print(self.zones)
        #     (self.dwell, self.count) = read_zones(self.zones,self.im_height,self.im_width)
        #     # assert int(self.zones["imageWidth"]
        #     #         ) == self.im_width, "Error sizes doesnt match"
        #     # assert int(self.zones["imageHeight"]
        #     #         ) == self.im_height, "Error sizes doesnt match"
                    
        return self.vdo.isOpened()

    def detect(self, args):
        xmin, ymin, xmax, ymax = self.area
        df = pd.DataFrame()
        while True:
            
            self.frame_count = self.frame_count+1
            print (self.frame_count)
            time_current_frame = time.time()
            # if self.frame_count > 1:
                # print (float(time_current_frame - time_end_frame))
            # print (int(self.vdo.get(cv2.CAP_PROP_POS_FRAMES)))
            # if (self.frame_count == 1) or float(time_current_frame - time_end_frame) > 1/6):
            startbgs = time.time()
            # print (time.time())
            _, resized_img = self.vdo.read()

            if args.mode == 1:
                ori_im = cv2.resize(resized_img,(640, 480))
                self.im_width = 640
                self.im_height = 480
            elif args.mode == 2:    
                ori_im = cv2.resize(resized_img,(480, 320))
                self.im_width = 480
                self.im_height = 320
            elif args.mode == 3:
                ori_im = cv2.resize(resized_img,(320, 240))
                self.im_width = 320
                self.im_height = 240
            else:
                ori_im = resized_img
            im = ori_im[ymin:ymax, xmin:xmax, (2, 1, 0)]
            fgmask = self.bgs.apply(im)
            fgthres = cv2.threshold(fgmask.copy(), 200, 255, cv2.THRESH_BINARY)[1]
            kernel = np.ones((3,3),np.uint8)
            opening = cv2.morphologyEx(fgthres, cv2.MORPH_OPEN, kernel)
            im2, cnts, hierarchy = cv2.findContours(opening.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            bbox = []
            for c in cnts:
                if cv2.contourArea(c) > args.threshold:
                    x,y,w,h = cv2.boundingRect(c)
                    box = np.array([x, y, x+w, y+h,1])
                    bbox.append(box)
                    cv2.rectangle(fgmask,(x,y),(x+w,y+h),(0,255,0),2)
                    
            np_bb = np.asarray(bbox)
            indices = non_max_suppression(np_bb, 0.7)
            bbox = [bbox[i] for i in indices]
            endbgs = time.time()
            # print("detection fps: {}".format(1/(end1-start1)))

            trackstart = time.time()
            trackers = self.track.update(np_bb)
            # print(trackers)
            

            if len(trackers) > 0:
                bbox_xyxy = trackers[:, :4]
                identities = trackers[:, -1]
                results = {}
                results["frame_count"] = [str(self.frame_count)]
                results["time"] = [str(datetime.datetime.now().time())]
                results["epoch"] = [str(datetime.datetime.now().timestamp())]
                for val, count in enumerate(trackers):
                    #correct coords 
                    x1 = 0 if bbox_xyxy[val][0] < 0 else bbox_xyxy[val][0] 
                    y1 = 0 if bbox_xyxy[val][1] < 0 else bbox_xyxy[val][1]
                    x2 = self.im_width -1 if bbox_xyxy[val][2] > self.im_width else bbox_xyxy[val][2]
                    y2 = self.im_height -1  if bbox_xyxy[val][3] > self.im_height else bbox_xyxy[val][3]

                    results["id"] = [str(int(identities[val]))]
                    results["x1"] = [str(x1)]
                    results["y1"] = [str(y1)]
                    results["x2"] = [str(x2)]
                    results["y2"] = [str(y2)]
                    results["footpoint"] = [str(Point(round((x2+x1)/2),round(y2)))]
                    for i in self.dwell:
                        results[i["label"]] = [""]
                    for j in self.count:
                        results[j["label"]] = [""]
                    for dwell_zone in self.dwell:
                        if get_polygons(dwell_zone).contains(Point(round((x2+x1)/2),round(y2))):
                            results[dwell_zone["label"]] = True
                    for count_zone in self.count:
                        if get_polygons(count_zone).contains(Point(round((x2+x1)/2),round(y2))):
                            results[count_zone["label"]] = True
                    # print (df)
                    df = df.append(pd.DataFrame.from_dict(results))
                ori_im = draw_bboxes(
                    ori_im, bbox_xyxy, identities, offset=(xmin, ymin))
            trackend = time.time()
            
            dfstart = time.time()
            df = df.reset_index(drop=True)
            stats_uuid = "./data/" + self.cam_uuid + "_stats.json"
            df.to_json(stats_uuid,orient='records')
            
            # do_count_rest(self.cam_uuid)
            dfend = time.time()
            if args.stats:
                if self.count != None:
                    ori_im = draw_count_zones(self.count, ori_im)
                if self.dwell != None:
                    ori_im = draw_dwell_zones(self.dwell, ori_im)
                if self.lines != None:
                    ori_im = draw_lines(self.lines, ori_im)
            stats_end_time = time.time()

            visstart = time.time()
            if args.visualization:
                # if self.frame_count % 100 == 0 or self.frame_count == 1:
                    # heat_map = add_heat(stats_uuid, im,self.cam_uuid)
                if self.frame_count == 1:
                    reshaped = ori_im.transpose(2, 0, 1)
                    overlay_window = self.vis.image(reshaped)
                    bgs_window = self.vis.image(opening)
                    # reshaped_heat_map = heat_map.transpose(2, 0, 1)
                    # heatmap_window = self.vis.image(reshaped_heat_map)


                else:
                    reshaped = ori_im.transpose(2, 0, 1)
                    assert overlay_window is not None, 'Window was none'
                    self.vis.image(reshaped, win=overlay_window)
                    self.vis.image(opening, win=bgs_window)
                    # reshaped_heat_map = heat_map.transpose(2, 0, 1)
                    # self.vis.image(reshaped_heat_map, win=heatmap_window)
            visend = time.time()
            print("fps bgs: {}".format(1/(endbgs-startbgs)))
            print("fps track: {}".format(1/(trackend-trackstart)))
            print("fps e2e: {}".format(1/(trackend-startbgs)))
            print("fps df: {}".format(1/(dfend-dfstart)))
            # print("fps vis: {}".format(1/(visend-visstart)))
            time_end_frame = time.time()
            print("fps final: {}".format(1/(time_end_frame-time_current_frame)))

            sync_time = 1/self.vdo.get(cv2.CAP_PROP_FPS)-(time_end_frame - time_current_frame)
            if (sync_time > 0):
                print("sleeping", sync_time)
                time.sleep(sync_time)

