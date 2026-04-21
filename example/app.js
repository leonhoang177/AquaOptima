const canvas = document.getElementById("tankCanvas");
const ctx = canvas.getContext("2d");
const infoDiv = document.getElementById("info");

let frames = [];
let metadata = {};
let currentFrame = 0;

// Load the JSON data exported by Python
fetch("swarm_data.json")
  .then((response) => response.json())
  .then((data) => {
    frames = data.frames;
    metadata = data.metadata;

    // Display the evolved traits on the webpage
    const t = metadata.traits;
    infoDiv.innerHTML = `<strong>Optimized Traits:</strong> Inertia: ${t[0].toFixed(2)} | Cognitive: ${t[1].toFixed(2)} | Social: ${t[2].toFixed(2)} | Radius: ${t[3].toFixed(2)}`;

    animate(); // Start the loop
  })
  .catch((err) => {
    infoDiv.innerHTML =
      "Error loading swarm_data.json. Are you running a local server?";
    console.error(err);
  });

function drawFish(x, y, angle) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);

  // Draw fish shape (Triangle)
  ctx.fillStyle = "#f39c12";
  ctx.beginPath();
  ctx.moveTo(12, 0); // Nose
  ctx.lineTo(-8, 6); // Bottom fin
  ctx.lineTo(-8, -6); // Top fin
  ctx.fill();

  // Draw a small eye
  ctx.fillStyle = "white";
  ctx.beginPath();
  ctx.arc(4, -2, 1.5, 0, Math.PI * 2);
  ctx.fill();

  ctx.restore();
}

function animate() {
  // Clear previous frame
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Draw the food source
  ctx.fillStyle = "#27ae60";
  ctx.beginPath();
  ctx.arc(metadata.food_x, metadata.food_y, 10, 0, Math.PI * 2);
  ctx.fill();

  // Draw the swarm for the current frame
  const currentSwarm = frames[currentFrame];
  currentSwarm.forEach((fish) => {
    drawFish(fish.x, fish.y, fish.angle);
  });

  // Advance frame (loop back to start if at the end)
  currentFrame = (currentFrame + 1) % frames.length;

  // Call the next frame
  requestAnimationFrame(animate);
}
