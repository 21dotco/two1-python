import subprocess
import uuid
import time
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.normpath(os.path.join(script_dir, "../.."))

DRY_RUN = False

def shell(cmd, output=False):
    print("+ " + cmd)
    if DRY_RUN:
        return b"IMAGE_NAME"
    if output:
        return subprocess.check_output(cmd, shell=True)
    else:
        return subprocess.check_call(cmd, shell=True)

def main():
    # Build our Dockerfile
    image_name = "djangobitcoin:" + str(int(time.time()))
    shell("docker build -t " + image_name + " -f mmmDockerfile "+ repo_root)

    try:
        # Run the tests:
        print("--------------------")
        print("Running the tests...")
        print("--------------------")
        shell("docker run -i " + image_name + ' bash -c " python two1/mmm/manage.py test "')
        print("--------------------")
        print("Success!")
        print("--------------------")
    except Exception as e:
        print("--------------------")
        print("FAILURE!")
        print("--------------------")
        raise e
    finally:
        # Cleanup
        shell("docker rmi -f " + image_name)

if __name__ == "__main__":
    main()