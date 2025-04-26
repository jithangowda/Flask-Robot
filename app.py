from flask import Flask, render_template, jsonify, request, Response
import socket
import threading
import time
import cv2
import torch
from ultralytics import YOLO
import numpy as np

model = YOLO('best.pt')
model.eval()

app = Flask(__name__)


esp_connected = False
esp8266_connected = False
espcam_connected = False
stop_broadcast = False
log_messages = []
espcam_ip = None

stream_active = False


def log(msg):
    timestamp = time.strftime("[%H:%M:%S]", time.localtime())
    entry = f"{timestamp} {msg}"
    log_messages.append(entry)
    if len(log_messages) > 50:
        log_messages.pop(0)
    print(entry, flush=True)


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


def udp_broadcast(ip, port=4210):  # 4210 is connection port
    global stop_broadcast
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while not stop_broadcast:
        msg = f"SERVER_IP:{ip}"
        udp.sendto(msg.encode(), ('<broadcast>', port))
        log(f"[UDP] Broadcasting IP: {msg}")
        time.sleep(3)


def listen_for_connections():
    global esp_connected, esp8266_connected, espcam_connected, stop_broadcast, espcam_ip, stream_active
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.bind(('0.0.0.0', 4211))
    while True:
        data, addr = udp.recvfrom(1024)
        message = data.decode()
        log(f"[UDP] Received from {addr}: {message}")

        if message == "ESP Connected":
            esp_connected = True
            log("[Server] ESP32 connected.")

        elif message == "ESP8266 Connected":
            esp8266_connected = True
            log("[Server] ESP8266 connected.")

        elif message == "ESP-CAM Connected":
            espcam_connected = True
            espcam_ip = addr[0]
            log(f"[Server] ESP32-CAM connected with IP: {espcam_ip}")
            stream_active = True  

        if esp_connected and espcam_connected and esp8266_connected:
            log("[Server] ✅✅✅ All devices connected. Sending notification...")
            # Send UDP message to notify devices
            udp_notify = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_notify.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_notify.sendto("ALL_CONNECTED".encode(), ("<broadcast>", 4213))  # 4213 is for notification to 8266
            log("[Server] ALL_CONNECTED")
            stop_broadcast = True
            break


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def status():
    return jsonify({
        "esp": esp_connected,
        "esp8266": esp8266_connected,
        "espcam": espcam_connected,
        "espcam_ip": espcam_ip
    })


@app.route("/logs")
def logs():
    return jsonify({"logs": log_messages})


@app.route("/command/<cmd>")
def send_command(cmd):
    if not esp_connected:
        return jsonify({"status": "ESP not connected"}), 400

    # Map the command to the correct format
    if cmd == "w":
        cmd = "forward"
    elif cmd == "s":
        cmd = "backward"
    elif cmd == "a":
        cmd = "left"
    elif cmd == "d":
        cmd = "right"
    elif cmd == " ":
        cmd = "stop"

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.sendto(cmd.encode(), ("<broadcast>", 4212))  # 4212 is port for commands
    log(f"[UDP] Sent command: {cmd}")
    return jsonify({"status": "sent", "command": cmd})


@app.route("/slider", methods=["POST"])
def handle_slider():
    if not esp8266_connected:
        return jsonify({"status": "ESP8266 not connected"}), 400

    data = request.get_json()
    pan = data.get("pan")  # Only extract the "pan" value

    if pan is None:
        return jsonify({"status": "Invalid data"}), 400

    # Format the message as "PAN:<value>"
    msg = f"PAN:{pan}"

    # Send the message to the ESP8266 via UDP
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.sendto(msg.encode(), ("<broadcast>", 4212))  # 4212 is the control port
    log(f"[UDP] Sent slider data: {msg}")

    return jsonify({"status": "sent", "pan": pan})


def generate_frames():
    global espcam_ip, stream_active
    while True:
        if stream_active and espcam_ip:
            try:
                cap = cv2.VideoCapture(f"http://{espcam_ip}/stream")
                while stream_active:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    
                    results = model(frame) 

                   
                    annotated_frame = results[0].plot()  

                    
                    ret, buffer = cv2.imencode('.jpg', annotated_frame)
                    frame_bytes = buffer.tobytes()

                
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                cap.release()
            except Exception as e:
                log(f"[Stream] Error: {e}")
                time.sleep(1)
        else:
            time.sleep(1)


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    ip = get_ip()
    log(f"[Flask] Running on http://{ip}:5000")
    threading.Thread(target=udp_broadcast, args=(ip,), daemon=True).start()
    threading.Thread(target=listen_for_connections, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)