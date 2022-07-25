# coding-practices-tutorial

This repo contains buggy code for controlling a Franka Panda arm with PD
control. Can you spot the bugs?

## Setup

This code works on Linux and MacOS. To get started, first install the pip
requirements in a virtualenv.
```sh
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## Running the code

This tutorial is split into two parts. For part 1, run:
```python
python3 robot_part_1.py --kp 49 --kd 14
```

For part 2, run:
```python
python3 robot_part_2.py --kp 49 --kd 14
```

You can change the PD gains by changing the `--kp` and `--kd` arguments.

The scripts use your browser for visualization. They will pause until you load
this page:

[http://localhost:8000](http://localhost:8000)
