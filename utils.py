import subprocess


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
