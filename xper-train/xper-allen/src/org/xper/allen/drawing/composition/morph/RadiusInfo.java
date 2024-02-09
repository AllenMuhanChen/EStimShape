package org.xper.allen.drawing.composition.morph;

public class RadiusInfo {
    Double radius;
    Integer uNdx;
    NormalDistributedComponentMorphParameters.RADIUS_TYPE radiusType;
    Boolean preserve;

    public RadiusInfo(Double radius, Integer uNdx, NormalDistributedComponentMorphParameters.RADIUS_TYPE radiusType, Boolean preserve) {
        this.radius = radius;
        this.uNdx = uNdx;
        this.radiusType = radiusType;
        this.preserve = preserve;
    }

    public RadiusInfo(RadiusInfo oldRadiusInfo, Double newRadius) {
        this.radius = newRadius;
        this.uNdx = oldRadiusInfo.getuNdx(); //not needed?
        this.radiusType = oldRadiusInfo.getRadiusType();
        this.preserve = oldRadiusInfo.getPreserve(); //not needed?
    }

    public Double getRadius() {
        return radius;
    }

    public void setRadius(Double radius) {
        this.radius = radius;
    }

    public Integer getuNdx() {
        return uNdx;
    }

    public void setuNdx(Integer uNdx) {
        this.uNdx = uNdx;
    }

    public NormalDistributedComponentMorphParameters.RADIUS_TYPE getRadiusType() {
        return radiusType;
    }

    public void setRadiusType(NormalDistributedComponentMorphParameters.RADIUS_TYPE radiusType) {
        this.radiusType = radiusType;
    }

    public Boolean getPreserve() {
        return preserve;
    }

    public void setPreserve(Boolean preserve) {
        this.preserve = preserve;
    }
}