import numpy as np
import cv2

import numpy as np
import pandas as pd

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon, LineString



COLORS_10 =[(144,238,144),(178, 34, 34),(221,160,221),(  0,255,  0),(  0,128,  0),(210,105, 30),(220, 20, 60),
            (192,192,192),(255,228,196),( 50,205, 50),(139,  0,139),(100,149,237),(138, 43,226),(238,130,238),
            (255,  0,255),(  0,100,  0),(127,255,  0),(255,  0,255),(  0,  0,205),(255,140,  0),(255,239,213),
            (199, 21,133),(124,252,  0),(147,112,219),(106, 90,205),(176,196,222),( 65,105,225),(173,255, 47),
            (255, 20,147),(219,112,147),(186, 85,211),(199, 21,133),(148,  0,211),(255, 99, 71),(144,238,144),
            (255,255,  0),(230,230,250),(  0,  0,255),(128,128,  0),(189,183,107),(255,255,224),(128,128,128),
            (105,105,105),( 64,224,208),(205,133, 63),(  0,128,128),( 72,209,204),(139, 69, 19),(255,245,238),
            (250,240,230),(152,251,152),(  0,255,255),(135,206,235),(  0,191,255),(176,224,230),(  0,250,154),
            (245,255,250),(240,230,140),(245,222,179),(  0,139,139),(143,188,143),(255,  0,  0),(240,128,128),
            (102,205,170),( 60,179,113),( 46,139, 87),(165, 42, 42),(178, 34, 34),(175,238,238),(255,248,220),
            (218,165, 32),(255,250,240),(253,245,230),(244,164, 96),(210,105, 30)]




def read_zones(zone_file):

    print("reading zones")
    dwell_zones = []
    count_lines = []

    for x in zone_file["shapes"]:
        if x["shape_type"] == "polygon":
            dwell_zones.append(x)
        if x["shape_type"] == "line":
            count_lines.append(x)
    return (dwell_zones, count_lines)


def get_polygons(x):
    if x["shape_type"] == "polygon":
        polygon = Polygon(x["points"])
        # print (polygon)
        polyx, polyy = polygon.exterior.coords.xy
        # test = zip(list(np.array(polyx)/(800/320)),list(np.array(polyy)/(600/240)))
        test = zip(list(np.array(polyx)/(800/480)),
                   list(np.array(polyy)/(600/320)))

        polygon_resize = Polygon(test)
        return(polygon_resize)

    if x["shape_type"] == "line":
        ls = LineString(x["points"])
        polyx, polyy = ls.xy
        # test = zip(list(np.array(polyx)/(800/320)),list(np.array(polyy)/(600/240)))
        test = zip(list(np.array(polyx)/(800/480)),
                   list(np.array(polyy)/(600/320)))

        polygon_resize = LineString(test)
        return(polygon_resize)


def check_point_inside(point, polygon):
    # print (point)
    # print(polygon)
    if polygon.contains(point["foot_point"]):
        return True


def draw_zones(dwell_zones, img, identity=None):
    for i in dwell_zones:
        polygon = get_polygons(i)
        cv2.polylines(img, np.int32([polygon.exterior.coords]), 1,(0,0,255), thickness=2)

        font = cv2.FONT_HERSHEY_SIMPLEX

        bottomLeftCornerOfText = (
            int(polygon.exterior.coords[0][0]), int(polygon.exterior.coords[0][1]))
        fontScale = 0.5
        fontColor = COLORS_10[0]
        lineType = 1

        cv2.putText(img, str(i["label"]),
                    bottomLeftCornerOfText,
                    font,
                    fontScale,
                    fontColor,
                    lineType)
    return img


def draw_lines(lines, img, identity=None):
    for i in lines:
        ls = get_polygons(i)
        if "bw" in i["label"]:
            cv2.line(img, (int(ls.xy[0][0]), int(ls.xy[1][0])), (int(ls.xy[0][1]), int(ls.xy[1][1])),(255,0,0),2)
        elif "fw" in i["label"]:  
            cv2.line(img, (int(ls.xy[0][0]), int(ls.xy[1][0])), (int(ls.xy[0][1]), int(ls.xy[1][1])),(0,255,0),2)
        else:
            cv2.line(img, (int(ls.xy[0][0]), int(ls.xy[1][0])), (int(ls.xy[0][1]), int(ls.xy[1][1])),(0,0,0),2)

        font = cv2.FONT_HERSHEY_SIMPLEX

        # bottomLeftCornerOfText = (int(polygon.exterior.coords[0][0]), int(polygon.exterior.coords[0][1]))
        # fontScale = 0.5
        # fontColor = COLORS_10[0]
        # lineType = 1

        # cv2.putText(img, str(i["label"]),
        #             bottomLeftCornerOfText,
        #             font,
        #             fontScale,
        #             fontColor,
        #             lineType)
    return img
    



def non_max_suppression(boxes, max_bbox_overlap, scores=None):
   
    if len(boxes) == 0:
        return []

    boxes = boxes.astype(np.float)
    pick = []

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2] + boxes[:, 0]
    y2 = boxes[:, 3] + boxes[:, 1]

    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    if scores is not None:
        idxs = np.argsort(scores)
    else:
        idxs = np.argsort(y2)

    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)

        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])

        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        overlap = (w * h) / area[idxs[:last]]

        idxs = np.delete(
            idxs, np.concatenate(
                ([last], np.where(overlap > max_bbox_overlap)[0])))

    return pick

def draw_bboxes(img, bbox, identities=None, offset=(0,0)):
    for i,box in enumerate(bbox):
        x1,y1,x2,y2 = [int(i) for i in box]
        x1 += offset[0]
        x2 += offset[0]
        y1 += offset[1]
        y2 += offset[1]
        # box text and bar
        id = int(identities[i]) if identities is not None else 0    
        color = COLORS_10[id%len(COLORS_10)]
        label = '{}'.format(id)
        t_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_PLAIN, 2 , 2)[0]
        cv2.rectangle(img,(x1, y1),(x2,y2),color,2)
        cv2.rectangle(img,(x1, y1),(x1+t_size[0]+3,y1+t_size[1]+4), color,-1)
        cv2.putText(img,label,(x1,y1+t_size[1]+4), cv2.FONT_HERSHEY_PLAIN, 1, [255,255,255], 2)
    return img
