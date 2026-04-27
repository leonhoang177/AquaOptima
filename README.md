# AquaOptima: Multi-Species Aquaculture Optimization

## Overview

We want to optimize the environment for Largemouth Bass Aquaculture. The project simulates
the lifetime a swarm in many 2D near-realistic ponds.
The PSO help the fishes surive in the given pond, while the EA select the best pond that yields
the the swarm with highest survival rate, best health condition and and using cheapest policies.

## Running

To run the demo simulation:

1. Copy and Rename `./logs/simulation_data_demo.json` to `./logs/simulation_data.json`

2.

```bash
python -m http.server 8000
```

3. Open: http://localhost:8000/visuals/index.html

To compile your own simulation, edit constants on `./core/constants.py` and run:

```bash
python core/run.py
```
