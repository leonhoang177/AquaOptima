# AquaOptima: Multi-Species Aquaculture Optimization

## A nested bio-inspired simulation model designed to optimize multi-species aquaculture environments.

## Overview

### This project applies a combination of Evolutionary Algorithms (EA) and Particle Swarm Optimization (PSO) to address a real-world problem in the fish production industry. By inputting a target fish population and diversity metrics, the system automatically outputs the precise environmental parameters required to sustain that ecosystem.

## Architecture

### The system utilizes a nested algorithmic approach to handle both micro-behaviors and macro-environmental factors:

#### Inner Loop (PSO): Simulates dynamic fish foraging and localized swarm/group behavior within the tank.

#### Outer Loop (EA): Evaluates and evolves the overall tank conditions and environmental parameters based on the fitness and survival rates derived from the inner PSO simulation.

## How to Run the Simulation

This project uses a hybrid architecture: a Python engine for the heavy algorithmic computation and an HTML/JavaScript frontend for the visualization.

### Prerequisites

- Python 3.x
- A modern web browser (Chrome, Firefox, Safari)

### Execution Steps

#### 1. Go the example folder

```bash
cd ./example
```

#### 2. Generate the Swarm Data

First, run the Python engine to execute the Evolutionary Algorithm (EA) and Particle Swarm Optimization (PSO). This will calculate the optimal traits and export the final simulation frames to a JSON file.

```bash
python main.py
```

#### 3. Start a Local Web Server

To view the animation, you need to serve the files locally to comply with browser CORS (Cross-Origin Resource Sharing) security policies. Run the following command in the same directory:

```bash
python -m http.server 8000
```

#### 4. View the Visualization

Open your web browser and navigate to `http://localhost:8000`

## Academic Context

### This repository was developed as a final research project for CS 420/CS 527. It explores the application of bio-inspired algorithms to a novel domain, specifically testing the viability and performance of nested EA/PSO architectures in complex ecological modeling.
