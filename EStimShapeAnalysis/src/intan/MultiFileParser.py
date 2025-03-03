import os
from typing import Dict, List, Set, Tuple, Any
from clat.intan.one_file_spike_parsing import OneFileParser


class MultiFileParser:
    """
    Given a list of task Ids, this class will parse all intan files that contain those task_ids.
    The parsed data will be combined and returned in a dictionary.

    The data is returned in two dictionaries:
    - spikes_by_channel_by_task_id:
        - spikes_by_channel is a dictionary where the key is the channel (str) and the value is a list of spike times.
        - spikes_by_channel_by_task_id is a dictionary where the key is the task_id (int) and the value is the spikes_by_channel dictionary.
    - epochs_by_task_id is a dictionary where the key is the task_id (int) and the value is a list of epoch times (tuple: (start_time, stop_time)).

    if to_cache is True:
        - the parsed data will be saved in a cache directory.
        - when parse is called and there is already cached data, data for the requested task_ids will be loaded from cache where it exists.
            any non-cached task_ids will be parsed from the intan files.
    """
    sample_rate: int = None

    def __init__(self, to_cache: bool = False, cache_dir: str = None):
        self.one_file_parser = OneFileParser()
        self.to_cache = to_cache
        self.cache_dir = cache_dir

    def parse(self, task_ids: List[int], intan_files_dir: str) -> Tuple[Dict[int, Any], Dict[int, Any]]:
        """
        Parse multiple Intan files and combine their data for specified task IDs.

        Args:
            task_ids: List of task IDs to look for
            intan_files_dir: Directory containing Intan files

        Returns:
            Tuple containing:
            - Dictionary mapping task IDs to channel spike data
            - Dictionary mapping task IDs to epoch times
        """
        # Initialize combined results
        spikes_by_channel_by_task_id = {}
        epochs_by_task_id = {}

        task_id_set = set(task_ids)
        remaining_task_ids = list(task_id_set)  # Default to processing all task IDs

        # If cache is enabled, check if the data is already cached
        if self.to_cache and self.cache_dir is not None:
            # Load what we can from cache
            cached_spikes, cached_epochs, missing_task_ids = self._load_cache(task_ids)

            # Update our results with what we found in the cache
            spikes_by_channel_by_task_id.update(cached_spikes)
            epochs_by_task_id.update(cached_epochs)

            # If all task IDs were found in the cache, return the cached data
            if not missing_task_ids:
                print(f"All requested task IDs {task_ids} found in cache.")
                return spikes_by_channel_by_task_id, epochs_by_task_id

            # Otherwise, update the list of task IDs we still need to process
            remaining_task_ids = missing_task_ids
            print(
                f"Found {len(task_id_set) - len(missing_task_ids)} task IDs in cache. Still need to process: {missing_task_ids}")

        # Find relevant files for remaining task IDs
        remaining_task_id_set = set(remaining_task_ids)
        matching_dirs = self.find_files_containing_task_ids(remaining_task_id_set, intan_files_dir)

        if not matching_dirs:
            if spikes_by_channel_by_task_id:  # If we have some data from cache
                print(f"No files found for remaining task IDs {remaining_task_ids}. Returning partial data from cache.")
                return spikes_by_channel_by_task_id, epochs_by_task_id
            else:
                raise ValueError(f"No files found containing task IDs {task_ids}")

        # Create separate dictionaries for newly parsed data
        new_spikes_by_channel_by_task_id = {}
        new_epochs_by_task_id = {}

        # Process each matching directory
        for dir_path in matching_dirs:
            spikes_by_channel, epoch_times, file_sample_rate = self.one_file_parser.parse(dir_path)

            # Set sample rate from first file
            if self.sample_rate is None:
                self.sample_rate = file_sample_rate
            elif file_sample_rate != self.sample_rate:
                raise ValueError(f"Inconsistent sample rates: {self.sample_rate} vs {file_sample_rate}")

            # Combine results in both the complete result set and the new data set
            for task_id, channel_data in spikes_by_channel.items():
                if task_id in remaining_task_id_set:
                    # Add to the complete result set
                    spikes_by_channel_by_task_id[task_id] = channel_data
                    epochs_by_task_id[task_id] = epoch_times[task_id]

                    # Also add to the new data set (what we will cache)
                    new_spikes_by_channel_by_task_id[task_id] = channel_data
                    new_epochs_by_task_id[task_id] = epoch_times[task_id]

        # Cache results if requested - only cache newly parsed data
        if self.to_cache and self.cache_dir is not None and new_spikes_by_channel_by_task_id:
            self._cache(new_spikes_by_channel_by_task_id, new_epochs_by_task_id)

        return spikes_by_channel_by_task_id, epochs_by_task_id

    def find_files_containing_task_ids(self, task_ids: Set[int], intan_files_dir: str) -> List[str]:
        """Find all Intan file directories that contain any of the specified task IDs."""
        matching_dirs = []

        for dir_name in os.listdir(intan_files_dir):
            dir_path = os.path.join(intan_files_dir, dir_name)
            if not os.path.isdir(dir_path):
                continue

            notes_path = os.path.join(dir_path, "notes.txt")
            if not os.path.exists(notes_path):
                continue

            try:
                with open(notes_path, 'r') as f:
                    notes_content = f.read()

                # Parse notes file to find task IDs
                for line in notes_content.strip().split('\n\n'):
                    try:
                        parts = line.split(',')
                        if len(parts) >= 3:
                            event = parts[2].strip()
                            try:
                                file_task_id = int(event)
                                if file_task_id in task_ids:
                                    matching_dirs.append(dir_path)
                                    break  # Found a match, no need to check rest of file
                            except ValueError:
                                continue  # Not a task ID
                    except IndexError:
                        continue
            except Exception as e:
                print(f"Error reading notes file {notes_path}: {e}")

        return matching_dirs

    def _cache(self, spikes_by_channel_by_task_id: Dict[int, Any], epochs_by_task_id: Dict[int, Any]) -> str:
        """
        Cache the parsed spike data and epoch times to a pickle file.

        Args:
            spikes_by_channel_by_task_id: Dictionary mapping task IDs to channel spike data
            epochs_by_task_id: Dictionary mapping task IDs to epoch times

        Returns:
            Path to the created cache file

        Raises:
            ValueError: If cache_dir is not set
            IOError: If the directory does not exist or file cannot be written
        """
        import pickle
        import os

        if self.cache_dir is None:
            raise ValueError("Cache directory not set. Initialize with cache_dir parameter.")

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        # Extract task IDs from the epochs dictionary and sort them
        task_ids = list(epochs_by_task_id.keys())
        sorted_task_ids = sorted(task_ids)

        # Create filename based on the first and last task IDs
        if not sorted_task_ids:
            raise ValueError("No task IDs found in the provided data")

        filename = f"{sorted_task_ids[0]}_to_{sorted_task_ids[-1]}_parsed_spikes_and_epochs.pkl"
        file_path = os.path.join(self.cache_dir, filename)

        # Prepare data to be cached
        cache_data = {
            'spikes_by_channel_by_task_id': spikes_by_channel_by_task_id,
            'epochs_by_task_id': epochs_by_task_id,
            'sample_rate': self.sample_rate,
            'task_ids': sorted_task_ids
        }

        # Save to pickle file
        with open(file_path, 'wb') as f:
            pickle.dump(cache_data, f)

        return file_path

    def _load_cache(self, task_ids: List[int]) -> Tuple[Dict[int, Any], Dict[int, Any], List[int]]:
        """
        Load cached data for the specified task IDs.

        Args:
            task_ids: List of task IDs to find in cache

        Returns:
            Tuple containing:
            - Dictionary mapping task IDs to channel spike data
            - Dictionary mapping task IDs to epoch times
            - List of task IDs that were not found in the cache
        """
        import pickle
        import os
        import glob

        if not os.path.exists(self.cache_dir):
            return {}, {}, task_ids

        # Get a list of all cache files
        cache_files = glob.glob(os.path.join(self.cache_dir, "*_parsed_spikes_and_epochs.pkl"))

        # Initialize the results
        combined_spikes = {}
        combined_epochs = {}
        missing_task_ids = list(task_ids)  # Start with all task IDs marked as missing

        # Check each cache file
        for cache_file in cache_files:
            try:
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)

                # Check which of our requested task_ids are in this cache file
                cached_task_ids = cache_data.get('task_ids', [])

                # Update sample rate if we don't have one yet
                if self.sample_rate is None and 'sample_rate' in cache_data:
                    self.sample_rate = cache_data['sample_rate']
                elif self.sample_rate is not None and cache_data.get('sample_rate') != self.sample_rate:
                    print(f"Warning: Inconsistent sample rates in cache files. Expected {self.sample_rate}, "
                          f"found {cache_data.get('sample_rate')} in {cache_file}")
                    continue  # Skip this cache file due to sample rate mismatch

                # Extract data for any of our requested task IDs that are in this cache
                spikes_data = cache_data.get('spikes_by_channel_by_task_id', {})
                epochs_data = cache_data.get('epochs_by_task_id', {})

                for task_id in task_ids:
                    if task_id in cached_task_ids and task_id in spikes_data and task_id in epochs_data:
                        combined_spikes[task_id] = spikes_data[task_id]
                        combined_epochs[task_id] = epochs_data[task_id]

                        # Remove from missing list if it's there
                        if task_id in missing_task_ids:
                            missing_task_ids.remove(task_id)

            except Exception as e:
                print(f"Error reading cache file {cache_file}: {e}")
                continue

        return combined_spikes, combined_epochs, missing_task_ids
