import numpy as np
import cv2
import pandas as pd
from scipy.ndimage import gaussian_filter

def add_heat(data, base_image):
    
    df = pd.DataFrame()
    # df = df.from_dict(data)
    df = pd.read_json(data)

    heat_image = np.zeros((base_image.shape),dtype=float)
    # heat_image[:,:,2] = 255
    for index, item in df.data.items():
        if bool(item):
            # print (item)
            for boxes in item:
                x1 = int(float(boxes['x1']))
                y1 = int(float(boxes['y1']))
                x2 = int(float(boxes['x2']))
                y2 = int(float(boxes['y2']))
                # print (x,y,w,h)
                heat_image[round(y2),round((x2+x1)/2),:] = heat_image[round(y2),round((x2+x1)/2),:] + 1
                
                # heat_image[y,x,:] = 25
    heat_image = gaussian_filter(heat_image, sigma=10)            
    heat_image *= 255.0/heat_image.max()   
    imC = cv2.applyColorMap(heat_image.astype(np.uint8), cv2.COLORMAP_RAINBOW)
    overlay = cv2.addWeighted(base_image,0.7,imC,0.7,0)

    cv2.imwrite("data/heat.jpg",cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    # heat_image = base_image
    return(overlay)
