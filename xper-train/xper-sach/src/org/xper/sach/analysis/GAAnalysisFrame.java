package org.xper.sach.analysis;


import javax.sql.DataSource;
import org.springframework.dao.EmptyResultDataAccessException;
import javax.swing.JFrame;
import javax.swing.JPanel;
import javax.swing.border.EmptyBorder;

import javax.swing.BorderFactory;
import javax.swing.ImageIcon;
import javax.swing.JLabel;

import org.dom4j.Document;
import org.dom4j.Node;
import org.xper.exception.DbException;
import org.xper.sach.util.ListUtil;
import org.xper.sach.util.SachDbUtil;
import org.xper.sach.util.SachMathUtil;
import org.xper.time.TimeUtil;
import org.xper.util.StringUtil;
import org.xper.util.ThreadUtil;
import org.xper.util.XmlUtil;

import com.mchange.v2.c3p0.ComboPooledDataSource;

import java.awt.Color;
import java.awt.Font;
import java.awt.GridBagLayout;
import java.awt.GridBagConstraints;								
import java.awt.Insets;
import java.beans.PropertyVetoException;
import java.util.Arrays;
import java.util.List;


public class GAAnalysisFrame extends JFrame {

	/**
	 * 
	 */
	private static final long serialVersionUID = 1L;
	private JPanel contentPane;

    private JLabel behPercCorrLabels[][] = new JLabel[8][8];		// 8 by 8 matrix to hold the behavioral performance (percent correct) values for each stimulus combination
    private JLabel behCountLabels[][] = new JLabel[8][8];	// number of times each stim combo has been runModeRun
    private JLabel behTotLabels[][] = new JLabel[8][3];		// count totals (match,non-match,n)
    
    private int behPass[][]  = new int[8][8];				// num pass for each stim pairing
    private int behCount[][] = new int[8][8];				// counts for each stim pairing
    
	boolean done = false;

	TimeUtil timeUtil;
	long analysisStartTime;			// when behavorial analysis frame is started 
	SachDbUtil dbUtil;
	
	enum TrialOutcomes {PASS, FAIL, BREAK, NOGO};
	
	
	public static void main(String[] args) 
	{
		GAAnalysisFrame f = new GAAnalysisFrame();
		f.setDbUtil(f.dbUtil());
		
		long currTaskId = 1372770097383623L;
		long nextTaskId = f.dbUtil.readTaskDoneNextId(currTaskId);
		
		System.out.println(currTaskId + " " + nextTaskId);
//		f.showBehavAnalysisFrame();
	
	}
	
	/**
	 * Display/runModeRun the frame.
	 */
	public void showBehavAnalysisFrame() {
				
		System.out.println("Show behavioral analysis");
		
		try {
			setVisible(true);
			//analysisStartTime = timeUtil.currentTimeMicros();
								
			// while loop for updating stats -- nowTaskDoneMaxID != lastTaskDoneMaxID
//			long lastTaskDoneMaxID = dbUtil.readTaskDoneMaxId(); 
//			long nowTaskDoneMaxID;
			
			long currTaskId = dbUtil.readTaskDoneMaxId();
			long nextTaskId;
						
			while(!done) {
//				nowTaskDoneMaxID = dbUtil.readTaskDoneMaxId(); 
//				
//				if (nowTaskDoneMaxID != lastTaskDoneMaxID) {
//					// also add conditional so that fixation trials don't trigger this?
//					updateStats(nowTaskDoneMaxID);							
//					lastTaskDoneMaxID = nowTaskDoneMaxID;
//				}
				//ThreadUtil.sleep(50);
				
				nextTaskId = dbUtil.readTaskDoneNextId(currTaskId);
				
				if (nextTaskId != 0) {
					// also add conditional so that fixation trials don't trigger this?
					updateStats(nextTaskId);							
					currTaskId = nextTaskId;
				}
			}
			
		} catch (Exception e) {
			e.printStackTrace();
		}	
		
	}

