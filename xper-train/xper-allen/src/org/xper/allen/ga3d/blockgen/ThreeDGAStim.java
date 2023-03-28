package org.xper.allen.ga3d.blockgen;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.ga.Branch;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.PngSpec;

public abstract class ThreeDGAStim implements Stim {
    protected final GABlockGenerator generator;
    protected double size;
    protected Coordinates2D coords;
    protected long stimId;
    protected PngSpec stimSpec;
    protected AllenMStickData mStickData;
    protected Long parentId;
    private Branch<Long> tree;
    private Long lineageId;

    /**
     * Constructor for creating a parent stimulus
     */
    public ThreeDGAStim(GABlockGenerator generator, double size, Coordinates2D coords) {
        this.generator = generator;
        this.size = size;
        this.coords = coords;
        this.parentId = 0L;
        this.tree = null;
    }

    /**
     * Constructor for creating a child stimulus
     */
    public ThreeDGAStim(GABlockGenerator generator, Long parentId) {
        this.generator = generator;
        this.parentId = parentId;
        this.tree = null;
    }

    protected void writeStimSpec(long id) {
        generator.getDbUtil().writeStimSpec(id, stimSpec.toXml(), mStickData.toXml());
    }

    /**
     * Updates StimGaInfo and LineageGaInfo tables
     * @param gaName
     * @param genId
     */
    public void writeGaInfo(String gaName, long genId){
        updateStimTree();
        lineageId = tree.getIdentifier();
        generator.getDbUtil().writeStimGaInfo(stimId, parentId, gaName, genId, lineageId, tree.toXml(), "DEFAULT");
        updateLineageTree();
    }


    private boolean isFounderStim() {
        return parentId == 0L;
    }

    /**
     * Tracks the genetic history of a single stimulus, starting from the founder of the lineage that stimulus is in.
     * (Only the parent of the stimulus, and the parents of parents)
     */
    private void updateStimTree() {
        if (isFounderStim()) {
            tree = new Branch<>(stimId);
        }
        else {
            String treeSpec = generator.getDbUtil().readStimGaInfo(parentId).getTreeSpec();
            tree = Branch.fromXml(treeSpec);
            tree.addChildTo(parentId, stimId);
        }
    }

    /**
     * Tracks the pedigree of an entire lineage, starting from the founder of the lineage.
     * (Including siblings, uncles, cousins, etc.)
     */
    private void updateLineageTree() {
        Branch<Long> lineageTree;
        if (isFounderStim()){
            lineageTree = new Branch<>(stimId);
            generator.getDbUtil().writeLineageGaInfo(new MultiGaDbUtil.LineageGaInfo(
                    lineageId,
                    lineageTree.toXml(),
                    0.0,
                    new LineageData().toXml()));
        } else{
            lineageTree = Branch.fromXml(generator.getDbUtil().readLineageTreeSpec(lineageId));
            lineageTree.addChildTo(parentId, stimId);
            generator.getDbUtil().updateLineageTreeSpec(lineageId, lineageTree.toXml());
        }


    }

}