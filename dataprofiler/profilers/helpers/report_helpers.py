import math

import numpy as np


def calculate_quantiles(num_quantile_groups, quantiles):
    len_quant = len(quantiles)
    if not (num_quantile_groups and 0 < num_quantile_groups <= (len_quant + 1)):
        num_quantile_groups = 4
    quant_multiplier = (len_quant + 1) / num_quantile_groups
    # quantile is one less than group
    # Goes from zero (inclusive) to number of groups (exclusive)
    # +1 because 0 + 1 * multiplier = correct first quantile
    # -1 because 0 index
    # i.e. quantile:
    # quant_multiplier = 1000 / 4 = 250
    # [0 + 1] * (quant_multiplier) - 1 = 1 * 250 - 1 = 249 (first quantile)
    quantiles = {
        ind: quantiles[math.ceil((ind + 1) * quant_multiplier) - 1]
        for ind in range(num_quantile_groups - 1)
    }
    return quantiles


def flat_dict(od, separator='_', key=''):
    """
    Function to flatten nested dictionary. Each level is collapsed and 
    joined with the specified seperator.

    :param od: dictionary or dictionary-like object
    :type od: dict
    :param seperator: character(s) joining successive levels
    :type seperator: str
    :param key: concatenated keys
    :type key: str
    :returns: unnested dictionary
    :rtype: dict
    """
    return {str(key).replace(' ','_') + separator + str(k) if key else k : v
                for kk, vv in od.items()
                    for k, v in flat_dict(vv, separator, kk).items()
           } if isinstance(od, dict) else {key:od}


def _prepare_report(report, output_format=None, omit_keys=None):
    """
    Prepares report dictionary for users upon request.

    output_format options: 

    - Pretty: floats are rounded to four decimal places & lists are shortened.
    - Compact: Similar to pretty, but removes detailed statistics such as 
               runtimes, label probabilities, index locations of null types
    - Serializable: Output is json serializable and not prettified
    - Flat: Nested output is returned as a flattened dictionary

    :param report: contains the values identified from the profile
    :type report: dict()
    :param output_format: designation for how to format the returned report;
                          possible options: pretty, serializable, flat, compact
    :type output_format: dict()
    :param omit_keys: Keys to omit from the output report, to omit keys in the 
                      report a '.' represents a level of recursion example: 
                      report: { 'test1': { 'test2': val, 'test3': val }, 
                      to omit key 'test3' from report: omit_keys=['test1.test3']
                      wildcards are also possible, so: omit_keys=['*.test3']
    :type omit_keys: list(str)
    :return report: handle to the updated report
    :type report: dict()
    """

    if output_format is not None:
        output_format = output_format.lower()
    if omit_keys is None:
        omit_keys = []

    fmt_report = {}
    max_str_len = 50
    max_array_len = 5

    if output_format == 'compact':
        omit_keys.extend([
            "data_stats.*.statistics.times",
            "data_stats.*.statistics.avg_predictions",
            "data_stats.*.statistics.data_label_representation",
            "data_stats.*.statistics.null_types_index",
            "data_stats.*.statistics.histogram"
        ])
        output_format = "pretty"

    # Modify omit_keys to account for data_stats being a list and not a dict
    # With column names for keys
    new_omit_keys = []
    for omit_key in omit_keys:
        key_list = omit_key.split(".")
        if len(key_list) > 1 and key_list[0] == "data_stats" \
                and key_list[1] != "*":
            idxs = report["global_stats"]["profile_schema"][key_list[1]]
            for i in idxs:
                swapped_list = key_list
                swapped_list[1] = str(i)
                swapped_str = ".".join(swapped_list)
                new_omit_keys.append(swapped_str)
        else:
            new_omit_keys.append(omit_key)

    omit_keys = new_omit_keys
    
    for key in report:
        
        # Remove any keys omitted
        if key in omit_keys:
            continue
        
        value = report[key]

        # Convert set to list, for report generation
        if isinstance(value, set):
            value = sorted(list(value))

        # For data_stats (in structured case), need to recurse through a list
        # As well as account for omit_keys containing indices instead of keys
        if key == "data_stats" and isinstance(value, list):
            fmt_report["data_stats"] = []
            # split off any remaining keys for the recursion
            # i.e. [test0, test1.test2] -> omit_keys => [test1.test2]
            # This will filter out all the data_stats omit keys
            data_stat_omit_keys = []
            for omit_key in omit_keys:
                omit_key_split = omit_key.split('.', 1)

                # Must have more keys left for recursion
                if len(omit_key_split) > 1:
                    next_key_layer = omit_key_split[-1]
                    prior_key_layer = omit_key_split[0]
                    if len(next_key_layer) > 0:
                        if prior_key_layer == '*' or prior_key_layer == key:
                            data_stat_omit_keys.append(next_key_layer)

            # Recurse throw indices in data_stats and call report_helper for
            # each entry
            for i in range(len(value)):
                i_index_omit_keys = []
                # Filter off data_stats omit keys depending on index
                for nl_key in data_stat_omit_keys:
                    key_split = nl_key.split(".", 1)

                    # Must have more keys left for recursion
                    if len(key_split) > 1:
                        next_key_layer = key_split[-1]
                        index = key_split[0]
                        if len(next_key_layer) > 0:
                            if (index.isdigit() and int(index) == i) \
                                    or index == "*":
                                i_index_omit_keys.append(next_key_layer)

                # Recursively prepare each column in data_stats list
                fmt_report["data_stats"].append(
                    _prepare_report(value[i], output_format, i_index_omit_keys))

        # Do not recurse or modify profile_schema
        elif key == "profile_schema":
            fmt_report[key] = value

        elif isinstance(value, dict):

            # split off any remaining keys for the recursion
            # i.e. [test0, test1.test2] -> omit_keys => [test1.test2]
            next_layer_omit_keys = []
            for omit_key in omit_keys:
                omit_key_split = omit_key.split('.', 1)
                
                # Must have more keys left for recursion 
                if len(omit_key_split) > 1: 
                    next_key_layer = omit_key_split[-1]
                    prior_key_layer = omit_key_split[0]
                    if len(next_key_layer) > 0:
                        if prior_key_layer == '*' or prior_key_layer == key:
                            next_layer_omit_keys.append(next_key_layer)

            # Recursively add keys to the final report
            fmt_report[key] = _prepare_report(value, output_format,
                                              next_layer_omit_keys)
            
        elif isinstance(value, list) or isinstance(value, np.ndarray):
            
            if output_format == "pretty":
                
                if isinstance(value, list):
                    value = np.array(value)
                    
                str_value = np.array2string(value, separator=', ')
                
                if len(str_value) > max_str_len and len(value) > max_array_len:
                    ind = 1
                    str_value = ''
                    while len(str_value) <= max_str_len:
                        str_value = \
                            np.array2string(value[:ind], separator=', ')[:-1] + \
                            ', ... , ' + \
                            np.array2string(value[-ind:], separator=', ')[1:]
                        ind += 1
                        
                fmt_report[key] = str_value
                
            elif output_format == "serializable" and isinstance(value, np.ndarray):
                fmt_report[key] = value.tolist()
            else:
                fmt_report[key] = value
                
        elif isinstance(value, float) and output_format == "pretty":
            fmt_report[key] = round(value, 4)
        else:
            fmt_report[key] = value
            
    if output_format == 'flat':
        fmt_report = flat_dict(fmt_report)

    return fmt_report