	/**
	 * Create the frame.
	 */
	public GAAnalysisFrame() {		
		setTitle("Behavioral Analysis Window");
		setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
    	setResizable(false);   	
    	
		setBounds(100, 100, 505, 505);
		contentPane = new JPanel();
		contentPane.setBorder(new EmptyBorder(5, 5, 5, 5));
		setContentPane(contentPane);
		contentPane.setLayout(null);
		
		
		// full statistics panel:
		JPanel fullStatPanel = new JPanel();
		int w = 466, h = 350;
		fullStatPanel.setBounds(15, 15, w+10, h+40);
		fullStatPanel.setBorder(BorderFactory.createTitledBorder("Trial Stats"));
		contentPane.add(fullStatPanel);
		GridBagLayout gbl_panel = new GridBagLayout();
		int c = 36, r = 16;
		gbl_panel.columnWidths = new int[]{c,c,c,c,c,c,c,c,c,8,c,c,c};
		gbl_panel.rowHeights = new int[]{r*2,r,r,r,r,r,r,r,r,r,r,r,r,r,r,r,r};
		gbl_panel.columnWeights = new double[]{0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, Double.MIN_VALUE, 0.0, 0.0, 0.0};
		gbl_panel.rowWeights = new double[]{Double.MIN_VALUE, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
		fullStatPanel.setLayout(gbl_panel);

		// add stim labels: (images of stimuli)
		String currDir = System.getProperty("user.dir")+"/images/";

		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim0.jpg")),new GridBagConstraints(0,1,1,2,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim1.jpg")),new GridBagConstraints(0,3,1,2,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim2.jpg")),new GridBagConstraints(0,5,1,2,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim3.jpg")),new GridBagConstraints(0,7,1,2,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim4.jpg")),new GridBagConstraints(0,9,1,2,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim5.jpg")),new GridBagConstraints(0,11,1,2,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim6.jpg")),new GridBagConstraints(0,13,1,2,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim7.jpg")),new GridBagConstraints(0,15,1,2,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,0,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim0.jpg")),new GridBagConstraints(1,0,1,1,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim1.jpg")),new GridBagConstraints(2,0,1,1,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim2.jpg")),new GridBagConstraints(3,0,1,1,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim3.jpg")),new GridBagConstraints(4,0,1,1,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim4.jpg")),new GridBagConstraints(5,0,1,1,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim5.jpg")),new GridBagConstraints(6,0,1,1,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim6.jpg")),new GridBagConstraints(7,0,1,1,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
		fullStatPanel.add(new JLabel(new ImageIcon(currDir+"stim7.jpg")),new GridBagConstraints(8,0,1,1,0.0,0.0,GridBagConstraints.CENTER,GridBagConstraints.NONE,new Insets(0,0,5,0),0,0));
				
		// initialize behavioral stat values to 0:		
		for (int n=0;n<8;n++) {
			for (int m=0;m<8;m++) {
				behPercCorrLabels[n][m] = new JLabel("0");
//				behavNumRunsLabels[n][m] = new JLabel("0");
				behCountLabels[n][m] = new JLabel(StringUtil.format(behCount[n][m],0));

				if (m==n) {
					behPercCorrLabels[n][m].setFont(new Font("LucidaGrande",Font.BOLD,  12));
					behCountLabels[n][m].setFont(new Font("LucidaGrande",Font.BOLD,  9));
				} else {
					behPercCorrLabels[n][m].setFont(new Font("LucidaGrande",Font.PLAIN, 12));
					behCountLabels[n][m].setFont(new Font("LucidaGrande",Font.PLAIN,  9));
				}

				fullStatPanel.add(behPercCorrLabels[n][m],new GridBagConstraints(m+1,(n+1)*2-1,1,1,0.0,0.0,GridBagConstraints.EAST,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
				fullStatPanel.add(behCountLabels[n][m],new GridBagConstraints(m+1,(n+1)*2,1,1,0.0,0.0,GridBagConstraints.EAST,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
			}
			
			// initialize "totals":
			behTotLabels[n][0] = new JLabel("0");			// 0- match, 1- non-match, 2- n (count)
			behTotLabels[n][1] = new JLabel("0");
			behTotLabels[n][2] = new JLabel("0");
			
			behTotLabels[n][0].setFont(new Font("LucidaGrande",Font.BOLD, 12));
			behTotLabels[n][1].setFont(new Font("LucidaGrande",Font.BOLD, 12));
			behTotLabels[n][2].setFont(new Font("LucidaGrande",Font.BOLD, 12));
			
			fullStatPanel.add(behTotLabels[n][0],new GridBagConstraints(10,(n+1)*2-1,1,1,0.0,0.0,GridBagConstraints.EAST,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
			fullStatPanel.add(behTotLabels[n][1],new GridBagConstraints(11,(n+1)*2-1,1,1,0.0,0.0,GridBagConstraints.EAST,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
			fullStatPanel.add(behTotLabels[n][2],new GridBagConstraints(12,(n+1)*2-1,1,1,0.0,0.0,GridBagConstraints.EAST,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));

			
			JLabel title1 = new JLabel("match");
			title1.setFont(new Font("LucidaGrande",Font.PLAIN,8));
			fullStatPanel.add(title1,new GridBagConstraints(10,0,1,1,0.0,0.0,GridBagConstraints.EAST,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));

			JLabel title2 = new JLabel("non");
			title2.setFont(new Font("LucidaGrande",Font.PLAIN,8));
			fullStatPanel.add(title2,new GridBagConstraints(11,0,1,1,0.0,0.0,GridBagConstraints.EAST,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));

			JLabel title3 = new JLabel("trials");
			title3.setFont(new Font("LucidaGrande",Font.PLAIN,8));
			fullStatPanel.add(title3,new GridBagConstraints(12,0,1,1,0.0,0.0,GridBagConstraints.EAST,GridBagConstraints.NONE,new Insets(0,0,5,5),0,0));
			
		}

	}
	
	
	void updateStats(long taskId) {
		// this runs when a new trial is finished (while loop above looks for when nowTaskDoneMaxID != lastTaskDoneMaxID)
		// -- it checks which stimuli were runModeRun, what the outcome was, and updates the appropriate numbers and labels
				
		// get stimulus info: (categories of 1st and 2nd stimuli)
		String spec = dbUtil.getSpecByTaskId(taskId).getSpec();
		Document specDoc = XmlUtil.parseSpec(spec);
		//System.out.println(taskId);
		
		int[] stimCats = new int[2];	
		List<Node> nList = ListUtil.castList(Node.class, specDoc.node(0).selectNodes("object"));
		for (int n = 0; n < nList.size(); n++) {	// for behavioral trials n = 2
			Node node = nList.get(n);
			stimCats[n] = Integer.parseInt(node.selectSingleNode("category").getText());			
		}
		int p = stimCats[0], q = stimCats[1];
		
		long msgTaskId = -1;
		TrialOutcomes outcome = null;

//		int i = 0;
//		while (taskId > msgTaskId & i < 10) {
//			// get behavioral outcome:
//			String msg = dbUtil.getLastTrialOutcomeMsg();
//			//System.out.println(msg);
//			
//			// parse msg to check if taskId is same and to get outcome:
//			Document msgDoc = XmlUtil.parseSpec(msg);
//			
//			String trialOutcome = msgDoc.node(0).selectSingleNode("outcome").getText();
//			outcome = TrialOutcomes.valueOf(trialOutcome);
//			
//			msgTaskId = Long.parseLong(msgDoc.node(0).selectSingleNode("taskID").getText());
//			i++;
//			ThreadUtil.sleep(50);	
//		}
		
		// get behavioral outcome:
		String msg = "";
		int i = 0;
		while(msg.isEmpty() & i < 10) {
			try {
//				msg = dbUtil.getTaskIdOutcomeByTaskId(taskId); // can't really do this hack, turned off TaskIdOutcome recording in SachExperimentMessageDispatcher
				msg = dbUtil.readTrialOutcomeByTaskId(taskId);
			} catch (EmptyResultDataAccessException e) {
				i++;
				System.out.println(i);
				ThreadUtil.sleep(50);
			}
			
		}
		//System.out.println(msg);

		// parse msg to check if taskId is same and to get outcome:
		Document msgDoc = XmlUtil.parseSpec(msg);
		String trialOutcome = msgDoc.node(0).selectSingleNode("outcome").getText();
		outcome = TrialOutcomes.valueOf(trialOutcome);
		msgTaskId = Long.parseLong(msgDoc.node(0).selectSingleNode("taskID").getText());

		// debug:
		System.out.println("--taskId = " + taskId + "  msgTaskId = " + msgTaskId);
		System.out.println("stim = " + Arrays.toString(stimCats) + "  outcome = " + outcome.toString());
		
		if (taskId != msgTaskId) {	// if its still not the same, announce error
			System.err.println("taskId mismatch in BehavAnalysisFrame!");
			return;
		}
		
		// update counts and labels: (depending on which outcome)
		switch(outcome) {
		case PASS:
			behCount[p][q]++;	// first update the stim counter
			behPass[p][q]++;	// update pass counter
			updateLabelCount(behCountLabels[p][q],behCount[p][q]);
			updateLabelCount(behPercCorrLabels[p][q],(double)behPass[p][q]/(double)behCount[p][q]*100);
			
			updateLabelCount(behTotLabels[p][0],(double)behPass[p][p]/(double)behCount[p][p]*100); // update total match performance
			updateLabelCount(behTotLabels[p][1],(SachMathUtil.vectSum(behPass[p])-behPass[p][p])/(SachMathUtil.vectSum(behCount[p])-behCount[p][p])*100); // update total non-matches
			updateLabelCount(behTotLabels[p][2],SachMathUtil.vectSum(behCount[p])); // update total number of trials
			break;
			
		case FAIL:
			behCount[p][q]++;	// first update the stim counter
			updateLabelCount(behCountLabels[p][q],behCount[p][q]);
			updateLabelCount(behPercCorrLabels[p][q],(double)behPass[p][q]/(double)behCount[p][q]*100);

			updateLabelCount(behTotLabels[p][0],(double)behPass[p][p]/(double)behCount[p][p]*100); // update total match performance
			updateLabelCount(behTotLabels[p][1],(SachMathUtil.vectSum(behPass[p])-behPass[p][p])/(SachMathUtil.vectSum(behCount[p])-behCount[p][p])*100); // update total non-matches
			updateLabelCount(behTotLabels[p][2],SachMathUtil.vectSum(behCount[p])); // update total number of trials
			break;
			
		case BREAK:
			// do not update counter (not used for percent correct evaluation!)
			break;
		
		case NOGO:
			
			break;
		}		
	}
	
	void updateLabelCount(JLabel label, double count) {
		String lastCount = label.getText();
		String thisCount = StringUtil.format(count, 0);
		label.setText(thisCount);
		if (thisCount.equals(lastCount)) {
			label.setForeground(Color.BLACK);
		} else {
			label.setForeground(Color.RED);
		}
	}
	
	
	// setters:
	
	public void setDbUtil(SachDbUtil dbUtil_in) {
		this.dbUtil = dbUtil_in;
	}
	
	public void setGlobalTimeUtil(TimeUtil globalTimeUtil) {
		this.timeUtil = globalTimeUtil;
	}
	
	// the following is to set the dbutil during testing, otherwise it is set via the config file(s)
	public SachDbUtil dbUtil() {
		SachDbUtil util = new SachDbUtil();
		util.setDataSource(dataSource());
		return util;
	}

	public DataSource dataSource() {
		ComboPooledDataSource source = new ComboPooledDataSource();
		try {
			source.setDriverClass("com.mysql.jdbc.Driver");
		} catch (PropertyVetoException e) {
			throw new DbException(e);
		}
//		source.setJdbcUrl("jdbc:mysql://192.168.1.1/sach_2013_06_05_training?useUnicode=true&characterEncoding=UTF8");
		source.setJdbcUrl("jdbc:mysql://localhost/xper_sach_testing");
		source.setUser("xper_rw");
		source.setPassword("up2nite");
		return source;
	}

	
	
}
