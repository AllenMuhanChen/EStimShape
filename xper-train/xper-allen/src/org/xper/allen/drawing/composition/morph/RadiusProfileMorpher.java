package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RADIUS_TYPE;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusInfo;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusProfile;

import java.util.*;
import java.util.function.BiConsumer;

public class RadiusProfileMorpher {

    public RadiusProfile morphRadiusProfile(RadiusProfile oldRadiusProfile, Double length, Double curvature, Double radiusProfileMagnitude){
        Map<Integer, RadiusInfo> oldRadiusInfoForPoints = oldRadiusProfile.getInfoForRadius();

        Map<Integer, Double> normalizedMagnitudeForRadii =
                distributeMagnitudeToRadiiAndNormalize(radiusProfileMagnitude, oldRadiusInfoForPoints);

        // Use the radius points' associated normalized magnitudes to change the radius points
        RadiusProfile newRadiusProfile = pickNewRadii(oldRadiusInfoForPoints, normalizedMagnitudeForRadii, length, curvature);

        return newRadiusProfile;
    }

    private Map<Integer, Double> distributeMagnitudeToRadiiAndNormalize(double radiusProfileMagnitude, Map<Integer, RadiusInfo> radiusInfoForPoints) {
        int numPoints = radiusInfoForPoints.size();
        double maxToDistributeToSingleRadius = 1.0 / numPoints;

        List<Map.Entry<Integer, RadiusInfo>> radiusInfosForPointList = new ArrayList<>(radiusInfoForPoints.entrySet());


        Map<Integer, Double> normalizedMagnitudeForRadii = new HashMap<>();
        for (Map.Entry<Integer, RadiusInfo> radiusInfoForPoint : radiusInfosForPointList) {
            normalizedMagnitudeForRadii.put(radiusInfoForPoint.getKey(), 0.0);
        }
        double amountLeftToDistribute = radiusProfileMagnitude;
        while (Math.round(amountLeftToDistribute * 100000.0)/ 100000.0 > 0){
            Collections.shuffle(radiusInfosForPointList);
            for (Map.Entry<Integer, RadiusInfo> radiusInfoForPoint : radiusInfosForPointList) {
                double normalizedRandomMagnitude = Math.random() * radiusProfileMagnitude / numPoints;
                // If the random magnitude is greater than the amount left to distribute, then we need to
                // reduce the magnitude to the amount left to distribute
                if (normalizedRandomMagnitude > amountLeftToDistribute) {
                    normalizedRandomMagnitude = amountLeftToDistribute;

                }
                // If adding the random magnitude to the current magnitude would exceed the max, then we need to
                // reduce the magnitude to the amount that would bring the current magnitude to the max
                if (normalizedMagnitudeForRadii.get(radiusInfoForPoint.getKey()) + normalizedRandomMagnitude > maxToDistributeToSingleRadius) {
                    normalizedRandomMagnitude = maxToDistributeToSingleRadius - normalizedMagnitudeForRadii.get(radiusInfoForPoint.getKey());
                }
                normalizedMagnitudeForRadii.put(radiusInfoForPoint.getKey(), normalizedMagnitudeForRadii.get(radiusInfoForPoint.getKey()) + normalizedRandomMagnitude);
                amountLeftToDistribute -= normalizedRandomMagnitude;
                System.out.println("Amount left to distribute to radii: " + amountLeftToDistribute);
            }
        }
        return normalizedMagnitudeForRadii;
    }

    private RadiusProfile pickNewRadii(Map<Integer, RadiusInfo> oldRadiusInfoForPoints, Map<Integer, Double> normalizedMagnitudeForRadii, Double length, Double curvature) {
        RadiusProfile newRadiusProfile = new RadiusProfile();
        HashMap<Object, Object> newRadiusInfoForPoints = new HashMap<>();
        oldRadiusInfoForPoints.forEach(new BiConsumer<Integer, RadiusInfo>() {
            @Override
            public void accept(Integer pointIndex, RadiusInfo oldRadiusInfo) {
                double normalizedMagnitude = normalizedMagnitudeForRadii.get(pointIndex);
                RADIUS_TYPE radiusType = oldRadiusInfo.getRadiusType();
                double MIN_RADIUS;
                double MAX_RADIUS;
                if (radiusType == RADIUS_TYPE.JUNCTION) {
                    MIN_RADIUS = length / 10.0;
                    MAX_RADIUS = Math.min(length / 3.0, 0.5 * (1/ curvature));
                }
                else if (radiusType == RADIUS_TYPE.ENDPT) {
                    MIN_RADIUS = 0.00001;
                    MAX_RADIUS = Math.min(length / 3.0, 0.5 * (1/ curvature));
                }
                else if (radiusType == RADIUS_TYPE.MIDPT) {
                    MIN_RADIUS = length / 10.0;
                    MAX_RADIUS = Math.min(length / 3.0, 0.5 * (1/ curvature));
                }
                else {
                    throw new RuntimeException("Invalid radius type");
                }

                ValueShifter1D converter = new ValueShifter1D(MIN_RADIUS, MAX_RADIUS);
                double newRadius = converter.convert(normalizedMagnitude, oldRadiusInfo.getRadius());

                RadiusInfo newRadiusInfo = new RadiusInfo(oldRadiusInfo, newRadius);
                newRadiusProfile.addRadiusInfo(pointIndex, newRadiusInfo);
            }
        });
        return newRadiusProfile;
    }
}