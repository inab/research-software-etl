#!/bin/bash

parallel bash ::: scripts/evaluation/inference_scripts/*.sh
