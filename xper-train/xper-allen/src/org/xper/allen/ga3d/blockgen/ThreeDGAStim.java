package org.xper.allen.ga3d.blockgen;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.ga.GABranch;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.PngSpec;

public abstract class ThreeDGAStim implements Stim {
    protected final GA3DBlockGenerator generator;
    protected double size;
    protected Coordinates2D coords;
    protected long stimId;
    protected PngSpec stimSpec;
    protected AllenMStickData mStickData;
    protected Long parentId;
    private GABranch tree;

    /**
     * Constructor for creating a parent stimulus
     */
    public ThreeDGAStim(GA3DBlockGenerator generator, double size, Coordinates2D coords) {
        this.generator = generator;
        this.size = size;
        this.coords = coords;
        this.parentId = 0L;
    }

    /**
     * Constructor for creating a child stimulus
     */
    public ThreeDGAStim(GA3DBlockGenerator generator, Long parentId) {
        this.generator = generator;
        this.parentId = parentId;
    }

    protected void writeStimSpec(long id) {
        generator.getDbUtil().writeStimSpec(id, stimSpec.toXml(), mStickData.toXml());
    }


    public void writeStimGaInfo(String gaName, long genId){
        //Is Founder Stimulus
        if (parentId == 0L) {
            tree = new GABranch(stimId);
        }
        else {
            String treeSpec = generator.getDbUtil().readStimGaInfo(parentId).getTreeSpec();
            tree = GABranch.fromXml(treeSpec);
            tree.addChildTo(parentId, stimId);
        }

        generator.getDbUtil().writeStimGaInfo(stimId, parentId, gaName, genId, tree.toXml());
    }
}
