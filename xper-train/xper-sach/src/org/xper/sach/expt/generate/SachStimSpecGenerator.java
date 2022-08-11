package org.xper.sach.expt.generate;

import java.util.List;

//import org.xper.drawing.renderer.AbstractRenderer;

// ***NOT USED, currently***

public interface SachStimSpecGenerator {
//	public String generateStimSpec(AbstractRenderer renderer);
//	public String generateBehTrialSpec(long stimObjId_A, long stimObjId_B, int targetIndex);
	public String generateGATrialSpec(List<Long> stimObjIds);
//	public long generateBlankStim(long gen, int lineage);
//	public long generateRandGAStim(long gen, int lineage);
//	public long generateMorphStim(long gen, int lineage, long parentId);
}
