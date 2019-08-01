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


def do_count_rest(cam_uuid):
    
    stats_file = "./data/" + cam_uuid + "_stats.json"
    zone_file = "./data/" + cam_uuid + "_zone.json"
    if os.path.isfile(zone_file):
        with open(zone_file, mode='r') as zone_json:
            zones = json.loads(zone_json.read())
            (dwell, count_zones) = read_zones(zones)



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
    
    temp_data = []
    temp = {}
    id_dict = {}
    all_ids = []
    counter = 0
    blacklist = []
    element_array = []
    
    for i in count_zones:
        element = {}
        element["element-id"] = i["label"]
        element["measurement"] = {}
        current_timestamp = datetime.now().timestamp()
        
        dwell_array = []
        if df.empty != True:
            if filtered_df.empty != True:
                mask = (filtered_df['epoch'] > current_timestamp - 60) & (filtered_df['epoch'] <= current_timestamp)
                time_restricted_df = filtered_df.loc[mask]
                relevent_df = time_restricted_df.loc[(time_restricted_df[i["label"]] == True)]
                counter = len(relevent_df["id"].unique())
                print ("count -- " , counter)
                grouped_df = relevent_df.groupby('id')
                for group_name, df_id in grouped_df:
                    # print ("name",group_name,df_id["epoch"].max() - df_id["epoch"].min())
                    dwell_array.append(df_id["epoch"].max() - df_id["epoch"].min())
                    np_dwell = np.array(dwell_array)
                avg_dwell = np.average(np_dwell[np_dwell > 2])
                print ("avg_dwell -- " , avg_dwell)

                element["element-name"] = i["label"]
                element["data-type"] = "ZONE"
                element["resolution"] = "ONE_MINUTE"
                element["sensor-type"] = "SINGLE_SENSOR"
                element["from"] = str(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(current_timestamp - 60)))
                element["to"] = str(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(current_timestamp)))
                element["measurement"]["from"] = str(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(current_timestamp - 60)))
                element["measurement"]["to"] = str(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.localtime(current_timestamp)))
                element["measurement"]["value"]= []
                counter_value = {}
                counter_value["value"] = str(counter)
                counter_value["label"] = "count"
                dwell_value = {}
                dwell_value["value"] = str(avg_dwell)
                dwell_value["label"] = "stat"
                element["measurement"]["value"].append(counter_value)
                element["measurement"]["value"].append(dwell_value)


                element_array.append(element)
        
    json_output['content']['element'] = element_array
    return(json_output,id_dict)





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




@app.route('/getcount', methods=['GET'])
def get_count():
    try:
        cam_uuid = request.form["uuid"]
        count_zones,id_dict = do_count_rest(cam_uuid)
        
        return (json.dumps(count_zones), 200, {'Content-Type': 'application/json'})

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

