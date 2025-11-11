import argparse
import sys
import json
import subprocess
import time
import os
import re # Added import for SSH URI parsing

# --- Configuration Constants ---
MAX_ATTEMPTS = 6
SLEEP_SECONDS = 15
DEFAULT_GPU = "RTX_3060"
# NOTE: Using os.path.expanduser for cross-platform home directory reference


# --- Helper Functions ---

def run_vast_command(command_args: list, check: bool = True, capture_output: bool = True):
    """
    Executes a vastai CLI command.
    
    :param command_args: List of arguments to pass to 'vastai'.
    :param check: If True, raise an exception on non-zero exit status.
    :param capture_output: If True, capture stdout/stderr and return it.
    :return: The output (stdout) as a string, or the subprocess result object.
    """
    try:
        command = ["vastai"] + command_args
        result = subprocess.run(
            command,
            check=check,
            capture_output=capture_output,
            text=True
        )
        if capture_output:
            return result.stdout.strip()
        return result

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error executing command: {' '.join(command)}")
        print(f"   Stderr: {e.stderr.strip()}")
        # Re-raise the exception to be caught by the main try/except block
        raise 
    except FileNotFoundError:
        print(f"\n❌ Error: 'vastai' command not found. Is the Vast.ai CLI installed and in your PATH?")
        raise 
    except Exception as e:
        print(f"\n❌ Unexpected error executing command: {' '.join(command)}")
        print(f"   Error: {e}")
        raise


def cleanup_instance(instance_id: str):
    """Destroys the instance if the ID is valid."""
    # CLI instance IDs are typically strings
    if instance_id and instance_id != "null":
        print("\n🚨 ERROR/INTERRUPT DETECTED. Cleaning up...")
        print(f"🧹 Terminating instance {instance_id}...")
        
        # We don't use check=True here because vastai destroy might return an error
        # if the instance is already gone (e.g., 404). We silence the output.
        result = subprocess.run(
            ["vastai", "destroy", "instance", instance_id],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Instance {instance_id} terminated.")
        else:
            # Check for specific "not found" error, otherwise warn
            if "not found" in result.stderr:
                 print(f"✅ Instance {instance_id} terminated (was already destroyed).")
            else:
                 print(f"⚠️ Failed to destroy instance {instance_id}. Check the Vast.ai console.")
                 print(f"   Error: {result.stderr.strip()}")
    else:
        print("Script failed before instance creation. No cleanup needed.")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Search, launch, and connect to the cheapest Vast.ai instance for a specified GPU."
    )
    parser.add_argument(
        "--gpu-name",
        type=str,
        default=DEFAULT_GPU,
        help=f"The name of the GPU to search for (e.g., RTX_4090, A100). Defaults to '{DEFAULT_GPU}'."
    )
    parser.add_argument(
        "--num-gpus",
        nargs='?',
        type=int,
        default=1,
        help="The number of GPUs to request. Defaults to 1."
    )

    parser.add_argument(
        "--min-cpu-ram",
        type=int,
        default=16,
        help="Minimum CPU RAM in GB required. Defaults to 16GB."
    )

    parser.add_argument(
        "--disk-storage",
        type=int,
        default=16,
        help="Disk storage size in GB for the instance. Defaults to 16GB."
    )

    parser.add_argument(
        "--max-dph",
        type=float,
        default=0.2,
        help="Maximum dollars per hour (DPH) for the instance. Defaults to 0.2."
    )

    parser.add_argument(
        "--min-cuda-version",
        type=float,
        default=12.8,
        help="Minimum CUDA version required. Defaults to 12.8."
    )

    parser.add_argument(
        "--template",
        type=str,
        default="vastai/pytorch:cuda-12.8.1-auto",
        help="The Vast.ai image template to use for the instance. Defaults to 'vastai/pytorch:cuda-12.8.1-auto'."
    )

    parser.add_argument(
        "--ssh-key-path",
        type=str,
        default=os.path.expanduser("~/.ssh/id_ed25519.pub"),
        help="Path to the SSH public key to add to the instance. Defaults to '~/.ssh/id_ed25519.pub'."
    )   

    parser.add_argument(
        "--tag",
        type=str,
        default="Launched_GPU_Instance",
        help="Label/tag to assign to the launched instance. Defaults to 'Launched_GPU_Instance'."
    )

    return parser.parse_args()

