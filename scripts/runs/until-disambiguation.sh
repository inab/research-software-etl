#!/bin/bash
rsetl run-transformation --sources github 
rsetl run --from-stage grouping --until disambiguation --remove-opeb-metrics --tag pre-annotation 