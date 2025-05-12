import numpy as np


class SpikeRateSortingUtils:
    """
    Utility class for creating various types of sorting functions.
    """

    @staticmethod
    def by_avg_value(column, comparison_col=None, ascending=False, limit=None):
        """
        Create a sorting function that sorts based on the max average value in another column.

        Args:
            column: The column containing the values to average
            comparison_col: Optional column to average within groups in this col. Will sort based on max
             between these groups.
            ascending: Whether to sort in ascending order
            limit: Optional maximum number of values to return (None returns all values)

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of the average value for each item
            lookup = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                if filtered.empty or column not in filtered.columns:
                    lookup[value] = 0
                    continue

                if comparison_col:
                    # If we have a grouping column, calculate average within each group first,
                    # then take the maximum average across groups
                    groups = filtered[comparison_col].unique()
                    group_avgs = []

                    for group in groups:
                        group_data = filtered[filtered[comparison_col] == group]
                        if not group_data.empty:
                            group_avg = group_data[column].mean()
                            group_avgs.append(group_avg)

                    # Use the maximum average across groups
                    lookup[value] = max(group_avgs) if group_avgs else 0
                else:
                    # Otherwise, just find the average value
                    lookup[value] = filtered[column].mean()

            # Sort based on the lookup values
            sorted_values = sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)

            # Apply limit if specified
            if limit is not None and limit > 0:
                sorted_values = sorted_values[:limit]

            # Print debug info
            print(f"\nSorting {sort_col} by average values of {column}:")
            for value in sorted_values:
                print(f"{value}: {lookup.get(value, 0):.4f}")

            return sorted_values

        return sorter

    @staticmethod
    def by_max_avg_difference(column, group_col, ascending=False):
        """
        Create a sorting function that sorts based on the maximum difference
        between group averages.

        Args:
            column: The column containing the values to analyze
            group_col: Column used to group by before finding averages
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of the max difference for each item
            lookup = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                if filtered.empty or column not in filtered.columns:
                    lookup[value] = 0
                    continue

                # If we have a grouping column, calculate averages within each group
                if group_col:
                    groups = filtered[group_col].unique()
                    group_avgs = {}

                    # Calculate average for each group
                    for group in groups:
                        group_data = filtered[filtered[group_col] == group]
                        if not group_data.empty:
                            group_avgs[group] = group_data[column].mean()

                    # Find the maximum difference between any two group averages
                    if len(group_avgs) >= 2:
                        # Get all pairs of groups and find max difference
                        import itertools
                        max_diff = 0
                        for g1, g2 in itertools.combinations(group_avgs.keys(), 2):
                            diff = abs(group_avgs[g1] - group_avgs[g2])
                            max_diff = max(max_diff, diff)
                        lookup[value] = max_diff
                    else:
                        lookup[value] = 0
                else:
                    # If no grouping, just use the std dev as a measure of difference
                    lookup[value] = filtered[column].std() if len(filtered) > 1 else 0

            # Sort based on the lookup values
            sorted_values = sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)

            # Print debug info
            print(f"\nSorting {sort_col} by maximum average differences in {column}:")
            for value in sorted_values:
                print(f"{value}: {lookup.get(value, 0):.4f}")

            return sorted_values

        return sorter

    @staticmethod
    def by_column_value(column, ascending=True):
        """
        Create a sorting function that sorts based on values in another column.

        Args:
            column: The column to use for sorting
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, _):
            # Create a lookup of the first value for each item
            lookup = {}
            for value in values:
                matches = data[data[_] == value]
                if not matches.empty and column in matches.columns:
                    lookup[value] = matches[column].iloc[0]

            # Sort based on the lookup values
            return sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)

        return sorter

    @staticmethod
    def by_max_value(column, group_col=None, ascending=False):
        """
        Create a sorting function that sorts based on the maximum value in another column.

        Args:
            column: The column containing the values to maximize
            group_col: Optional column to group by before finding max
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of the max value for each item
            lookup = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                if group_col:
                    # If we have a grouping column, calculate max within each group
                    groups = filtered[group_col].unique()
                    max_val = 0

                    for group in groups:
                        group_data = filtered[filtered[group_col] == group]
                        if column in group_data.columns:
                            group_max = group_data[column].max()
                            max_val = max(max_val, group_max)

                    lookup[value] = max_val
                else:
                    # Otherwise, just find the max value
                    if column in filtered.columns:
                        lookup[value] = filtered[column].max()
                    else:
                        lookup[value] = 0

            # Sort based on the lookup values
            sorted_values = sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)
            # print values:
            for value in sorted_values:
                print(value, lookup.get(value, 0))
            return sorted_values

        return sorter

    @staticmethod
    def by_aggregation(column, agg_func, group_col=None, ascending=False):
        """
        Create a sorting function based on an aggregation of values.

        Args:
            column: The column containing the values to aggregate
            agg_func: Function to aggregate values (e.g., np.mean, np.max, np.sum)
            group_col: Optional column to group by before aggregating
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of the aggregated value for each item
            lookup = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                if group_col:
                    # If we have a grouping column, calculate aggregates within each group
                    groups = filtered[group_col].unique()
                    agg_values = []

                    for group in groups:
                        group_data = filtered[filtered[group_col] == group]
                        if column in group_data.columns:
                            agg_values.append(agg_func(group_data[column].values))

                    # Aggregate across groups if we have any values
                    if agg_values:
                        lookup[value] = agg_func(agg_values)
                    else:
                        lookup[value] = 0
                else:
                    # Otherwise, just aggregate all values
                    if column in filtered.columns:
                        lookup[value] = agg_func(filtered[column].values)
                    else:
                        lookup[value] = 0

            # Sort based on the lookup values
            return sorted(values, key=lambda x: lookup.get(x, 0), reverse=not ascending)

        return sorter

    @staticmethod
    def by_difference(column, group_col, value1, value2, absolute=True, ascending=False):
        """
        Create a sorting function based on the difference between two grouped values.

        Args:
            column: The column containing the values to compare
            group_col: Column used to differentiate the two values to compare
            value1: First value in the group_col to use
            value2: Second value in the group_col to use
            absolute: Whether to use absolute difference
            ascending: Whether to sort in ascending order

        Returns:
            A sorting function
        """

        def sorter(values, data, sort_col):
            # Create a lookup of differences
            differences = {}

            for value in values:
                # Filter data for this value
                filtered = data[data[sort_col] == value]

                # Get values for the two groups
                group1_data = filtered[filtered[group_col] == value1]
                group2_data = filtered[filtered[group_col] == value2]

                # Calculate difference if we have both groups
                if not group1_data.empty and not group2_data.empty and column in filtered.columns:
                    val1 = group1_data[column].mean()
                    val2 = group2_data[column].mean()
                    diff = val2 - val1

                    if absolute:
                        differences[value] = abs(diff)
                    else:
                        differences[value] = diff
                else:
                    differences[value] = 0

            # Sort based on differences
            return sorted(values, key=lambda x: differences.get(x, 0), reverse=not ascending)

        return sorter
