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
- 10+ GB of free disk space to accommodate the Docker image and the datasets.
- 8+ GB of RAM allocated to Docker.
- 4+ CPU cores allocated to Docker.
- Internet access to build the Docker image.
- A web browser to access the interactive application.

We have tested the artifact on an x86_64 Linux (Ubuntu 24.04.3) and ARM MacOS (Tahoe 26.3.1).

## Building the Docker Image

To build the Docker image, please follow the steps below:
1. Ensure Docker is installed (<https://www.docker.com/get-started>). We have tested the artifact with Docker version 28.2.2.
2. Open a terminal and navigate to the directory containing this `README.md` file and the `Dockerfile`.
3. Building the image may take up to 30 minutes, as several dependencies must be downloaded and compiled.
    This estimation may vary based on your internet connection and machine performance.
    On the machine we used for testing, building the image took around 20 minutes.
    ```bash
    docker build -t pyrona-artifact .
    ``` 
4. After completion, verify that the image has been created successfully by running:
    ```bash
    docker images
    ```
    You should see `pyrona-artifact` listed.

## Troubleshooting

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
