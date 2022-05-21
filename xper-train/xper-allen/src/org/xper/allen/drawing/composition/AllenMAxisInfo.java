package org.xper.allen.drawing.composition;

import org.xper.drawing.stick.EndPt_Info;
import org.xper.drawing.stick.JuncPt_Info;
import org.xper.drawing.stick.MatchStick;
import org.xper.drawing.stick.TubeInfo;

public class AllenMAxisInfo {
	private int nComponent;        
	private int nEndPt;
	private int nJuncPt;
	private double[] finalRotation = new double[3];
	private double[] finalShiftInDepth = new double[3];
	private EndPt_Info[] EndPt;
	private JuncPt_Info[] JuncPt;
    private AllenTubeInfo[] Tube;
    
    private int specialEndComp;
    private int specialEnd;
    private int baseComp;


	public void setAllenMAxisInfo(AllenMatchStick inStick) {
		//Added by AC
		setSpecialEndComp(inStick.getSpecialEndComp());
		setSpecialEnd(inStick.getSpecialEnd());
		setBaseComp(inStick.getBaseComp());
		/////////////
		setnComponent(inStick.getNComponent());
		setnEndPt(inStick.getNEndPt());
		setnJuncPt(inStick.getNJuncPt());
		
		setJuncPt(new JuncPt_Info[getnJuncPt()+1]);
		setEndPt(new EndPt_Info[getnEndPt()+1]);
		setTube(new AllenTubeInfo[getnComponent()+1]);
		
		for (int i=1; i<= getnEndPt(); i++) {
			getEndPt()[i] = new EndPt_Info();
			getEndPt()[i].setEndPtInfo(inStick.getEndPtStruct(i));
		}
		for (int i=1; i<= getnJuncPt(); i++) {
			getJuncPt()[i] = new JuncPt_Info();
			getJuncPt()[i].setJuncPtInfo( inStick.getJuncPtStruct(i));
		}
		for (int i=1; i<= getnComponent(); i++) {
			getTube()[i] = new AllenTubeInfo();
			getTube()[i].setTubeInfo(inStick.getTubeComp(i));
		}
		
		for (int i=0; i<3; i++)
			getFinalRotation()[i] = inStick.getFinalRotation(i);
		
		for (int i=0; i<3; i++)
			getFinalShiftInDepth()[i] = inStick.getFinalShiftInDepth(i);
	}

	public JuncPt_Info[] getJuncPt() {
		return JuncPt;
	}

	public void setJuncPt(JuncPt_Info[] juncPt) {
		JuncPt = juncPt;
	}

	public EndPt_Info[] getEndPt() {
		return EndPt;
	}

	public void setEndPt(EndPt_Info[] endPt) {
		EndPt = endPt;
	}

	public int getnEndPt() {
		return nEndPt;
	}

	public void setnEndPt(int nEndPt) {
		this.nEndPt = nEndPt;
	}

	public int getnComponent() {
		return nComponent;
	}

	public void setnComponent(int nComponent) {
		this.nComponent = nComponent;
	}

	public AllenTubeInfo[] getTube() {
		return Tube;
	}

	public void setTube(AllenTubeInfo[] tube) {
		Tube = tube;
	}

	public double[] getFinalShiftInDepth() {
		return finalShiftInDepth;
	}

	public void setFinalShiftInDepth(double[] finalShiftInDepth) {
		this.finalShiftInDepth = finalShiftInDepth;
	}

	public double[] getFinalRotation() {
		return finalRotation;
	}

	public void setFinalRotation(double[] finalRotation) {
		this.finalRotation = finalRotation;
	}

	public int getSpecialEndComp() {
		return specialEndComp;
	}

	public void setSpecialEndComp(int specialEndComp) {
		this.specialEndComp = specialEndComp;
	}

	public int getSpecialEnd() {
		return specialEnd;
	}

	public void setSpecialEnd(int specialEnd) {
		this.specialEnd = specialEnd;
	}

	public int getnJuncPt() {
		return nJuncPt;
	}

	public void setnJuncPt(int nJuncPt) {
		this.nJuncPt = nJuncPt;
	}

	public int getBaseComp() {
		return baseComp;
	}

	public void setBaseComp(int baseComp) {
		this.baseComp = baseComp;
	}
}