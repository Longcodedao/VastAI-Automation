import subprocess
import sys


def run_vast_command(
    command_list: list, check: bool = True, capture_output: bool = True
):
    """
    Executes a vastai CLI command.

    :param command_args: List of arguments to pass to 'vastai'.
    :param check: If True, raise an exception on non-zero exit status.
    :param capture_output: If True, capture stdout/stderr and return it.
    :return: The output (stdout) as a string, or the subprocess result object.
    """
    try:
        command = ["vastai"] + command_list
        result = subprocess.run(
            command, check=check, capture_output=capture_output, text=True
        )
        # print(f"Result is: {result}")
        # print(f"Stdout of result: {result}")
        if capture_output:
            return result.stdout.strip()

        return result

    except subprocess.CalledProcessError as e:
        print(f"Command failed and return code: {e.returncode}")
        print(f"STDERR: {e.stderr}")
        raise

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise


def run_command(command_list: list, check: bool = True, capture_output: bool = True):
    """
    Executes a Bash CLI command.

    :param command_args: List of arguments to pass to 'vastai'.
    :param check: If True, raise an exception on non-zero exit status.
    :param capture_output: If True, capture stdout/stderr and return it.
    :return: The output (stdout) as a string, or the subprocess result object.
    """
    try:
        result = subprocess.run(
            command_list, check=check, capture_output=capture_output, text=True
        )
        # print(f"Result is: {result}")
        # print(f"Stdout of result: {result}")
        if capture_output:
            return result.stdout.strip()

        return result

    except subprocess.CalledProcessError as e:
        print(f"Command failed and return code: {e.returncode}")
        print(f"STDERR: {e.stderr}")
        raise

    except Exception as e:
        print(f"Unexpected error: {e}")
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
            text=True,
        )

        if result.returncode == 0:
            print(f"✅ Instance {instance_id} terminated.")
        else:
            # Check for specific "not found" error, otherwise warn
            if "not found" in result.stderr:
                print(f"✅ Instance {instance_id} terminated (was already destroyed).")
            else:
                print(
                    f"⚠️ Failed to destroy instance {instance_id}. Check the Vast.ai console."
                )
                print(f"   Error: {result.stderr.strip()}")
    else:
        print("Script failed before instance creation. No cleanup needed.")


def display_instance(offer_instance, target_gpu: str = None):
    #    print(offer_instance)
    offer_id = offer_instance.get("id")

    if not offer_id:
        print(f"\nNo suitable offer found matching all criteria for {target_gpu}")
        sys.exit(1)

    # Extract and calculate details (API returns MB, convert to GB)
    cpu_name = offer_instance.get("cpu_name", "N/A")
    gpu_name = offer_instance.get("gpu_name", "N/A")
    dph_total = float(offer_instance.get("dph_total", 0.0))
    cpu_ram_mb = offer_instance.get("cpu_ram", 0)
    gpu_ram_mb = offer_instance.get("gpu_ram", 0)
    disk_storage = offer_instance.get("disk_space", 0)
    rel_score = float(offer_instance.get("reliability", 0.0))
    dlperf_score = float(offer_instance.get("dlperf", 0.0))
    inet_down = float(offer_instance.get("inet_down", 0.0))
    inet_up = float(offer_instance.get("inet_up", 0.0))
    geolocation = offer_instance.get("geolocation", "N/A")

    cpu_ram_gb = cpu_ram_mb / 1024
    gpu_ram_gb = gpu_ram_mb / 1024
    inet_down_mbs = inet_down * 0.125
    inet_up_mbs = inet_up * 0.125

    print(f"✅ Found cheapest offer: ID {offer_id}")
    print("💡 Offer details:")
    print(f"   Geolocation: {geolocation}")
    print(f"   CPU Name: {cpu_name}")
    print(f"   CPU RAM (GB): {cpu_ram_gb:.2f}")
    print(f"   GPU Name: {gpu_name}")
    print(f"   VRAM (GB): {gpu_ram_gb:.2f}")
    print(f"   DPH Total: {dph_total:.4f} USD")
    print(f"   Disk Storage (GB): {disk_storage:.2f}")
    print(f"   Reliability: {rel_score:.4f}")
    print(f"   DLPerf: {dlperf_score:.2f}")
    print(f"   Inet Down (MB/s): {inet_down_mbs}")
    print(f"   Inet Up   (MB/s): {inet_up_mbs}")
