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
from util import *

from shapely.geometry.polygon import Polygon
# from rest_api.routes import do_count_rest
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')


cv2.setNumThreads(1)



def is_similar(image1, image2):
    return image1.shape == image2.shape and not(np.bitwise_xor(image1, image2).any())


class Detector(object):
    def __init__(self, args, cam_uuid):
        self.vdo = cv2.VideoCapture()

        # self.vdo.set(cv2.CAP_PROP_FPS,100)
        self.frame_count = 0
        self.vis = visdom.Visdom()
        self.bgs = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=True)
        self.track = Sort()
        self.cam_uuid = cam_uuid

        if args.zones != None:
            zone_path = "./data/" + self.cam_uuid + "_zone.json"
            if os.path.isfile(args.zones):
                with open(args.zones, mode='r') as zone_json:
                    self.zones = json.loads(zone_json.read())
                    (self.dwell_zones, self.count_lines) = read_zones(self.zones)
                    with open(zone_path, 'w') as outfile:
                        json.dump(self.zones, outfile)
        else:
            self.dwell_zones = None
            self.count_lines = None
        
        self.logger = logging.getLogger()
        self.logger.addHandler(logging.FileHandler("./data/" + self.cam_uuid + ".log", 'a'))


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
            # print(self.frame_count)
            time_current_frame = time.time()

            startbgs = time.time()
            # print (time.time())
            _, resized_img = self.vdo.read()

            # checker for same image
            # if self.frame_count == 1:
            #     previous_image = resized_img
            # else:
            #     print(is_similar(previous_image,resized_img))

            if args.mode == 1:
                ori_im = cv2.resize(resized_img, (640, 480))
                self.im_width = 640
                self.im_height = 480
            elif args.mode == 2:
                ori_im = cv2.resize(resized_img, (480, 320))
                self.im_width = 480
                self.im_height = 320
            elif args.mode == 3:
                ori_im = cv2.resize(resized_img, (320, 240))
                self.im_width = 320
                self.im_height = 240
            else:
                ori_im = resized_img

            im = ori_im[ymin:ymax, xmin:xmax, (2, 1, 0)]
            fgmask = self.bgs.apply(im)
            fgthres = cv2.threshold(
                fgmask.copy(), 200, 255, cv2.THRESH_BINARY)[1]
            kernel = np.ones((3, 3), np.uint8)
            opening = cv2.morphologyEx(fgthres, cv2.MORPH_OPEN, kernel)
            im2, cnts, hierarchy = cv2.findContours(
                opening.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            bbox = []
            for c in cnts:
                if cv2.contourArea(c) > args.threshold:
                    x, y, w, h = cv2.boundingRect(c)
                    box = np.array([x, y, x+w, y+h, 1])
                    bbox.append(box)
                    cv2.rectangle(fgmask, (x, y), (x+w, y+h), (0, 255, 0), 2)

            np_bb = np.asarray(bbox)
            indices = non_max_suppression(np_bb, 0.7)
            bbox = [bbox[i] for i in indices]
            endbgs = time.time()

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
                    # correct coords
                    x1 = 0 if bbox_xyxy[val][0] < 0 else bbox_xyxy[val][0]
                    y1 = 0 if bbox_xyxy[val][1] < 0 else bbox_xyxy[val][1]
                    x2 = self.im_width - \
                        1 if bbox_xyxy[val][2] > self.im_width else bbox_xyxy[val][2]
                    y2 = self.im_height - \
                        1 if bbox_xyxy[val][3] > self.im_height else bbox_xyxy[val][3]

                    results["id"] = [str(int(identities[val]))]
                    # results["x1"] = [str(x1)]
                    # results["y1"] = [str(y1)]
                    # results["x2"] = [str(x2)]
                    # results["y2"] = [str(y2)]
                    results["fpx"] = [round((x2+x1)/2)]
                    results["fpy"] = [round(y2)]

                    for i in self.dwell_zones:
                        results[i["label"]] = [""]
                    for per_dwell_zone in self.dwell_zones:
                        if get_polygons(per_dwell_zone).contains(Point(round((x2+x1)/2), round(y2))):
                            results[per_dwell_zone["label"]] = True
                    # print (df)
                    df = df.append(pd.DataFrame.from_dict(results))
                ori_im = draw_bboxes(
                    ori_im, bbox_xyxy, identities, offset=(xmin, ymin))
            trackend = time.time()

            dfstart = time.time()
            df = df.reset_index(drop=True)
            stats_uuid = "./data/" + self.cam_uuid + "_stats.json"
            df.to_json(stats_uuid, orient='records')

            # do_count_rest(self.cam_uuid)
            dfend = time.time()

            visstart = time.time()
            if args.visualization:
                if self.dwell_zones != None:
                    ori_im = draw_zones(self.dwell_zones, ori_im)
                if self.count_lines != None:
                    ori_im = draw_lines(self.count_lines, ori_im)


            if False:
                cv2.imwrite("./data/" + str(self.cam_uuid) + "_" +
                            str(self.frame_count) + ".jpg", ori_im)

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
            # print()
            time_end_frame = time.time()

            sync_time = 1/self.vdo.get(cv2.CAP_PROP_FPS) - \
                (time_end_frame - time_current_frame)
            if (sync_time > 0):
                time.sleep(sync_time)

            bgsfps = 1 / (endbgs - startbgs)
            trackfps = 1 / (trackend - trackstart)
            bgstrack = 1 / (trackend - startbgs)
            dffps = 1 / (dfend - dfstart)
            visfps = 1/(visend-visstart)
            finalfps = 1 / (time_end_frame - time_current_frame)
            
            print("frame {}".format(self.frame_count), \
                "fps bgs: {0:.0f}".format(bgsfps), \
                    "track: {0:.0f}".format(trackfps), \
                        "e2e: {0:.0f}".format(bgstrack), \
                            "df: {0:.0f}".format(dffps), \
                                "vis: {0:.0f}".format(visfps), \
                                    "final: {0:.2f}".format(finalfps), \
                                        "sleeping: {0:.2f}".format(sync_time))

            with open("./data/" + self.cam_uuid + ".log", 'a') as the_file:
                the_file.write(str(int(bgsfps))+","+str(int(trackfps))+","+str(int(bgstrack))+","+str(int(dffps))+","+str(int(visfps))+","+str(int(finalfps)) + "\n")


