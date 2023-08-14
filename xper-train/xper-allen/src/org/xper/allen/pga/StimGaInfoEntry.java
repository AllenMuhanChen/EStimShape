package org.xper.allen.pga;

public class StimGaInfoEntry {
    private long stimId;
    private long parentId;
    private long lineageId;
    private String stimType;
    private double response;
    private Double mutationMagnitude; // Using Double to allow for null values

    // Constructor
    public StimGaInfoEntry(long stimId, long parentId, long lineageId, String stimType, double response, Double mutationMagnitude) {
        this.stimId = stimId;
        this.parentId = parentId;
        this.lineageId = lineageId;
        this.stimType = stimType;
        this.response = response;
        this.mutationMagnitude = mutationMagnitude;
    }

    public long getStimId() {
        return stimId;
    }

    public void setStimId(long stimId) {
        this.stimId = stimId;
    }

    public long getParentId() {
        return parentId;
    }

    public void setParentId(long parentId) {
        this.parentId = parentId;
    }

    public long getLineageId() {
        return lineageId;
    }

    public void setLineageId(long lineageId) {
        this.lineageId = lineageId;
    }

    public String getStimType() {
        return stimType;
    }

    public void setStimType(String stimType) {
        this.stimType = stimType;
    }

    public double getResponse() {
        return response;
    }

    public void setResponse(double response) {
        this.response = response;
    }

    public Double getMutationMagnitude() {
        return mutationMagnitude;
    }

    public void setMutationMagnitude(Double mutationMagnitude) {
        this.mutationMagnitude = mutationMagnitude;
    }
}