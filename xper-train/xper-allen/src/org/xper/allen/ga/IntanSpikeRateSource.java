package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.intan.read.SpikeReader;

import java.io.File;
import java.io.FileFilter;
import java.util.LinkedList;
import java.util.List;

public class IntanSpikeRateSource implements SpikeRateSource {

    @Dependency
    String spikeDatDirectory;

    @Dependency
    List<String> channels;

    @Override
    public List<Double> getSpikeRates(Long taskId){
        String spikeDatPath = getSpikeDatPathFor(taskId);
        return getCombinedSpikeRatesFrom(spikeDatPath);
    }

    private String getSpikeDatPathFor(Long stimId) {
        File dir = new File(spikeDatDirectory);
        File[] matchingSpikeDats = dir.listFiles(new FileFilter() {
            @Override
            public boolean accept(File pathname) {
                return pathname.getName().contains(stimId + "_");
            }
        });
        if (matchingSpikeDats.length == 1){
            return matchingSpikeDats[0].getAbsolutePath() + "/spike.dat";
        } else{
            throw new IllegalArgumentException("There's either none or too many" +
                    "spike.dat files matching the stimId: " + stimId);
        }
    }

    private List<Double> getCombinedSpikeRatesFrom(String spikeDatPath) {
        SpikeReader spikeReader = new SpikeReader(spikeDatPath);
        List<Double> spikeRates = new LinkedList<>();
        for (String channel:channels){
            spikeRates.add(spikeReader.getSpikeRate(channel));
        }
        return spikeRates;
    }

    public void setChannels(List<String> channels) {
        this.channels = channels;
    }

    public String getSpikeDatDirectory() {
        return spikeDatDirectory;
    }

    public void setSpikeDatDirectory(String spikeDatDirectory) {
        this.spikeDatDirectory = spikeDatDirectory;
    }

    public List<String> getChannels() {
        return channels;
    }
}
