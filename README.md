# video_analytics

docker run -dit -p 5000:8097 -p 8000:8000 -v /home/test/project/data/:/opt/data/ video-analytics:test

docker exec -it boring_pasteur bash -c "python3 demo.py --input=/opt/data/Dwell_185.mp4 --mode=0 --visualization=1 --stats=1"

POST localhost:8000/setzone key-zone

GET localhost:8000/getcount 

```
    parser.add_argument( "--input"   ,type=str, help="path to video",required=True)
    parser.add_argument( "--visualization"   ,type=bool, help="displays live visualized output detections and tracking in a visdom",default=True)
    parser.add_argument( "--zones"   ,type=str, help="path to zones files")
    parser.add_argument( "--stats"   ,type=bool, help="set true for computing zones information like count and dwell",default=False)
    parser.add_argument( "--threshold"   ,type=int, help="Area in pixel to which the less sized box are removed as noise",default=100)
    parser.add_argument( "--mode"   ,type=int, help="Area in pixel to which the less sized box are removed as noise",default=2)
    parser.add_argument( "--output"   ,type=str, help="csv output file name",default="./data/stats.json")
    
```
