# fiorun

script to run through test scenarios easily with fio

When running io tests I often find myself thinking "...but I wonder what
the difference is with *slight tweak*".  This script has dicts with that allow
the operator to specify various fio options and all possible combinations are tested.

I have found in some scenarios where the workload of a server varies I can use this
approach to find the best middle ground.
