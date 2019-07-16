import numpy as np
import os
import cv2
import numpy as np
import json

import visdom

from util import COLORS_10, draw_bboxes, non_max_suppression

import time
import datetime

import cv2
from sort import *

from stats.heatmap import add_heat
from stats.count import *

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
                    (self.dwell, self.count) = read_zones(self.zones)
                    with open(zone_path, 'w') as outfile:
                        json.dump(self.zones, outfile)
        else:
            self.zones = None
            self.dwell = None
            self.count = None
            

    
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
        results = {}
        while True:
            self.frame_count = self.frame_count+1
            print (self.frame_count)
            time_current_frame = time.time()
            # if self.frame_count > 1:
                # print (float(time_current_frame - time_end_frame))
            # print (int(self.vdo.get(cv2.CAP_PROP_POS_FRAMES)))
            # if (self.frame_count == 1) or float(time_current_frame - time_end_frame) > 1/6):
            if True:
                start1 = time.time()
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
                end1 = time.time()
                # print("detection fps: {}".format(1/(end1-start1)))

                start2 = time.time()
                trackers = self.track.update(np_bb)
                # print(trackers)
                results["frame_count"] = str(self.frame_count)
                results["time"] = str(datetime.datetime.now().time())
                results["data"] = []
                results["ids"] = []

                if len(trackers) > 0:
                    bbox_xyxy = trackers[:, :4]
                    identities = trackers[:, -1]

                    for val, count in enumerate(trackers):
                        per_frame = {}

                        #correct coords 
                        x1 = 0 if bbox_xyxy[val][0] < 0 else bbox_xyxy[val][0] 
                        y1 = 0 if bbox_xyxy[val][1] < 0 else bbox_xyxy[val][1]
                        x2 = self.im_width -1 if bbox_xyxy[val][2] > self.im_width else bbox_xyxy[val][2]
                        y2 = self.im_height -1  if bbox_xyxy[val][3] > self.im_height else bbox_xyxy[val][3]

                        per_frame["id"] = (str(identities[val]))
                        per_frame["x1"] = str(x1)
                        per_frame["y1"] = str(y1)
                        per_frame["x2"] = str(x2)
                        per_frame["y2"] = str(y2)

                        

                        results["data"].append(per_frame)
                        results["ids"].append(per_frame["id"])
                        # print (results)
                    ori_im = draw_bboxes(
                        ori_im, bbox_xyxy, identities, offset=(xmin, ymin))

                end2 = time.time()
                
                #TODO - change the way of read/write to append in better dataformat

                json_start_time = time.time()
                stats_uuid = "./data/" + self.cam_uuid + "_stats.json"
                if not os.path.exists(stats_uuid):
                    with open(stats_uuid, mode='w') as feedsjson:
                        data = []
                        data.append(results)
                        feedsjson.write(json.dumps(
                            data, indent=4, sort_keys=False))

                else:
                    with open(stats_uuid, mode='r') as feedsjson:
                        data = json.loads(feedsjson.read())
                        data.append(results)
                    with open(stats_uuid, mode='w') as feedsjson:
                        feedsjson.write(json.dumps(
                            data, indent=4, sort_keys=False))

                json_end_time = time.time()
                stats_start_time = time.time()

                if args.stats:

                    self.update_zone()
                    if self.count != None:
                        ori_im = draw_count_zones(self.count, ori_im)
                        # entrance_counts,useless = do_count(args.output, self.count)
                        # print (entrance_counts)
                    if self.dwell != None:
                        ori_im = draw_dwell_zones(self.dwell, ori_im)
                        # dwell_counts,id_dict_zone = do_count(args.output, self.dwell)
                        # dwell_stats = do_dwell(id_dict_zone,self.dwell)
                        # print (dwell_stats)
                stats_end_time = time.time()

                start3 = time.time()
                if args.visualization:
                    if self.frame_count % 100 == 0 or self.frame_count == 1:
                        heat_map = add_heat(stats_uuid, im,self.cam_uuid)
                    if self.frame_count == 1:
                        reshaped = ori_im.transpose(2, 0, 1)
                        overlay_window = self.vis.image(reshaped)
                        bgs_window = self.vis.image(opening)
                        reshaped_heat_map = heat_map.transpose(2, 0, 1)
                        heatmap_window = self.vis.image(reshaped_heat_map)


                    else:
                        reshaped = ori_im.transpose(2, 0, 1)
                        assert overlay_window is not None, 'Window was none'
                        self.vis.image(reshaped, win=overlay_window)
                        self.vis.image(opening, win=bgs_window)
                        reshaped_heat_map = heat_map.transpose(2, 0, 1)
                        self.vis.image(reshaped_heat_map, win=heatmap_window)
                end3 = time.time()
                # print("fps bgs: {}".format(1/(end1-start1)))
                # print("fps track: {}".format(1/(end2-start2)))
                print("fps e2e: {}".format(1/(end2-start1)))
                # print("fps stats: {}".format(1/(stats_end_time-stats_start_time)))
                # print("fps json: {}".format(1/(json_end_time-json_start_time)))

                # print("fps vis: {}".format(1/(end3-start3)))

                print("fps final: {}".format(1/(stats_end_time-start1)))

                time_end_frame = time.time()
                sync_time = 1/self.vdo.get(cv2.CAP_PROP_FPS)-(time_end_frame - time_current_frame)
                if (sync_time > 0):
                    print("sleeping", sync_time)
                    time.sleep(sync_time)

