# AquaOptima: Multi-Species Aquaculture Optimization

## Overview

We want to optimize the environment for Largemouth Bass Aquaculture. The project simulates
the lifetime a swarm in many 2D near-realistic ponds.
The PSO help the fishes surive in the given pond, while the EA select the best pond that yields
the the swarm with highest survival rate, best health condition and and using cheapest policies.

## Run Leon's Branch

```bash
cd ./leon
python simulation.py
python plot.py
python -m http.server 8000
```

Open http://localhost:8000/visualization.html
