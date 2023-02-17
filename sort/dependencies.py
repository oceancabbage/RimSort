import logging

logger = logging.getLogger(__name__)


def gen_deps_graph(active_mods_json, active_mod_ids):
    """
    Get dependencies
    """
    # Schema: {item: {dependency1, dependency2, ...}}
    logging.info("Generating dependencies graph")
    dependencies_graph = {}
    for package_id, mod_data in active_mods_json.items():
        dependencies_graph[package_id] = set()
        if mod_data.get("dependencies"):  # Will either be None, or a set
            for dependency in mod_data["dependencies"]:
                # Only add a dependency if dependency exists in active_mods
                # (related to comment about stripping dependencies)
                if dependency in active_mod_ids:
                    dependencies_graph[package_id].add(dependency)
    logging.info(
        f"Finished generating dependencies graph of {len(dependencies_graph)}, returning"
    )
    return dependencies_graph


def gen_rev_deps_graph(active_mods_json, active_mod_ids):
    # Schema: {item: {isDependentOn1, isDependentOn2, ...}}
    logging.info("Generating reverse dependencies graph")
    reverse_dependencies_graph = {}
    for package_id, mod_data in active_mods_json.items():
        reverse_dependencies_graph[package_id] = set()
        if mod_data.get("isDependencyOf"):  # Will either be None, or a set
            for dependent in mod_data["isDependencyOf"]:
                if dependent in active_mod_ids:
                    reverse_dependencies_graph[package_id].add(dependent)
    logging.info(
        f"Finished generating reverse dependencies graph of {len(reverse_dependencies_graph)}, returning"
    )
    return reverse_dependencies_graph


def gen_tier_one_deps_graph(dependencies_graph):
    # Below is a list of mods determined to be "tier one", in the sense that they
    # should be loaded first before any other regular mod. Tier one mods will have specific
    # load order needs within themselves, e.g. Harmony before core. There is no guarantee that
    # this list of mods is exhaustive, so we need to add any other mod that these mods depend on
    # into this list as well.
    # TODO: pull from a config
    logger.info("Generating dependencies graph for tier one mods")
    known_tier_one_mods = {
        "zetrith.prepatcher",
        "brrainz.harmony",
        "ludeon.rimworld",
        "ludeon.rimworld.royalty",
        "ludeon.rimworld.ideology",
        "ludeon.rimworld.biotech",
        "unlimitedhugs.hugslib",
    }
    tier_one_mods = set()
    for known_tier_one_mod in known_tier_one_mods:
        if known_tier_one_mod in dependencies_graph:
            # Some known tier one mods might not actually be active
            tier_one_mods.add(known_tier_one_mod)
            dependencies_set = get_dependencies_recursive(
                known_tier_one_mod, dependencies_graph
            )
            tier_one_mods.update(dependencies_set)
    logger.info(f"Recursively generated the following set of tier one mods: {tier_one_mods}")
    tier_one_dependency_graph = {}
    for tier_one_mod in tier_one_mods:
        # Tier one mods will only ever reference other tier one mods in their dependencies graph
        tier_one_dependency_graph[tier_one_mod] = dependencies_graph[tier_one_mod]
    logger.info("Attached corresponding dependencies to every tier one mod, returning")
    return tier_one_dependency_graph, tier_one_mods


def get_dependencies_recursive(package_id, active_mods_dependencies):
    dependencies_set = set()
    # Should always be true since all active ids get initialized with a set()
    if package_id in active_mods_dependencies:
        for dependency_id in active_mods_dependencies[package_id]:
            dependencies_set.add(dependency_id)  # Safe, as should refer to active id
            dependencies_set.update(  # Safe, as should refer to active ids
                get_dependencies_recursive(dependency_id, active_mods_dependencies)
            )
    return dependencies_set


def gen_tier_three_deps_graph(dependencies_graph, reverse_dependencies_graph):
    # Below is a list of mods determined to be "tier three", in the sense that they
    # should be loaded after any other regular mod, potentially at the very end of the load order.
    # Tier three mods will have specific load order needs within themselves. There is no guarantee that
    # this list of mods is exhaustive, so we need to add any other mod that these mods depend on
    # into this list as well.
    # TODO: pull from a config
    logger.info("Generating dependencies graph for tier three mods")
    known_tier_three_mods = {"krkr.rocketman"}
    tier_three_mods = set()
    for known_tier_three_mod in known_tier_three_mods:
        if known_tier_three_mod in dependencies_graph:
            # Some known tier three mods might not actually be active
            tier_three_mods.add(known_tier_three_mod)
            rev_dependencies_set = get_reverse_dependencies_recursive(
                known_tier_three_mod, reverse_dependencies_graph
            )
            tier_three_mods.update(rev_dependencies_set)
    logger.info(f"Recursively generated the following set of tier three mods: {tier_three_mods}")
    tier_three_dependency_graph = {}
    for tier_three_mod in tier_three_mods:
        # Tier three mods may reference non-tier-three mods in their dependencies graph,
        # so it is necessary to trim here
        tier_three_dependency_graph[tier_three_mod] = set()
        for possible_add in dependencies_graph[tier_three_mod]:
            if possible_add in tier_three_mods:
                tier_three_dependency_graph[tier_three_mod].add(possible_add)
    logger.info("Attached corresponding dependencies to every tier three mod, returning")
    return tier_three_dependency_graph, tier_three_mods


def get_reverse_dependencies_recursive(package_id, active_mods_rev_dependencies):
    reverse_dependencies_set = set()
    # Should always be true since all active ids get initialized with a set()
    if package_id in active_mods_rev_dependencies:
        for dependent_id in active_mods_rev_dependencies[package_id]:
            reverse_dependencies_set.add(
                dependent_id
            )  # Safe, as should refer to active id
            reverse_dependencies_set.update(  # Safe, as should refer to active ids
                get_reverse_dependencies_recursive(
                    dependent_id, active_mods_rev_dependencies
                )
            )
    return reverse_dependencies_set


def gen_tier_two_deps_graph(
    active_mods, active_mod_ids, tier_one_mods, tier_three_mods
):
    # Now, sort the rest of the mods while removing references to mods in tier one and tier three
    # First, get the dependency graph for tier two mods, minus all references to tier one
    # and tier three mods
    logger.info("Generating dependencies graph for tier two mods")
    logger.info("Stripping all references to tier one and tier three mods and their dependencies")
    tier_two_dependency_graph = {}
    for package_id, mod_data in active_mods.items():
        if package_id not in tier_one_mods and package_id not in tier_three_mods:
            dependencies = mod_data.get("dependencies")
            stripped_dependencies = set()
            if dependencies:
                for dependency_id in dependencies:
                    # Remember, dependencies from all_mods can reference non-active mods
                    if (
                        dependency_id not in tier_one_mods
                        and dependency_id not in tier_three_mods
                        and dependency_id in active_mod_ids
                    ):
                        stripped_dependencies.add(dependency_id)
            tier_two_dependency_graph[package_id] = stripped_dependencies
    logger.info("Generated tier two dependency graph, returning")
    return tier_two_dependency_graph
