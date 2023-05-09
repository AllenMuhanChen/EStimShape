package org.xper.allen.drawing.composition.morph;

import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RADIUS_TYPE;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusInfo;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusProfile;

import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.BiConsumer;

public class RadiusProfileMorpher {

    public RadiusProfile morphRadiusProfile(RadiusProfile oldRadiusProfile, Double length, Double curvature, Double radiusProfileMagnitude){
        Map<Integer, RadiusInfo> oldRadiusInfoForPoints = oldRadiusProfile.getInfoForRadius();

        Map<Integer, Double> normalizedMagnitudeForRadii =
                distributeMagnitudeToRadiiAndNormalize(radiusProfileMagnitude, oldRadiusInfoForPoints);

        // Use the radius points' associated normalized magnitudes to change the radius points

        return pickNewRadii(oldRadiusInfoForPoints, normalizedMagnitudeForRadii, length, curvature);
    }

    private Map<Integer, Double> distributeMagnitudeToRadiiAndNormalize(double radiusProfileMagnitude, Map<Integer, RadiusInfo> radiusInfoForPoints) {
        List<Map.Entry<Integer, RadiusInfo>> radiusInfosForPointList = new ArrayList<>(radiusInfoForPoints.entrySet());


        Map<Integer, AtomicReference<Double>> magnitudesForPointsToDistributeTo = new HashMap<>();
        for (Map.Entry<Integer, RadiusInfo> radiusInfoForPoint : radiusInfosForPointList) {
            magnitudesForPointsToDistributeTo.put(radiusInfoForPoint.getKey(), new AtomicReference<>(0.0));
        }
        NormalMorphDistributer normalMorphDistributer = new NormalMorphDistributer(1/3.0);
        normalMorphDistributer.distributeMagnitudeTo(magnitudesForPointsToDistributeTo.values(), radiusProfileMagnitude);

        Map<Integer, Double> output = new HashMap<>();
        magnitudesForPointsToDistributeTo.forEach(new BiConsumer<Integer, AtomicReference<Double>>() {
            @Override
            public void accept(Integer pointIndex, AtomicReference<Double> magnitude) {
                output.put(pointIndex, magnitude.get());
            }
        });

        return output;
    }

    private RadiusProfile pickNewRadii(Map<Integer, RadiusInfo> oldRadiusInfoForPoints, Map<Integer, Double> normalizedMagnitudeForRadii, Double length, Double curvature) {
        RadiusProfile newRadiusProfile = new RadiusProfile();
        HashMap<Object, Object> newRadiusInfoForPoints = new HashMap<>();
        try {
            oldRadiusInfoForPoints.forEach(new BiConsumer<Integer, RadiusInfo>() {
                @Override
                public void accept(Integer pointIndex, RadiusInfo oldRadiusInfo) {
                    double normalizedMagnitude = normalizedMagnitudeForRadii.get(pointIndex);
                    RADIUS_TYPE radiusType = oldRadiusInfo.getRadiusType();
                    double MIN_RADIUS;
                    double MAX_RADIUS;
                    if (radiusType == RADIUS_TYPE.JUNCTION) {
                        MIN_RADIUS = length / 10.0;
                        MAX_RADIUS = Math.min(length / 3.0, 0.5 * (1 / curvature));
                    } else if (radiusType == RADIUS_TYPE.ENDPT) {
                        MIN_RADIUS = 0.00001;
                        MAX_RADIUS = Math.min(length / 3.0, 0.5 * (1 / curvature));
                    } else if (radiusType == RADIUS_TYPE.MIDPT) {
                        MIN_RADIUS = length / 10.0;
                        MAX_RADIUS = Math.min(length / 3.0, 0.5 * (1 / curvature));
                    } else {
                        throw new RuntimeException("Invalid radius type");
                    }

                    ValueShifter1D converter = new ValueShifter1D(MIN_RADIUS, MAX_RADIUS);
                    double newRadius = converter.convert(normalizedMagnitude, oldRadiusInfo.getRadius());

                    RadiusInfo newRadiusInfo = new RadiusInfo(oldRadiusInfo, newRadius);
                    newRadiusProfile.addRadiusInfo(pointIndex, newRadiusInfo);
                }
            });
        } catch (Exception e) {

        }
        return newRadiusProfile;
    }
}