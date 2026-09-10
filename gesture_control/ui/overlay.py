import cv2
import numpy as np

CONNECTIONS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
               (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
               (13,17),(0,17),(17,18),(18,19),(19,20)]


def draw(frame, hands, engine, fps, now, message=None):
    height, width = frame.shape[:2]
    color = (80, 220, 100) if engine.sink.enabled else (80, 80, 240)
    if engine.sink.enabled and engine.state.name == 'POTENTIAL_GESTURE': color = (0,190,255)
    if engine.sink.enabled and engine.state.name == 'IDLE': color = (190,180,150)
    x1,y1,x2,y2 = engine.c.interaction_region
    cv2.rectangle(frame, (int(x1*width),int(y1*height)), (int(x2*width),int(y2*height)), (180,160,70), 1)
    cv2.line(frame, (0,int(engine.c.tab_zone_y*height)), (width,int(engine.c.tab_zone_y*height)), (170,120,170), 1)
    for hand in hands:
        pixels = (hand.points[:, :2]*[width,height]).astype(int)
        for a,b in CONNECTIONS: cv2.line(frame, tuple(pixels[a]), tuple(pixels[b]), (150,150,150), 1)
        for i, p in enumerate(pixels):
            cv2.circle(frame, tuple(p), 4 if i in (4,8,12,16,20) else 2, color, -1)
        label = f'{hand.label} {hand.confidence:.2f} pinch {hand.pinch:.2f}'
        cv2.putText(frame, label, tuple(pixels[0]), cv2.FONT_HERSHEY_SIMPLEX, .42, color, 1)
    if engine.circle.points:
        aspect = width/height
        path = (np.array(engine.circle.points)*[width,height*aspect]).astype(np.int32)
        cv2.polylines(frame,[path],False,(0,220,255),2)
    status = 'ENABLED' if engine.sink.enabled else 'PAUSED - '+engine.c.resume_hotkey
    output_mode = 'CALIBRATION' if message else ('DRY RUN - no OS actions' if engine.sink.dry_run else 'REAL CONTROL')
    lines = [f'{output_mode} | {fps:.1f} FPS | {status}',
             f'{engine.mode or "IDLE"} / {engine.state.name} / {engine.confidence:.2f}',
             'G: enable (preview focused) | Esc: pause | F12: quit']
    event, timestamp = engine.sink.last_event
    if event.startswith('VOLUME') and now-timestamp < 1.2: lines.append(event.replace('_',' '))
    if message: lines.extend(message)
    for i, line in enumerate(lines):
        y = 20+i*22
        cv2.putText(frame,line,(10,y),cv2.FONT_HERSHEY_SIMPLEX,.46,(0,0,0),3)
        cv2.putText(frame,line,(10,y),cv2.FONT_HERSHEY_SIMPLEX,.46,color,1)
    if engine.target:
        point = (int(engine.target[0]/engine.screen[0]*width), int(engine.target[1]/engine.screen[1]*height))
        cv2.drawMarker(frame,point,(255,200,50),cv2.MARKER_CROSS,12,1)
    return frame
