package org.xper.allen.ga3d.blockgen;

import org.xper.allen.Trial;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;

import java.util.Map;

public class MorphTrial extends ThreeDGATrial {

    private Long parentId;

    public MorphTrial(GA3DBlockGen generator, Long parentId) {
        super(generator);
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void write() {
        AllenMatchStick mStick = new AllenMatchStick();
        mStick.genMatchStickFromShapeSpec(AllenMStickSpec.fromXml(getMStickSpec(parentId)),new double[]{0,0,0});
    }

    private String getMStickSpec(Long parentId) {
        return generator.getDbUtil().readStimSpecDataByIdRangeAsMap(parentId, parentId).get(parentId);
    }

    @Override
    public Long getTaskId() {
        return null;
    }
}
