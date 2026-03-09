# Differences

## Immutability Implementation

- To align with CPython's naming standards we renamed these items from the paper:
    - `register_shallow_freezable(type)` --> `_PyImmutability_RegisterShallowImmutable(type)`
    - `immutable.Yes` --> `immutable.FREEZABLE_YES`
    - `immutable.No` --> `immutable.FREEZABLE_NO`
    - `immutable.Explicit` --> `immutable.FREEZABLE_EXPLICIT`
    - `immutable.Proxy` --> `immutable.FREEZABLE_PROXY`
- The test microbenchmark now uses the baseline commit `aeff92d8`
    mentioned in section 7 instead of `754e7c9b`. The paper will
    be adjusted to reflect this change.
 