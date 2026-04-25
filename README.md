# AquaOptima: Multi-Species Aquaculture Optimization

## Overview

We want to optimize the environment for Largemouth Bass Aquaculture. The project simulates
the lifetime a swarm in many 2D near-realistic ponds.
The PSO help the fishes surive in the given pond, while the EA select the best pond that yields
the the swarm with highest survival rate, best health condition and and using cheapest policies.

## Run Leon's Branch

Note:

- Use `simulation_demo.py` for quick run
- Use `simulation_real.py` for realistic run (take 20 minutes to run)
- Feel free to adjust the params in the simulation code to tune it

Run:

```bash
cd ./leon
python run.py
python -m http.server 8000
```

Open: http://localhost:8000/visualization.html
