# Artefact: "Dynamically Checked Deep Immutability in Python"

## Artifact Information

This artifact holds a snapshot of CPython and a patched CPython
version with the modifications described in the paper. Differences
between the paper and the implementation are documented in
[DIFFERENCES.md](./DIFFERENCES.md)

The [GUIDE.md](./GUIDE.md) file contains links to examples, benchmarks
and implementation details that are part of this artifact.

## System requirements

This artifact is packaged using Docker to ensure reproducibility across different systems.
We recommend using a machine with:
- 20+ GB of free disk space to accommodate the Docker image and the datasets.
- 12+ GB of RAM allocated to Docker.
- 8+ CPU cores allocated to Docker.
- A web browser to access the interactive application.
- Internet access, if you want to build the docker container or from scratch
    or run the artifact locally on your machine

We have tested the artifact on an x86_64 Linux (Ubuntu 24.04.3) and ARM MacOS (Tahoe 26.3.1).

## Working with this Artifact

These instructions assume that you have downloaded `pyrona-artifact.zip` from
Zenodo and unzipped the file. Now you should have a new folder `pyrona-artifact`.

### Using Pre-Built Docker Images

The Zenodo archive includes pre-built Docker image archives for `linux-amd64`
and `linux-arm64`. If you're on either of these platforms we recommend that
you use the pre-built image like this:

1. Ensure Docker is installed (<https://www.docker.com/get-started>).
    We have tested the artifact with Docker version 28.2.2.
2. Select and unzip the docker image for your platform like this:

    ```bash
    unzip -p docker/pyrona-artifact-linux-amd64.docker.zip | docker load
    unzip -p docker/pyrona-artifact-linux-arm64.docker.zip | docker load
    ```

3. Confirm that the docker image has been loaded:

    ```bash
    docker images
    ```

4. Start the docker image:

    ```bash
    docker run --rm -p 8501:8501 --memory=12g --cpus=8 pyrona-artifact:immutability
    ```

    Make sure that docker has enough memory and cores allocated to it. On linux
    you can use the `--memory` and `--cpus` arguments in the command above.

    These flags don't work on Windows and MacOS. If you're using docker desktop
    you can open "Docker Desktop -> Settings -> Resources" and allocate
    more resources.

5. When you open <http://localhost:8501/> you should see a web application.

6. While the container is running, you can connect to the container to run
    commands and inspect the file system. For this, first fetch the container
    by ID running `docker ps` in a new terminal on your host, and then:

    ```bash
    docker exec -it <container-id> /bin/bash
    ```

### Manually Building the Docker Image

Building the image from scratch may take up to 30 minutes, as several
dependencies must be downloaded and compiled. On the machine we used
for testing, building the image took around ~10 minutes.

```bash
docker buildx build --load -t pyrona-artifact .
```

Now resume from step 3 in the section above.

### Run the Artifact Locally (Without Docker)

You can check the [`Dockerfile`](./Dockerfile) to see the full
setup and required linux packages. If all dependencies are installed
you should be able to initialise everything with this short script:
(take from the docker file)

```bash
# UV as a build manager
curl -LsSf https://astral.sh/uv/install.sh | sh
PATH="/root/.local/bin:${PATH}"

# Load Environment Variables
source env.env

# Build snapshots and Python environments used by the artifact.
scripts/setup/1_build_cpython.sh
scripts/setup/2_build_venv.sh
scripts/setup/3_pyperformance_setup.sh

# Run minimal smoke test
scripts/smoketest.sh --minimal
```

You can start the website locally using this command:

```bash
source "$STABLE_PYTHON_ENV_ACTIVATE"
python -m streamlit run app/immutability/artifact.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true
deactivate
```

You can also run benchmarks directly like this:

```bash
benchmarks/pickling-vs-freeze/run.sh
```

## Navigation

The simplest way to interact with this artifact is to open this website
<http://localhost:8501/> and follow the instructions.

If you want to look at the benchmarks or implementation you can start
by looking at [`./GUIDE.md`](./GUIDE.md) it contains links to the implementation
and benchmarks.

## Clean-up

Once you're done, you can remove the docker image using the following
command in the host terminal:

```bash
docker rmi pyrona-artifact:immutability
```

## Troubleshooting

1. **"Permission denied" when running Docker commands:**

    Docker's documentation explains how you can manage Docker as a non-root user:
    <https://docs.docker.com/engine/install/linux-postinstall/>
    You can also invoke all Docker commands as root, that should work here.

2. **Problems with credentials on Linux**

    Building the Docker container can fail due to a missing or incorrectly
    configured credential helper (`docker-credential-desktop`). This can be
    caused by the default configuration of the host system. In the past, it
    has helped to modify `~/.docker/config.json` to delete the following line:

    ```json
    "credsStore": "desktop"
    ```

3. **Is the docker daemon running? On MacOS**

    ```
    Cannot connect to the Docker daemon at unix:///Users/.../.colima/default/docker.sock. Is the docker daemon running?
    ```

    Assuming you use colima, you can start it with the following command:

    ```bash
    colima start
    ```

    And then check the status via:

    ```bash
    colima status
    docker info
    ```

4. **The CPython build as part of the Docker build fails**

    If the error messages look something like this:

    ```
    gcc: fatal error: Killed signal terminated program cc1
    compilation terminated.
    make[2]: *** [Makefile:3305: Parser/action_helpers.o] Error 1
    make[2]: *** Waiting for unfinished jobs....
    ```

    It is likely due to memory limitations. You can either increase the
    memory in docker desktop or use the following commands if you're using
    `colima`:

    ```
    colima stop
    colima start --memory 12 --cpu 8 --disk 100
    ```

## License

This artifact is licensed under the MIT license. It includes copies
of 3rd party software, like CPython, coming with their own licenses.

### Credit

Parts of this README and the interactive application have been adapted
from <https://doi.org/10.5281/zenodo.18500269> by
[Andrea Gilot](https://orcid.org/0009-0006-4463-9414),
[Tobias Wrigstad](https://orcid.org/0000-0002-4269-5408),
[Eva Darulova](https://orcid.org/0000-0002-6848-3163) licensed
under Apache License 2.0.
