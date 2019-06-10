# video_analytics

Command to get the docker initialized 
```docker run -dit -p 5000:8097 -p 8000:8000 -v /home/test/project/data/:/opt/data/ itoiretail/analytics:v4```

Command to check the name of the docker that is running 
```docker ps ```

Command to trigger a video or a RTSP link
```docker exec -it boring_pasteur bash -c "python3 demo.py --input=/opt/data/Dwell_185.mp4 --mode=0 --visualization=1 --stats=1" ```

postman collection in here - https://www.getpostman.com/collections/88574ec6eb19aa50c998

Quick Help for the parameters:
```
    parser.add_argument( "--input"   ,type=str, help="path to video",required=True)
    parser.add_argument( "--visualization"   ,type=bool, help="displays live visualized output detections and tracking in a visdom",default=True)
    parser.add_argument( "--zones"   ,type=str, help="path to zones files")
    parser.add_argument( "--stats"   ,type=bool, help="set true for computing zones information like count and dwell",default=False)
    parser.add_argument( "--threshold"   ,type=int, help="Area in pixel to which the less sized box are removed as noise",default=100)
    parser.add_argument( "--mode"   ,type=int, help="modes changes with the processing size of the image 0-original 1-640*480, 2-480*320, 3-320*240, ",default=2)
    parser.add_argument( "--output"   ,type=str, help="csv output file name",default="./data/stats.json")
    
```
