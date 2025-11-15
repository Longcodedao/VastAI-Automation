import argparse
import os
import json
import sys
import subprocess
import re
from utils import run_vast_command, run_command


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
    return parser.parse_args()


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
            print("There is no instance. Shut down")
            sys.exit(1)

        public_ip = out_json.get("public_ipaddr", None)
        ports = out_json.get("ports")

        mosh_ext_port = ports.get(f"{args.port_udp}/udp")[0].get("HostPort")
        ssh_ext_port = ports.get("22/tcp")[0].get("HostPort")

        if not public_ip or not ports or not ssh_ext_port:
            print("Error: Missing required components for connection (IP, Ports, ...)")
            sys.exit(1)

    except Exception as e:
        print(f"Unexpected Error has occured: {e}")

    mosh_cmd = f"mosh-server new -p {args.port_udp}"
    ssh_cmd = [
        "ssh",
        "-p",
        ssh_ext_port,
        f"root@{public_ip}",
        "-L",
        "8080:localhost:8080",
        mosh_cmd,
    ]

    print("Connecting to the SSH to get the Mosh key ...")

    try:
        ssh_result = run_command(ssh_cmd)
        # mosh_key = re.search(r"^[A-Za-z0-9+/]+={0,2}$", ssh_result)
        mosh_key = ssh_result.split(" ")[-1]
        print(ssh_result)
        print(f"Mosh key is: {mosh_key}")
        if not mosh_key:
            print("Error Cannot find a valid Mosh Key. Exiting ....")
            sys.exit(1)

    except Exception as e:
        print(f"Unexpected error when connecting SSH: {e}")
        sys.exit(1)

    print("Launching the MOSH shell")

    os.environ["MOSH_KEY"] = mosh_key

    mosh_client_cmd = [
        "mosh-client",
        public_ip,
        # Tell mosh which external UDP port to use
        str(mosh_ext_port),
    ]

    subprocess.run(mosh_client_cmd)


if __name__ == "__main__":
    main()
