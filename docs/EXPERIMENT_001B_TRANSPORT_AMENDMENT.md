# Experiment 001B transport amendment

The frozen protocol proposed ten queries containing ten cones each. IRSA rejected
that query with TAP QUERY_STATUS ERROR (unsupported ADQL). Its official TAP
documentation states that only one geometric constraint is supported per query:
https://irsa.ipac.caltech.edu/docs/program_interface/TAP.html#where

Before successful target retrieval or analysis, replace those queries with 100
individual cone requests, one per frozen target, with at most three concurrent
requests. Each response is independently archived and validated. All selection,
radius, epoch, quality, association and interpretation rules remain unchanged.
The original protocol and selection hashes remain intact. The manifest records
this amendment's hash and replay verifies it. A single-target syntax probe was
successful; its measurements were not examined or used for selection or analysis.
