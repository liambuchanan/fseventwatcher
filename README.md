[![Build Status](https://travis-ci.org/liambuchanan/fseventwatcher.svg?branch=master)](https://travis-ci.org/liambuchanan/fseventwatcher) [![Coverage Status](https://coveralls.io/repos/liambuchanan/fseventwatcher/badge.svg?branch=master&service=github)](https://coveralls.io/github/liambuchanan/fseventwatcher?branch=master)

fseventwatcher
--------------

A supervisor event listener which listens to `TICK*` events.

If any file system events occur at the given path between ticks, the specified processes will be restarted.
