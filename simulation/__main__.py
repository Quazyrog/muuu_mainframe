from sys import argv, exit
from . import world, ai
import yaml


if len(argv) < 1:
    print("Usage: python TheGame.py <config file>.yml")
    exit(1)
setup = yaml.safe_load(open(argv[1]))

the_creator = ai.default_creator()
the_creator.quiet = False

the_world = the_creator.create(**setup)
the_world.run_until(setup["end_time"])

print()
print("SUMMARY:")
for (name, volume) in the_world._products.items():
    print(f"{name.rjust(10)}: {'#' * (volume['volume'] // 2)}")