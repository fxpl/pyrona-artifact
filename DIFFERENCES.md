# Differences

## Paper

- This artifact includes PyPerformance benchmarks that have been requested
    as part of the conditional accept.
- The test microbenchmark now uses the baseline commit `aeff92d8`
    mentioned in section 7 instead of `754e7c9b`. The paper will
    be adjusted to reflect this change.
- The figure, section and table numbers refer to the numbers of the conditionally
    accepted version of the paper. They may differ from the final version.

## Immutability Implementation

- We renamed these items from the paper:
    - `register_shallow_freezable(type)` --> `_PyImmutability_RegisterShallowImmutable(type)`
    - `immutable.Yes` --> `immutable.FREEZABLE_YES`
    - `immutable.No` --> `immutable.FREEZABLE_NO`
    - `immutable.Explicit` --> `immutable.FREEZABLE_EXPLICIT`
    - `immutable.Proxy` --> `immutable.FREEZABLE_PROXY`
    - `immutable.mutable` --> `immutable.requires_mutable`
- The default freezability of types in this artifact is `FREEZABLE_YES` to help
    during development. Our paper proposes `FREEZABLE_NO` as the default freezability
    for types to ensure safety. Changing the default will be easy since changing
    freezability is implemented. The semantics of the paper can be mirrored exactly
    by setting the freezability of new types to `FREEZABLE_NO` or using the
    `@unfreezable` decorator.
