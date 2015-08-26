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
    image_name = "two1:" + str(int(time.time()))
    shell("docker build -t " + image_name + " -f Dockerfile "+ repo_root)

    try:
        # Run the tests:
        print("--------------------")
        print("Running the tests...")
        print("--------------------")
        shell("docker run --rm -i " + image_name + ' bash -c " py.test two1 tests"')
        print("--------------------")
        print("Success!")
        print("--------------------")
        shell("docker tag -f " + image_name + " two1:latest-success")
    except Exception as e:
        print("--------------------")
        print("FAILURE!")
        print("--------------------")
        shell("docker tag -f " + image_name + " two1:latest-failure")
        raise e
    finally:
        # Cleanup
        shell("docker rmi " + image_name) #since we tagged the image, rmi only untags.

if __name__ == "__main__":
    main()