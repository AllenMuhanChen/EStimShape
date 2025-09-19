from spikeinterface.sorters import run_sorter
import spikeinterface.extractors as se

test_recording, _ = se.toy_example(
    duration=30,
    seed=0,
    num_channels=64,
    num_segments=1
)
test_recording = test_recording.save(folder="test-docker-folder", overwrite=True)

sorting = run_sorter(sorter_name="kilosort3",
                     recording=test_recording,
                     folder="kilosort3",
                     docker_image=True
                     )


print(sorting)
