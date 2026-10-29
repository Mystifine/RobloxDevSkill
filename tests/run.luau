--!strict
-- Runs every spec of the skill's pure-Luau scripts (the Studio scripts are checked in Studio, as README.md records).
-- From the skill's folder: lune run tests/run.luau  (a failing spec raises an error, so the exit code is non-zero)

require("./PacingSim.spec")
