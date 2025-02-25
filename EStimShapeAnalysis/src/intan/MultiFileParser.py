import os
from typing import Dict, List, Set, Tuple, Any
from clat.intan.one_file_spike_parsing import OneFileParser


class MultiFileParser:
    sample_rate: int = None

    def __init__(self):
        self.one_file_parser = OneFileParser()

    def parse(self, task_ids: List[int], intan_files_dir: str) -> Tuple[Dict[int, Any], Dict[int, Any]]:
        """
        Parse multiple Intan files and combine their data for specified task IDs.

        Args:
            task_ids: List of task IDs to look for

        Returns:
            Tuple containing:
            - Dictionary mapping task IDs to channel spike data
            - Dictionary mapping task IDs to epoch times
            - Sample rate
        """
        # Convert task_ids to set for efficient lookup
        task_id_set = set(task_ids)

        # Find relevant files
        matching_dirs = self.find_files_containing_task_ids(task_id_set, intan_files_dir)

        if not matching_dirs:
            raise ValueError(f"No files found containing task IDs {task_ids}")

        # Initialize combined results
        spikes_by_channel_by_task_id = {}
        epochs_by_task_id = {}
        sample_rate = None

        # Process each matching directory
        for dir_path in matching_dirs:

            spikes_by_channel, epoch_times, file_sample_rate = self.one_file_parser.parse(dir_path)

            # Set sample rate from first file
            if sample_rate is None:
                self.sample_rate = file_sample_rate
            elif file_sample_rate != sample_rate:
                raise ValueError(f"Inconsistent sample rates: {sample_rate} vs {file_sample_rate}")

            # Combine results
            for task_id, channel_data in spikes_by_channel.items():
                if task_id in task_id_set:
                    spikes_by_channel_by_task_id[task_id] = channel_data
                    epochs_by_task_id[task_id] = epoch_times[task_id]

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
