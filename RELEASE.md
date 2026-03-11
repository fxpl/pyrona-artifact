# Release: The big HOW TO

1. Make sure the baseline and patch ref in [`scripts/update/1_create_cpython_snapshots.sh`](./scripts/update/1_create_cpython_snapshots.sh) are correct
2. Create/Update the CPython snapshot
    ```
    ./scripts/update/1_create_cpython_snapshots.sh
    ```
3. Update `GUIDE.md`
    ```
    python3 ./scripts/update/2_build_navigation_guide.py
    ```
4. Make sure GitHub Actions secrets are configured for Docker artifact publishing:
    - `ZENODO_TOKEN`
    - `ZENODO_DEPOSITION_ID`
5. Publish a GitHub release. The workflow at `.github/workflows/docker-images.yml` will:
    - build `linux/amd64` and `linux/arm64` Docker archives
    - attach checksums as workflow artifacts
    - prepare `pyrona-artifact.zip` containing the repository tree
    - include `pyrona-artifact/docker/` with Docker archives and checksums
    - include root files like `pyrona-artifact/README.md` and `pyrona-artifact/LICENSE`
    - upload that single zip into a Zenodo draft deposition
6. Publish the Zenodo draft manually in the Zenodo UI. The repository token only needs `deposit:write`, so CI does not attempt to publish.
7. To rerun the upload manually, start the workflow with `workflow_dispatch` and provide `zenodo_deposition_id` when needed.


