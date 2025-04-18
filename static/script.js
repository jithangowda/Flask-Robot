function updateStatus() {
  fetch("/status")
    .then((res) => res.json())
    .then((data) => {
      const esp = document.getElementById("esp-circle");
      const espcam = document.getElementById("espcam-circle");

      esp.classList.toggle("connected", data.esp);
      espcam.classList.toggle("connected", data.espcam);

      document.getElementById("esp-label").innerText = `ESP32: ${
        data.esp ? "Connected" : "Not Connected"
      }`;
      document.getElementById("espcam-label").innerText = `ESP32-CAM: ${
        data.espcam ? "Connected" : "Not Connected"
      }`;
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
