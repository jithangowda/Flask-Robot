function updateStatus() {
  fetch("/status")
    .then((res) => res.json())
    .then((data) => {
      const esp = document.getElementById("esp-circle");
      const esp8266 = document.getElementById("esp8266-circle");
      const espcam = document.getElementById("espcam-circle");

      esp.classList.toggle("connected", data.esp);
      esp8266.classList.toggle("connected", data.esp8266);
      espcam.classList.toggle("connected", data.espcam);

      document.getElementById("esp-label").innerText = `ESP32: ${
        data.esp ? "Connected" : "Not Connected"
      }`;
      document.getElementById("esp8266-label").innerText = `ESP8266: ${
        data.esp8266 ? "Connected" : "Not Connected"
      }`;
      document.getElementById("espcam-label").innerText = `ESP32-CAM: ${
        data.espcam ? "Connected" : "Not Connected"
      }`;

      const connectingText = document.getElementById("connecting-text");
      if (data.espcam) {
        connectingText.style.display = "none";
      } else {
        connectingText.style.display = "block";
      }
    });
}

function updateLogs() {
  fetch("/logs")
    .then((res) => res.json())
    .then((data) => {
      const logDiv = document.getElementById("logs");
      logDiv.innerHTML = data.logs.map((l) => `<div>${l}</div>`).join("");
      logDiv.scrollTop = logDiv.scrollHeight;
    });
}

setInterval(() => {
  updateStatus();
  updateLogs();
}, 3000);

updateStatus();
updateLogs();

const commandMap = {
  "w-btn": "w",
  "a-btn": "a",
  "s-btn": "s",
  "d-btn": "d",
  "stop-btn": "stop",
};

function sendCommand(cmd) {
  fetch(`/command/${cmd}`);
}

Object.keys(commandMap).forEach((btnId) => {
  document.getElementById(btnId).addEventListener("click", () => {
    sendCommand(commandMap[btnId]);
  });
});

document.addEventListener("keydown", (e) => {
  const key = e.key.toLowerCase();
  if (["w", "a", "s", "d", " "].includes(key)) {
    const cmd = key === " " ? "stop" : key;
    sendCommand(cmd);

    const btnId = Object.keys(commandMap).find((id) => commandMap[id] === cmd);
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.classList.add("pressed");
      setTimeout(() => btn.classList.remove("pressed"), 150);
    }
  }
});

function sendSliderValues(tilt) {
  fetch("/slider", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ tilt: tilt }),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Tilt value sent:", data);
    })
    .catch((error) => {
      console.error("Error sending tilt value:", error);
    });
}

document.getElementById("tilt-slider").addEventListener("input", (event) => {
  const tilt = event.target.value;
  sendSliderValues(tilt);
});

function sendPanCommand(direction) {
  fetch("/pan", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ direction: direction }),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(`Pan direction sent: ${direction}`, data);
    })
    .catch((error) => {
      console.error("Error sending pan direction:", error);
    });
}

document.getElementById("pan-left-btn").addEventListener("mousedown", () => {
  sendPanCommand("left");
});

document.getElementById("pan-left-btn").addEventListener("mouseup", () => {
  sendPanCommand("stop");
});

document.getElementById("pan-right-btn").addEventListener("mousedown", () => {
  sendPanCommand("right");
});

document.getElementById("pan-right-btn").addEventListener("mouseup", () => {
  sendPanCommand("stop");
});
