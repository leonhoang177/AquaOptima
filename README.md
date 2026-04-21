# AquaOptima: Multi-Species Aquaculture Optimization

## A nested bio-inspired simulation model designed to optimize multi-species aquaculture environments.

## Overview

### This project applies a combination of Evolutionary Algorithms (EA) and Particle Swarm Optimization (PSO) to address a real-world problem in the fish production industry. By inputting a target fish population and diversity metrics, the system automatically outputs the precise environmental parameters required to sustain that ecosystem.

## Architecture

### The system utilizes a nested algorithmic approach to handle both micro-behaviors and macro-environmental factors:

#### Inner Loop (PSO): Simulates dynamic fish foraging and localized swarm/group behavior within the tank.

#### Outer Loop (EA): Evaluates and evolves the overall tank conditions and environmental parameters based on the fitness and survival rates derived from the inner PSO simulation.

## Academic Context

### This repository was developed as a final research project for CS 420/CS 527. It explores the application of bio-inspired algorithms to a novel domain, specifically testing the viability and performance of nested EA/PSO architectures in complex ecological modeling.
