package org.xper.allen.ga3d.blockgen;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.ga.Branch;
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
    private Branch<Long> tree;
    private Long lineageId;

    /**
     * Constructor for creating a parent stimulus
     */
    public ThreeDGAStim(GA3DBlockGenerator generator, double size, Coordinates2D coords) {
        this.generator = generator;
        this.size = size;
        this.coords = coords;
        this.parentId = 0L;
        this.tree = null;
    }

    /**
     * Constructor for creating a child stimulus
     */
    public ThreeDGAStim(GA3DBlockGenerator generator, Long parentId) {
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
        generator.getDbUtil().writeStimGaInfo(stimId, parentId, gaName, genId, lineageId, tree.toXml());
        updateLineageTree();
    }


    private boolean isFounderStim() {
        return parentId == 0L;
    }


    private void updateLineageTree() {
        Branch lineageTree;
        if (isFounderStim()){
            lineageTree = new Branch<>(stimId);
        } else{
            lineageTree = Branch.fromXml(generator.getDbUtil().readLineageTreeSpec(lineageId));
            lineageTree.addChildTo(parentId, stimId);
        }

        generator.getDbUtil().updateLineageTreeSpec(lineageId, lineageTree.toXml());
    }

    /**
     * MAy be deprecated/
     * Only update the tree if it hasn't been updated yet.
     *
     * A stim tree is a stimulus' tree of ancestors.
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
}