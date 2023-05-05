read_Intan_spike_file()

channels = [0,15];
timeElapsed = spikes{channels(1)+1,3}(end) - spikes{channels(1)+1,3}(1);

spikeRate=0;
for i=1:1:length(channels)
    spikeRate = spikeRate + length(spikes{channels(i)+1,3})/timeElapsed;
end 

spikeRate


