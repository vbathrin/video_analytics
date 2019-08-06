import json
import traceback
import os
from flask import request, Response
# from rest_api.api importfrom . import routes
from flask import Flask , send_file
from flask_cors import CORS, cross_origin
from stats.count import read_zones




app = Flask(__name__)
CORS(app)



import pandas as pd 

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

from stats.count import *
from datetime import datetime, timezone, date, timedelta


def do_dwell_rest(cam_uuid,time_interval,min_dwell):
    
    stats_file = "./data/" + cam_uuid + "_stats.json"
    zone_file = "./data/" + cam_uuid + "_zone.json"
    if os.path.isfile(zone_file):
        with open(zone_file, mode='r') as zone_json:
            zones = json.loads(zone_json.read())
            (dwell_zones, count_zones, _) = read_zones(zones)
    else:
        return("Error file not found", zone_file)

    if not os.path.isfile(stats_file):
        return("Error file not found", stats_file)

    json_output = {}
    json_output['sensor-info'] = {}
    json_output['status'] = {}
    json_output['sensor-time'] = {}
    json_output['content'] = {}

    utc_dt = datetime.now(timezone.utc)
    json_output['sensor-time']["time"] = str(utc_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
    json_output['sensor-time']["timezone"] = str("UTC")
    json_output['status']["code"] = str("OK")

    # print (json_output)

    # df = pd.read_json(stats_file)
    df = pd.read_json(stats_file,orient='records')
    # df = df.sort_index()
    # print(df)

    # Filter dataset for what is needed
    if df.empty != True:
        filtered_df = df.groupby('id').filter(lambda x : len(x)>3)
    
    counter = 0
    element_array = []
    for i in count_zones + dwell_zones:
        element = {}
        element["element-id"] = i["label"]
        element["measurement"] = {}
        current_timestamp = datetime.now().timestamp()
        
        dwell_array = []
        if df.empty != True:
            if filtered_df.empty != True:
                element["measurement"] = []
                element["element-name"] = i["label"]
                element["data-type"] = "ZONE"
                element["resolution"] = str(time_interval) + "_MINUTES"
                element["sensor-type"] = "SINGLE_SENSOR"
                element["from"] = str(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(current_timestamp - 60*time_interval)))
                element["to"] = str(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(current_timestamp)))
                mask = (filtered_df['epoch'] > current_timestamp - 60*time_interval) & (filtered_df['epoch'] <= current_timestamp)
                time_restricted_df = filtered_df.loc[mask]
                relevent_df = time_restricted_df.loc[(time_restricted_df[i["label"]] == True)]
                counter = len(relevent_df["id"].unique())
                print ("count -- " , counter)
                if counter > 0:
                    grouped_df = relevent_df.groupby('id')
                    for group_name, df_id in grouped_df:
                        # print(df_id)
                        # print ("name",group_name,df_id["epoch"].max() - df_id["epoch"].min())
                        dwell_array.append(df_id["epoch"].max() - df_id["epoch"].min())
                        np_dwell = np.array(dwell_array)
                    filtered_dwell = np_dwell[np_dwell > min_dwell]
                    avg_dwell = np.average(filtered_dwell)
                    print ("avg_dwell -- " , avg_dwell)
                    dwell_count = filtered_dwell.size
                else:
                    avg_dwell = 0
                    
                per_interval = {}
                per_interval["from"] = str(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(current_timestamp - 60*time_interval)))
                per_interval["to"] = str(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(current_timestamp)))
                per_interval["value"]= []
                print(per_interval)

                dwell_counter_value = {}
                dwell_counter_value["value"] = str(dwell_count)
                dwell_counter_value["label"] = "count"
                dwell_value = {}
                dwell_value["value"] = str(avg_dwell)
                dwell_value["label"] = "stat"
                print(dwell_counter_value)
                print(dwell_value)
                per_interval["value"].append(dwell_counter_value)
                per_interval["value"].append(dwell_value)
                

                element["measurement"].append(per_interval)
                print(element)
                element_array.append(element)
        
    json_output['content']['element'] = element_array
    return(json_output)



@app.route('/')
def health():
    return 'ok'


@app.route('/setzone', methods=['POST'])
def set_zone():
    try:
        current_zone = request.files['zone'].read()
        cam_uuid = request.form["uuid"]
        zones = json.loads(current_zone.decode('utf-8'))
        zone_file = "./data/" + cam_uuid + "_zone.json"
        with open(zone_file, 'w') as outfile:
            json.dump(zones, outfile)
        return (json.dumps("updated ZONE"), 200, {'Content-Type': 'application/json'})

    except Exception as e:
      
        return json.dumps(e), 500, {'ContentType': 'application/json'}




@app.route('/getdwell', methods=['GET'])
def get_dwell():
    try:
        cam_uuid = request.form["uuid"]
        time_interval = int(request.form["time_interval"])
        min_dwell = int(request.form["min_dwell"])
        
        json_count_zones = do_dwell_rest(cam_uuid,time_interval,min_dwell)
        
        return (json.dumps(json_count_zones), 200, {'Content-Type': 'application/json'})

    except Exception as e:
        return json.dumps(e), 500, {'ContentType': 'application/json'}



@app.route('/getcount', methods=['GET'])
def get_count():
    try:
        cam_uuid = request.form["uuid"]
        time_interval = int(request.form["time_interval"])
        min_dwell = int(request.form["min_dwell"])

        json_count_zones = do_count_rest(cam_uuid,time_interval,min_dwell)
        
        return (json.dumps(json_count_zones), 200, {'Content-Type': 'application/json'})

    except Exception as e:
        return json.dumps(e), 500, {'ContentType': 'application/json'}




@app.route('/get_info', methods=['GET'])
def get_camera_uuid():
    try:
        camera_uuid_file = "./data/camera_uuid.csv"
        camera_df = pd.read_csv(camera_uuid_file,index_col=None,header=None)
        camera_df.columns = ["uuid","video_source"]
        # print (camera_df) 
        return (camera_df.to_json(orient='records'), 200, {'Content-Type': 'application/json'})

    except Exception as e:
        return json.dumps(e), 500, {'ContentType': 'application/json'}


@app.route('/getheatmap', methods=['GET'])
def get_heatmap():
    try:

        return (send_file("../data/heat.jpg", mimetype='image/jpeg'))

    except Exception as e:
      
        return json.dumps(e), 500, {'ContentType': 'application/json'}

