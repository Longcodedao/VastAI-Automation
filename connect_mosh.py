import argparse
import os
import json
import sys
import subprocess
import re
from utils import run_vast_command


def parse_args():
    parser = argparse.ArgumentParser(description="Connect the instance via Mosh Shell")

    parser.add_argument(
        "--instance-id",
        type=str,
        required=True,
        help="Please type the instance id to see the information",
    )

    parser.add_argument(
        "--port-udp",
        type=int,
        default=60001,
        help="UDP Port for connecting the Mosh shell",
    )
    return parser


def main():
    # Parse the argument to get the instance
    args = parse_args()
    instance_id = args.instance_id

    try:
        # Create a command to collect the instance information
        list_command = ["show instance"] + [instance_id] + ["--raw"]
        show_output = run_vast_command(list_command)

        # Details output json file
        out_json = json.loads(show_output)

        if not out_json:
            print(f"There is no instance. Shut down")
            sys.exit(1)

        public_ip = out_json.get("public_ipaddr", None)
        ports = out_json.get("ports")

        mosh_ext_port= ports.get(f"{args.port_udp}/udp")
        ssh_ext_port = ports.get("22/tcp") 

        if not public_ip or not ports or not ssh_ext_port:
            print("Error: Missing required components for connection (IP, Ports, ...)")
           sys.exit(1) 
       
         

    except Exception as e:
        print(f"Unexpected Error has occured: {e}")
