[![Build Status](https://travis-ci.org/liambuchanan/fseventwatcher.svg?branch=master)](https://travis-ci.org/liambuchanan/fseventwatcher) [![Coverage Status](https://coveralls.io/repos/liambuchanan/fseventwatcher/badge.svg?branch=master&service=github)](https://coveralls.io/github/liambuchanan/fseventwatcher?branch=master)

# fseventwatcher

A supervisor event listener which listens to `TICK*` events.

If any file system events occur at the given path between ticks, the specified processes will be restarted.

## Usage
```shell
fseventwatcher.py --help
usage: fseventwatcher [-h] [-p [PROGRAM [PROGRAM ...]]] [-a] -f PATH
                      [PATH ...] [-r]
                      [--watched-events [{moved,created,deleted,modified} [{moved,created,deleted,modified} ...]]]
                      [--dither DITHER_MAX]

Supervisor TICK event listener which restarts processes if file system changes
occur between ticks.

optional arguments:
  -h, --help            show this help message and exit
  -p [PROGRAM [PROGRAM ...]], --programs [PROGRAM [PROGRAM ...]]
                        Supervisor process name/s to be restarted if in
                        RUNNING state.
  -a, --any-program     Restart any supervisor processes in RUNNING state.
  -f PATH [PATH ...], --paths PATH [PATH ...]
                        Path to watch for file system events.
  -r, --recursive       Watch path/s recursively.
  --watched-events [{moved,created,deleted,modified} [{moved,created,deleted,modified} ...]]
                        Watch file system for specified events (by default all
                        events will be watched).
  --dither DITHER_MAX   Add dither before restarting processes.
```