def main():
    args = parse_args()
    target_gpu = args.gpu_name
    instance_id = None # CLI instance ID is a string/None
    
    print(f"🔍 Searching for the cheapest '{target_gpu}' instance...")

    # --- 3. Find Best Offer ---
    try:
        # Construct search query
        # Note: cpu_ram is in GB for the vastai CLI search query, but MB in the API (handled by CLI)
        search_query = (
            f"gpu_name={target_gpu} num_gpus={args.num_gpus} "
            f"cpu_ram>={args.min_cpu_ram} dph_total<{args.max_dph} "
            f"cuda_vers>={args.min_cuda_version} disk_space>={args.disk_storage}" 
        )

        # Execute vastai search
        offer_output = run_vast_command([
            "search", "offers", search_query,
            "--order", "dph_total",
            "--raw" # Request JSON output
        ])
        # Parse JSON output
        offer_details = json.loads(offer_output)
        if not offer_details:
            print(f"\nNo suitable offer found matching all criteria for {target_gpu}")
            sys.exit(1)


        offer = offer_details[0]
        offer_id = offer.get('id')

        if not offer_id:
            print(f"\nNo suitable offer found matching all criteria for {target_gpu}")
            sys.exit(1)

        # Extract and calculate details (API returns MB, convert to GB)
        gpu_name = offer.get('gpu_name', 'N/A')
        dph_total = float(offer.get('dph_total', 0.0))
        cpu_ram_mb = offer.get('cpu_ram', 0)
        gpu_ram_mb = offer.get('gpu_ram', 0)
        disk_storage = offer.get('disk_space', 0)
        rel_score = float(offer.get('reliability', 0.0))
        dlperf_score = float(offer.get('dlperf', 0.0))
        
        cpu_ram_gb = cpu_ram_mb / 1024
        gpu_ram_gb = gpu_ram_mb / 1024

        print(f"✅ Found cheapest offer: ID {offer_id}")
        print("💡 Offer details:")
        print(f"   GPU Name: {gpu_name}")
        print(f"   VRAM (GB): {gpu_ram_gb:.2f}")
        print(f"   DPH Total: {dph_total:.4f} USD")
        print(f"   CPU RAM (GB): {cpu_ram_gb:.2f}")
        print(f"   Disk Storage (GB): {disk_storage:.2f}")
        print(f"   Reliability: {rel_score:.4f}")
        print(f"   DLPerf: {dlperf_score:.2f}")

    except Exception as e:
        print(f"\n❌ Error during offer search or parsing.")
        print(e)
        # Print details only if not a subprocess error (which is handled in run_vast_command)
        if not isinstance(e, subprocess.CalledProcessError):
            print(f"   Detail: {e}")
        sys.exit(1)


    # --- 4. Interactive Confirmation ---
    user_choice = input("Do you want to launch this instance? (y/n): ").lower()
    while user_choice not in ['y', 'n']:
        user_choice = input("Invalid input. Please enter 'y' for yes or 'n' for no: ").lower()

    if user_choice == 'n':
        print("Operation cancelled by user.")
        sys.exit(0)

    # --- 5. Create Instance (Wrapped in try/finally for cleanup) ---
    try:
        print("🚀 Creating instance...")
        create_output = run_vast_command([
            "create", "instance", str(offer_id),
            "--image", str(args.template),
            "--disk", str(args.disk_storage),
            # "--jupyter", 
            "--label", args.tag,
            "--raw"
        ])
        
        create_data = json.loads(create_output)
        # The new_contract ID is returned as a string by the CLI/API
        instance_id = str(create_data.get('new_contract'))
        
        if not instance_id or instance_id == "null":
             raise Exception("Instance ID was not returned by vastai create.")
             
        print(f"✅ Instance ID {instance_id} created successfully. Waiting for it to start...")

        # --- 6. Connection Info Retrieval with Timeout ---
        print("⏳ Waiting for instance to start and network to initialize (Max 90 seconds)...")

        ssh_uri = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                # Use check=False here because the command often fails while the instance is spinning up
                ssh_output = run_vast_command(
                    ["ssh-url", instance_id, "--raw"], 
                    check=False,
                    capture_output=True
                )
                if ssh_output:
                    ssh_uri = ssh_output.strip()
                    print(f"✅ Retrieved SSH command. The SSH Address is: {ssh_uri}")
                    break
            except Exception:
                pass # Suppress any errors during the transient startup phase

            if attempt < MAX_ATTEMPTS:
                print(f"Attempt {attempt}/{MAX_ATTEMPTS} failed. Retrying in {SLEEP_SECONDS}s...")
                time.sleep(SLEEP_SECONDS)

        if not ssh_uri:
            raise Exception("Failed to retrieve SSH connection info within the timeout period.")

        # --- 7. SSH Key Attachment ---
        print("🔐 Adding SSH public key to the instance for passwordless login...")
        if os.path.exists(args.ssh_key_path):
            with open(args.ssh_key_path, 'r') as f:
                ssh_public_key = f.read().strip()
            
            print("   Attempting key attachment... ", end='', flush=True)
            # Silencing output for the attachment command
            result = subprocess.run(
                ["vastai", "attach", "ssh", instance_id, ssh_public_key],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                print("✅ Success.")
                print("   SSH public key added to the instance.")
            else:
                print("❌ Failed.")
                print(f"⚠️ WARNING: Failed to attach SSH public key. Error: {result.stderr.strip()}")
        else:
            print(f"⚠️ SSH public key not found at {args.ssh_key_path}. Skipping key addition.")
            print("   Ensure your key is added to your Vast.ai account for automatic injection.")

        # --- 8. Final Connection Instructions ---
        # Parse the URI: ssh://user@host:port
        match = re.search(r"ssh://([^@]+)@([^:]+):([0-9]+)", ssh_uri)
        if match:
            user, host, port = match.groups()
            ssh_command = f"ssh -p {port} {user}@{host} -L 8080:localhost:8080"
            
            print("\n✅ Instance is ready! You can connect using the following SSH command:")
            print(ssh_command)
            print("🔑 Make sure your SSH private key is properly set up to connect.")
            print("Please connect SSH a few minutes after launching to allow all services to initialize.")
            print("Don't forget to stop or terminate your instance when you're done to avoid extra charges!")
        else:
            raise Exception("Could not parse SSH URI format.")

        print("\n🎉 Setup complete! Instance remains running.")

    except Exception as e:
        print(f"\n\n❌ Fatal Error during launch or connection: {e}")
        # Call cleanup for the instance that was created
        if instance_id:
             cleanup_instance(instance_id)
        sys.exit(1)
        
    # Successful exit
    sys.exit(0)

if __name__ == "__main__":
    main()