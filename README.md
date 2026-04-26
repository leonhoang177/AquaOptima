# AquaOptima: Multi-Species Aquaculture Optimization

## Overview

We want to optimize the environment for Largemouth Bass Aquaculture. The project simulates
the lifetime a swarm in many 2D near-realistic ponds.
The PSO help the fishes surive in the given pond, while the EA select the best pond that yields
the the swarm with highest survival rate, best health condition and and using cheapest policies.

## Run Leon's Branch

To run the compiled simulation:

1.

```bash
python -m http.server 8000
```

2. Open: http://localhost:8000/visuals/index.html

To compile your own simulation, edit constants on `./core/constants.py` and run:

```bash
python core/run.py
```
