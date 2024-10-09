from datetime import datetime, timedelta

from flask import Flask, render_template, Response, jsonify
import mysql.connector
import cv2

app = Flask(__name__)

# Configure MySQL connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'raqeebdb'


def get_db_connection():
    connection = mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    return connection


@app.route('/')
def home():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Retrieve camera information
    cursor.execute('SELECT HallName, CameraID FROM hall WHERE EventID=1')
    camera_data = cursor.fetchall()

    detailed_camera_data = []

    for camera in camera_data:
        camera_id = camera['CameraID']
        # Retrieve all information for each CameraID
        cursor.execute(f'SELECT * FROM camera WHERE CameraID="{camera_id}"')
        camera_info = cursor.fetchall()

        for info in camera_info:
            rtsp_link = f"rtsp://{info['CameraUsername']}:{info['CameraPassword']}@{info['CameraIPAddress']}:{info['PortNo']}/{info['StreamingChannel']}"
            detailed_camera_data.append({
                'HallName': camera['HallName'],
                'CameraID': camera_id,
                'rtsp_link': rtsp_link,
            })

    cursor.close()
    connection.close()

    # Pass the camera data to the template
    return render_template('dashboard.html', cameras=detailed_camera_data)


@app.route('/get_static_data', methods=['GET'])
def get_data():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Retrieve event information:
    cursor.execute('SELECT * FROM events WHERE EventID=1')
    event_data = cursor.fetchall()

    # Convert datetime and timedelta to string for JSON serialization
    for row in event_data:
        for key, value in row.items():
            if isinstance(value, (datetime, timedelta)):
                row[key] = str(value)  # Convert to string

    # Retrieve camera information
    cursor.execute('SELECT HallID, HallName, CameraID FROM hall WHERE EventID=1')
    camera_data = cursor.fetchall()

    # Prepare a list to hold all camera details
    detailed_camera_data = []

    
    numOfHalls = len(camera_data) #count the number of halls

    for camera in camera_data:
        camera_id = camera['CameraID']
        # Retrieve all information for each CameraID
        cursor.execute(f'SELECT * FROM camera WHERE CameraID="{camera_id}"')
        camera_info = cursor.fetchall()

        # Append the hall name and corresponding camera info to the detailed list
        for info in camera_info:
            rtsp_link = f"rtsp://{info['CameraUsername']}:{info['CameraPassword']}@{info['CameraIPAddress']}:{info['PortNo']}/{info['StreamingChannel']}"
            detailed_camera_data.append({
                 'HallName': camera['HallName'],
                 'CameraID': camera_id,
                 'CameraIPAddress': info['CameraIPAddress'],
                 'PortNo': info['PortNo'],
                 'StreamingChannel': info['StreamingChannel'],
                 'CameraUsername': info['CameraUsername'],
                 'CameraPassword': info['CameraPassword'],
                 'cameraName': info['cameraName'],
                 'rtsp_link' : rtsp_link,
                 'numOfHalls' : numOfHalls,
            })

    cursor.close()
    connection.close()

    return jsonify({
        'event': event_data,
        'cameras': detailed_camera_data
    })


def generate_frames(rtsp_link):
    cap = cv2.VideoCapture(rtsp_link)
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            # Yield the frame as part of the video stream
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed/<camera_id>')
def video_feed(camera_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    # Retrieve RTSP link for the given camera_id
    cursor.execute(f'SELECT * FROM camera WHERE CameraID="{camera_id}"')
    camera_info = cursor.fetchone()
    rtsp_link = f"rtsp://{camera_info['CameraUsername']}:{camera_info['CameraPassword']}@{camera_info['CameraIPAddress']}:{camera_info['PortNo']}/{camera_info['StreamingChannel']}"

    cursor.close()
    connection.close()

    # Use the RTSP link to stream the video
    return Response(generate_frames(rtsp_link),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
