package org.xper.intan.read;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class SpikeReader {

    private static InputStream inputStream;
    double sampleRate;
    int samplesPreDetect;
    int samplesPostDetect;
    private String spikeDatPath;
    int magicNumber;
    int spikeFileVersionNumber;
    String filename;
    List<String> channelList;
    List<String> customChannelList;

    Map<String, List<Spike>> spikesForChannel = new LinkedHashMap<>();

    private int snapshots_present;
    private int nSamples;

    public SpikeReader(String spikeDatPath) {
        this.spikeDatPath = spikeDatPath;
        try {
            inputStream = new FileInputStream(this.spikeDatPath);
        } catch (FileNotFoundException e) {
            throw new RuntimeException(e);
        }
    }

    public double getSpikeRate(String channelName) {
        List<Spike> spikes = spikesForChannel.get(channelName);
        double elapsedTime = spikes.get(spikes.size() - 1).tstampSeconds - spikes.get(0).tstampSeconds;

        return spikes.size()/ elapsedTime;
    }

    public void readSpikeFile(){
        try {
            magicNumber = readUInt32();
            spikeFileVersionNumber = readUInt16();
            filename = readString();
            channelList = readList();
            customChannelList = readList();
            sampleRate = readSingle();
            samplesPreDetect = readUInt32();
            samplesPostDetect = readUInt32();

            while(inputStream.available()>0){
                String channelName;
                if(isMultiChannel()){
                    channelName = readNextNChars(5);
                } else{
                    channelName = "Single Channel";
                }
                spikesForChannel.putIfAbsent(channelName, new ArrayList<>());

                int timestamp = readInt32();
                byte spikeId = readUInt8();

                List<Double> snapshot = new LinkedList<>();
                if(snapshotsPresent()){
                    for (int i =0;i<nSamples; i++) {
                        snapshot.add(readMicrovolts());
                    }
                }
                double tstampSeconds = timestamp / sampleRate;
                Spike spike = new Spike(tstampSeconds, spikeId, snapshot);
                spikesForChannel.get(channelName).add(spike);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private double readMicrovolts() {
        return 0.195 * (readUInt16() - 32768);
    }

    private String readNextNChars(int N) throws IOException {
        StringBuilder stringBuilder = new StringBuilder();
        for (int i = 0; i< N; i++){
            stringBuilder.append(nextChar());
        }
        String channelName = stringBuilder.toString();
        return channelName;
    }

    private boolean isMultiChannel() {
        boolean multichannel;
        if(magicNumber == 418924363)
            return true;
        else if(magicNumber == 418941952)
            return false;
        else
            throw new IllegalArgumentException("Unrecognized file type");
    }

    private boolean snapshotsPresent() {
        nSamples = samplesPostDetect + samplesPreDetect;
        if(nSamples ==0)
            return false;
        else
            return true;
    }

    private float readSingle() {
        byte[] bytes = new byte[4];
        try {
            inputStream.read(bytes);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        ByteBuffer byteBuffer = ByteBuffer.wrap(bytes);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN);
        return byteBuffer.getFloat();
    }

    public int readInt32() {
        byte[] bytes = new byte[4];
        try {
            inputStream.read(bytes);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        ByteBuffer byteBuffer = ByteBuffer.wrap(bytes);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN);
        return byteBuffer.getInt();
    }


    public int readUInt32() {
        byte[] bytes = new byte[4];
        try {
            inputStream.read(bytes);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        ByteBuffer byteBuffer = ByteBuffer.wrap(bytes);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN);
        return byteBuffer.getInt();
    }

    public int readUInt16(){
        byte[] bytes = new byte[2];
        try {
            inputStream.read(bytes);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        ByteBuffer byteBuffer = ByteBuffer.wrap(bytes);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN);
        return byteBuffer.getShort();

    }

    public byte readUInt8(){
        byte[] bytes = new byte[1];
        try {
            inputStream.read(bytes);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        ByteBuffer byteBuffer = ByteBuffer.wrap(bytes);
        byteBuffer.order(ByteOrder.LITTLE_ENDIAN);
        return byteBuffer.get();

    }

    private List<String> readList() {
        return Arrays.asList(readString().split(","));
    }

    private String readString()  {
        StringBuilder str = new StringBuilder();

        try {
            char nextChar = nextChar();
            while (nextChar != 0) {
                str.append(nextChar);
                nextChar = nextChar();
            }
        } catch (Exception e){
            e.printStackTrace();
        }
        return str.toString();
    }

    private char nextChar() throws IOException {
        byte[] nextCharBytes = new byte[1];
        inputStream.read(nextCharBytes);
        ByteBuffer byteBuffer = ByteBuffer.wrap(nextCharBytes);

        String str = new String(byteBuffer.array(), StandardCharsets.UTF_8);
        return str.charAt(0);
    }
}
