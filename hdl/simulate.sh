#! /usr/bin/env bash

if [ "$1" == "preplace" ]; then
	MAIN_V_FILE="./top.v"
elif [ "$1" == "pnr" ]; then
	MAIN_V_FILE="./pnrtop.v"
else
	echo "Please specify either 'preplace' or 'pnr'"
	exit 1
fi

echo "Simulating with top from $MAIN_V_FILE"

iverilog -o top_simtest ./prims.v ./top_tb.v ${MAIN_V_FILE}
echo "Running vvp..."
vvp -N ./top_simtest
