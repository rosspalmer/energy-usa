#!/bin/bash

action=$1

if [ "$action" == "start" ]; then
    nohup uv run uvicorn energy_usa.main:app --reload > uvicorn.log 2>&1 &
elif [ "$action" == "stop" ]; then
    pkill -f "uvicorn energy_usa.main:app"
elif [ "$action" == "restart" ]; then
    pkill -f "uvicorn energy_usa.main:app"
    nohup uv run uvicorn energy_usa.main:app --reload > uvicorn.log 2>&1 &
fi