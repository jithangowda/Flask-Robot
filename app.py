# app.py
from flask import Flask, render_template, jsonify
import socket
import threading
import time

app = Flask(__name__)

esp_connected = False
espcam_connected = False
stop_broadcast = False
log_messages = []

def log(msg):
    timestamp = time.strftime("[%H:%M:%S]", time.localtime())
    entry = f"{timestamp} {msg}"
    log_messages.append(entry)
    if len(log_messages) > 50:
        log_messages.pop(0)
    print(entry)

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

def udp_broadcast(ip, port=4210):
    global stop_broadcast
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while not stop_broadcast:
        msg = f"SERVER_IP:{ip}"
        udp.sendto(msg.encode(), ('<broadcast>', port))
        log(f"[UDP] Broadcasting IP: {msg}")
        time.sleep(3)

def listen_for_connections():
    global esp_connected, espcam_connected, stop_broadcast
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.bind(('0.0.0.0', 4211))
    while True:
        data, addr = udp.recvfrom(1024)
        message = data.decode()
        log(f"[UDP] Received from {addr}: {message}")

        if message == "ESP Connected":
            esp_connected = True
            log("[Server] ESP32 connected.")
        elif message == "ESP-CAM Connected":
            espcam_connected = True
            log("[Server] ESP32-CAM connected.")

        if esp_connected and espcam_connected:
            log("[Server] ✅✅ Both devices connected. Stopping UDP broadcast.")
            stop_broadcast = True
            break

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/status")
def status():
    return jsonify({
        "esp": esp_connected,
        "espcam": espcam_connected
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
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # ✅ allow broadcast
    udp.sendto(cmd.encode(), ("<broadcast>", 4212))
    log(f"[UDP] Sent command: {cmd}")
    return jsonify({"status": "sent", "command": cmd})


if __name__ == "__main__":
    ip = get_ip()
    log(f"[Flask] Running on http://{ip}:5000")
    threading.Thread(target=udp_broadcast, args=(ip,), daemon=True).start()
    threading.Thread(target=listen_for_connections, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)

    

