package org.xper.drawing.stick;

public class MAxisInfo {
	private int nComponent;        
	private int nEndPt;
	public int nJuncPt;
	private double[] finalRotation = new double[3];
	private double[] finalShiftInDepth = new double[3];
	private EndPt_Info[] EndPt;
	private JuncPt_Info[] JuncPt;
    private TubeInfo[] Tube;

	public void setMAxisInfo(MatchStick inStick) {
		setnComponent(inStick.getNComponent());
		setnEndPt(inStick.getNEndPt());
		nJuncPt = inStick.getNJuncPt();
		
		setJuncPt(new JuncPt_Info[nJuncPt+1]);
		setEndPt(new EndPt_Info[getnEndPt()+1]);
		setTube(new TubeInfo[getnComponent()+1]);
		
		for (int i=1; i<= getnEndPt(); i++) {
			getEndPt()[i] = new EndPt_Info();
			getEndPt()[i].setEndPtInfo(inStick.getEndPtStruct(i));
		}
		for (int i=1; i<= nJuncPt; i++) {
			getJuncPt()[i] = new JuncPt_Info();
			getJuncPt()[i].setJuncPtInfo( inStick.getJuncPtStruct(i));
		}
		for (int i=1; i<= getnComponent(); i++) {
			getTube()[i] = new TubeInfo();
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

	public TubeInfo[] getTube() {
		return Tube;
	}

	public void setTube(TubeInfo[] tube) {
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
}