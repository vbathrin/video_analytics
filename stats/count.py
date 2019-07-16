import numpy as np
import cv2
import pandas as pd
import datetime 
import time
from datetime import timedelta

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

from util import COLORS_10

def read_zones(zone_file):
    
    print("reading zones")
    dwell_zones = []
    count_zones = []
    for x in zone_file["shapes"]:
        if "entrance" in x["label"]:
            count_zones.append(x)
        if "dwell" in x["label"]:
            dwell_zones.append(x)
    return (dwell_zones, count_zones)


def do_count(data,count_zones):
    df = pd.read_json(data)
    temp_data = []
    temp = {}
    id_dict = {}
    all_ids = []
    counter = 0
    blacklist = []
    for index, item in df.data.items():
        if bool(item):
            for boxes in item:
                x1 = int(float(boxes['x1']))
                y1 = int(float(boxes['y1']))
                x2 = int(float(boxes['x2']))
                y2 = int(float(boxes['y2']))
                person_id = int(float(boxes['id']))

                # print (x,y,w,h)
                # temp["foot_point"] = Point(round(y2),round((x2+x1)/2))
                temp["foot_point"] = Point(round((x2+x1)/2),round(y2))

                temp["id"] = person_id
                temp_data.append(temp)
                # print (temp)
                for i in count_zones:
                    if check_point_inside(temp,get_polygons(i)):
                        if temp["id"] not in blacklist:
                            counter = counter + 1
                            blacklist.append(temp["id"])
                            i["counter"] = str(counter)
                            i["ids"] = str(blacklist)
                            
                            id_dict[person_id] = {}
                            id_dict[person_id]["start_time"] = str(df.time[index])
                            id_dict[person_id]["zone_name"] = i["label"]
                        else:
                            id_dict[person_id]["end_time"] = str(df.time[index])
    return(count_zones,id_dict)






def do_dwell(dwell_dict,dwell_zones):
    dwell_stats = {}
    # print(dwell_dict)
    dict_keys = dwell_dict.keys()
    time_list = []
    total_time = datetime.datetime.strptime("0:0:0.000000","%H:%M:%S.%f")
    for i in dwell_zones:
        for j in dict_keys:
            if dwell_dict[j]["zone_name"] == i["label"]:
                if "end_time" in dwell_dict[j]:
                    total_time = total_time + (datetime.datetime.strptime(dwell_dict[j]["end_time"],"%H:%M:%S.%f") - datetime.datetime.strptime(dwell_dict[j]["start_time"],"%H:%M:%S.%f"))
        if len(dict_keys) > 0:
            avg_dwell_time = (total_time.second)/len(dict_keys)
            dwell_stats[i["label"]] = {}
            dwell_stats[i["label"]]["avg_dwell_time"] = avg_dwell_time
    return(dwell_stats)


#TODO remove hard coded value for pass mode to here

def get_polygons(x):
    if x["shape_type"] == "polygon":
        polygon = Polygon(x["points"])
        # print (polygon)
        polyx, polyy = polygon.exterior.coords.xy
        # test = zip(list(np.array(polyx)/(800/320)),list(np.array(polyy)/(600/240)))
        test = zip(list(np.array(polyx)/(800/480)),list(np.array(polyy)/(600/320)))

        polygon_resize = Polygon(test)
        return(polygon_resize)
           
           
def check_point_inside(point,polygon):
    # print (point)
    # print(polygon)
    if polygon.contains(point["foot_point"]):
        return True

def draw_count_zones(count_zones,img,identity=None):
    # print (count_zones)
    for i in count_zones:
        polygon = get_polygons(i)
        cv2.polylines(img, np.int32([polygon.exterior.coords]), 1, color = COLORS_10[identity%len(COLORS_10)] if identity is not None else COLORS_10[0],thickness = 2)

        font = cv2.FONT_HERSHEY_SIMPLEX 	

        bottomLeftCornerOfText = (int(polygon.exterior.coords[0][0]), int(polygon.exterior.coords[0][1]))
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


def draw_dwell_zones(dwell_zones,img,identity=None):
    # print (dwell_zones)
    for i in dwell_zones:
        polygon = get_polygons(i)
        cv2.polylines(img, np.int32([polygon.exterior.coords]), 1, color = COLORS_10[identity%len(COLORS_10)] if identity is not None else COLORS_10[1],thickness = 2)

        font = cv2.FONT_HERSHEY_SIMPLEX 	

        bottomLeftCornerOfText = (int(polygon.exterior.coords[0][0]), int(polygon.exterior.coords[0][1]))
        fontScale = 0.5
        fontColor = COLORS_10[1]
        lineType = 1

        cv2.putText(img, str(i["label"]),
                    bottomLeftCornerOfText,
                    font,
                    fontScale,
                    fontColor,
                    lineType)    
    return img







        
