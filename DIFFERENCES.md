# Differences

## Immutability Implementation

- To align with CPython's naming standards we renamed these items from the paper:
    - `register_shallow_freezable(type)` --> `_PyImmutability_RegisterShallowImmutable(type)`
    - `immutable.Yes` --> `immutable.FREEZABLE_YES`
    - `immutable.No` --> `immutable.FREEZABLE_NO`
    - `immutable.Explicit` --> `immutable.FREEZABLE_EXPLICIT`
    - `immutable.Proxy` --> `immutable.FREEZABLE_PROXY`
