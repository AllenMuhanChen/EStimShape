import os

from src.intan.MultiFileParser import MultiFileParser

# Set test variables
TEST_DIR = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/allen_ga_train_250116_0/ga/2025-01-24"  # Replace with your test directory
TEST_TASK_IDS = [1737741565294637, 1737742682009219]  # Replace with your test task IDs


def test_find_files_containing_task_ids():
    parser = MultiFileParser()
    matching_dirs = parser.find_files_containing_task_ids(set(TEST_TASK_IDS), TEST_DIR)
    print(matching_dirs)
    # Verify directories exist
    assert len(matching_dirs) > 0, "No matching directories found"

    # Verify each directory has required files
    for dir_path in matching_dirs:
        assert os.path.exists(os.path.join(dir_path, "notes.txt")), f"Missing notes.txt in {dir_path}"
        assert os.path.exists(os.path.join(dir_path, "amplifier.dat")), f"Missing amplifier.dat in {dir_path}"
        assert os.path.exists(os.path.join(dir_path, "digitalin.dat")), f"Missing digitalin.dat in {dir_path}"


def test_parse():
    parser = MultiFileParser()
    spikes_by_channel, epoch_times = parser.parse(TEST_TASK_IDS, TEST_DIR)

    # Verify data structure
    assert isinstance(spikes_by_channel, dict), "spikes_by_channel should be a dictionary"
    assert isinstance(epoch_times, dict), "epoch_times should be a dictionary"


    # Verify data content
    for task_id in TEST_TASK_IDS:
        if task_id in spikes_by_channel:
            assert len(spikes_by_channel[task_id]) > 0, f"No spike data for task_id {task_id}"
            assert task_id in epoch_times, f"Missing epoch times for task_id {task_id}"