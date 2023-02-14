from typing import Any, Dict


def do_rimpy_sort(
    dependency_graph: Dict[str, set], active_mods_json: Dict[str, Any]
) -> Dict[str, Any]:
    # Get an alphabetized list of dependencies
    active_mods_id_to_name = dict((k, v["name"]) for k, v in active_mods_json.items())
    active_mods_alphabetized = sorted(
        active_mods_id_to_name.items(), key=lambda x: x[1], reverse=False
    )
    dependencies_alphabetized = {}
    for tuple_id_name in active_mods_alphabetized:
        if tuple_id_name[0] in dependency_graph:
            dependencies_alphabetized[tuple_id_name[0]] = dependency_graph[
                tuple_id_name[0]
            ]

    mods_load_order = []
    for package_id in dependencies_alphabetized:
        # Avoid repeating adding packages that have already been added
        if package_id not in mods_load_order:
            # Add the current mod in alphabetical order
            mods_load_order.append(package_id)

            # ?
            index_just_appended = mods_load_order.index(package_id)
            recursively_force_insert(
                mods_load_order,
                dependency_graph,
                package_id,
                active_mods_json,
                index_just_appended,
            )

    reordered = {}
    for package_id in mods_load_order:
        reordered[package_id] = active_mods_json[package_id]
    return reordered


def recursively_force_insert(
    mods_load_order,
    dependency_graph,
    package_id,
    active_mods_json,
    index_just_appended,
):
    # Get the reverse alphabetized list (by name) of the current mod's dependencies
    deps_of_package = dependency_graph[package_id]
    deps_id_to_name = {}
    for dependency_id in deps_of_package:
        deps_id_to_name[dependency_id] = active_mods_json[dependency_id]["name"]
    deps_of_package_alphabetized = sorted(
        deps_id_to_name.items(), key=lambda x: x[1], reverse=True
    )

    # Iterate through the list of reverse alphabetized dependencies
    # The idea is to insert at the list index so that e.g.
    # mod A has dependencies B and C (in that rev alphabetical order),
    # then the return list will have [C, B, A].
    for tuple_dep_id_dep_name in deps_of_package_alphabetized:
        dep_id = tuple_dep_id_dep_name[0]
        if dep_id not in mods_load_order:
            # We can't just insert it here. This is because deps in deps_of_package_alphabetized
            # may contain deps that depend on each other. Therefore, before we insert a dep,
            # we need to interate through the sublist starting at the original package_id index
            # and ending at the live index of the package_id (this gives the sublist of deps)
            # that have been inserted for this package_id, this also works for recursively
            # inserted deps of deps). We iterate through this list backwards, as we want to check
            # for the first dep that the current dep depends on (if it exists). It if exists,
            # the index to insert the current dep will be the index of that dep + 1, as we do not
            # want to shift that dep back. Otherwise, if no dep of dep is found, then we insert
            # at the original index normally.
            index_to_insert_at = index_just_appended
            for e in reversed(
                mods_load_order[index_just_appended : mods_load_order.index(package_id)]
            ):
                if e in dependency_graph[dep_id]:
                    index_to_insert_at = mods_load_order.index(e) + 1
                    break

            mods_load_order.insert(index_to_insert_at, dep_id)
            new_idx = mods_load_order.index(dep_id)
            recursively_force_insert(
                mods_load_order,
                dependency_graph,
                dep_id,
                active_mods_json,
                new_idx,
            )
