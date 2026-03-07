# Release: The big HOW TO

## TODO: Remove `snapshots` from `.gitignore`

1. Make sure the baseline and patch ref in [`scripts/create_cpython_snapshots.sh`](./scripts/create_cpython_snapshots.sh) are correct
2. Create/Update the CPython snapshot

    ```
    ./scripts/create_cpython_snapshots.sh
    ```
3. Update `GUIDE.md`
    ```
    python3 ./scripts/build_navigation_guide.py
    ```


