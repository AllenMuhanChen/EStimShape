package org.xper.allen.nafc.console;

import java.awt.Canvas;
import java.awt.Color;
import java.awt.Cursor;
import java.awt.Dimension;
import java.awt.EventQueue;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyEvent;
import java.awt.event.MouseEvent;
import java.awt.event.MouseListener;
import java.awt.event.MouseMotionAdapter;
import java.awt.event.MouseWheelEvent;
import java.awt.event.MouseWheelListener;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import javax.swing.AbstractAction;
import javax.swing.Action;
import javax.swing.ActionMap;
import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.InputMap;
import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JComponent;
import javax.swing.JDialog;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.KeyStroke;
import javax.swing.SwingConstants;
import javax.swing.SwingUtilities;

import org.apache.log4j.Logger;
import org.lwjgl.LWJGLException;
import org.xper.Dependency;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.console.IConsolePlugin;
import org.xper.console.MessageReceiverEventListener;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.util.GuiUtil;
import org.xper.util.StringUtil;
import org.xper.util.ThreadUtil;

public class NAFCExperimentConsole extends JFrame implements
		MessageReceiverEventListener {
	static Logger logger = Logger.getLogger(NAFCExperimentConsole.class);

	private static final long serialVersionUID = -5313216043026458229L;

	@Dependency
	NAFCExperimentConsoleModel model;

	@Dependency
	NAFCExperimentConsoleRenderer consoleRenderer;

	@Dependency
	Coordinates2D monkeyScreenDimension;

	@Dependency
	double canvasScaleFactor = DEFAULT_CANVAS_SCALE_FACTOR;

	@Dependency
	List<IConsolePlugin> consolePlugins = new ArrayList<IConsolePlugin>();

	KeyStroke monitorToken = KeyStroke.getKeyStroke(KeyEvent.VK_F1, 0);

	KeyStroke lockUnlockKey = KeyStroke.getKeyStroke(KeyEvent.VK_L, 0);
	KeyStroke pauseResumeKey = KeyStroke.getKeyStroke(KeyEvent.VK_P, 0);
	KeyStroke rewardKey = KeyStroke.getKeyStroke(KeyEvent.VK_R, 0);
	IConsolePlugin currentPlugin = null;

	boolean paused = true;
	boolean lockSimulatedEyePos = false;

	AtomicReference<String> currentDeviceId = new AtomicReference<String>();

	static final double DEFAULT_CANVAS_SCALE_FACTOR = 2.5;

	public boolean isMonitorMode () {
		return currentPlugin == null;
	}

    public void initComponents() {
    	setTitle("Experiment Console");
    	setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE);
    	setResizable(true);
		GuiUtil.makeDisposeOnEscapeKey(this);
		addWindowListener(new WindowAdapter() {
            public void windowClosing(WindowEvent evt) {
            	stop();
            }
        });
		getContentPane().setLayout(new BoxLayout(getContentPane(), BoxLayout.PAGE_AXIS));
		InputMap keyMap = getRootPane().getInputMap(JComponent.WHEN_IN_FOCUSED_WINDOW);
		ActionMap actMap = getRootPane().getActionMap();
		Action eyeAction = new AbstractAction() {
			private static final long serialVersionUID = 1L;

			public void actionPerformed(ActionEvent e) {
				if (isMonitorMode()) {
					lockSimulatedEyePos = !lockSimulatedEyePos;
				}
			}
		};
		keyMap.put(lockUnlockKey, eyeAction);
		actMap.put(eyeAction, eyeAction);

		Action monitorAction = new AbstractAction() {
			private static final long serialVersionUID = 1L;

			public void actionPerformed(ActionEvent e) {
				currentPlugin = null;
			}
		};
		keyMap.put(monitorToken, monitorAction);
		actMap.put(monitorAction, monitorAction);

		for (final IConsolePlugin p : consolePlugins) {
			KeyStroke token = p.getToken();
			Action tokenAction = new AbstractAction() {
				private static final long serialVersionUID = 1L;

				public void actionPerformed(ActionEvent e) {
					currentPlugin = p;
				}
			};
			keyMap.put(token, tokenAction);
			actMap.put(tokenAction, tokenAction);
		}

		for (IConsolePlugin p : consolePlugins) {
			List<KeyStroke> keys = p.getCommandKeys();
			for (final KeyStroke k : keys) {
				Action keyAction = new AbstractAction() {
					private static final long serialVersionUID = 1L;

					public void actionPerformed(ActionEvent e) {
						if (!isMonitorMode()) {
							currentPlugin.handleKeyStroke(k);
						}
					}
				};
				keyMap.put(k, keyAction);
				actMap.put(keyAction, keyAction);
			}
		}

        JPanel canvasPanel = new JPanel();
        consoleCanvas = getCanvas();
        consoleCanvas.setPreferredSize(new Dimension((int)(monkeyScreenDimension.getX() / (canvasScaleFactor)),
        		(int)(monkeyScreenDimension.getY() / canvasScaleFactor)));
//        consoleCanvas.setPreferredSize(new Dimension(480,360));

        consoleCanvas.addMouseMotionListener(new MouseMotionAdapter() {
            public void mouseMoved(MouseEvent evt) {
            	if (isMonitorMode()) {
            		mousePosition(evt.getX(), evt.getY());
            	} else {
            		currentPlugin.handleMouseMove(evt.getX(), evt.getY());
            	}
            }
        });
        canvasPanel.add(consoleCanvas);

        consoleCanvas.addMouseWheelListener(new MouseWheelListener() {
			@Override
			public void mouseWheelMoved(MouseWheelEvent e) {
				if (!isMonitorMode()) {
					currentPlugin.handleMouseWheel(e);
				}
			}
		});

        consoleCanvas.addMouseListener(new MouseListener() {

			@Override
			public void mouseReleased(MouseEvent e) {
			}

			@Override
			public void mousePressed(MouseEvent e) {
			}

			@Override
			public void mouseExited(MouseEvent e) {
			}

			@Override
			public void mouseEntered(MouseEvent e) {
			}

			@Override
			public void mouseClicked(MouseEvent e) {
				if (!isMonitorMode()) {
					currentPlugin.handleMouseClicked(e);
				}
			}
		});
        getContentPane().add(canvasPanel);

        JPanel infoPanel = new JPanel();
        infoPanel.setLayout(new BoxLayout(infoPanel, BoxLayout.LINE_AXIS));

        getContentPane().add(infoPanel);

        JPanel trialPanel = new JPanel();
        trialPanel.setLayout(new BoxLayout(trialPanel, BoxLayout.PAGE_AXIS));
        infoPanel.add(trialPanel);

        JPanel eyePanel = new JPanel();
        eyePanel.setLayout(new BoxLayout(eyePanel, BoxLayout.PAGE_AXIS));
        infoPanel.add(eyePanel);

        JPanel commandPanel = new JPanel();
        commandPanel.setLayout(new BoxLayout(commandPanel, BoxLayout.PAGE_AXIS));
        infoPanel.add(commandPanel);

        JPanel mousePositionPanel = new JPanel();
        mousePositionPanel.setBorder(BorderFactory.createTitledBorder("Mouse Position"));
        mousePositionPanel.setLayout(new GridBagLayout());
        trialPanel.add(mousePositionPanel);

        JPanel trialStatPanel = new JPanel();
        trialStatPanel.setBorder(BorderFactory.createTitledBorder("Trial Statistics"));
        trialStatPanel.setLayout(new GridBagLayout());
        trialPanel.add(trialStatPanel);

        JPanel eyeDevicePanel = new JPanel();
        eyeDevicePanel.setBorder(BorderFactory.createTitledBorder("Eye Device"));
        eyeDevicePanel.setLayout(new GridBagLayout());
        eyePanel.add(eyeDevicePanel);

        JPanel eyeWinPanel = new JPanel();
        eyeWinPanel.setBorder(BorderFactory.createTitledBorder("Eye Window"));
        eyeWinPanel.setLayout(new GridBagLayout());
        eyePanel.add(eyeWinPanel);

        pauseResumeButton = new JButton();
        pauseResumeButton.setToolTipText("run/pause experiment");
        Action action = new AbstractAction() {
			private static final long serialVersionUID = 1L;

			public void actionPerformed(ActionEvent e) {
				pauseResume();
			}
		};
		Dimension size = new Dimension(100, 25);
        pauseResumeButton.getInputMap(JComponent.WHEN_IN_FOCUSED_WINDOW).put(pauseResumeKey, action);
        pauseResumeButton.getActionMap().put(action, action);
        pauseResumeButton.setMinimumSize(size);
        pauseResumeButton.setMaximumSize(size);
        pauseResumeButton.setPreferredSize(size);
        pauseResumeButton.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent evt) {
            	pauseResume();
            }
        });

		if (paused) {
			pauseResumeButton.setText("   Run   ");
		} else {
			pauseResumeButton.setText("  Pause  ");
		}

        commandPanel.add(Box.createRigidArea(new Dimension(0,6)));
        commandPanel.add(pauseResumeButton);
        commandPanel.add(Box.createRigidArea(new Dimension(0,3)));
        //////////////////// JUICE BUTTON AC /////////////////
        rewardButton = new JButton();
        rewardButton.setToolTipText("Manual Reward");
        Action rewardAction = new AbstractAction() {
			private static final long serialVersionUID = 2L;

			public void actionPerformed(ActionEvent e) {
				reward();
			}
		};
		Dimension rewardButtonSize = new Dimension(100, 25);
        rewardButton.getInputMap(JComponent.WHEN_IN_FOCUSED_WINDOW).put(rewardKey, rewardAction);
        rewardButton.getActionMap().put(rewardAction, rewardAction);
        rewardButton.setMinimumSize(rewardButtonSize);
        rewardButton.setMaximumSize(rewardButtonSize);
        rewardButton.setPreferredSize(rewardButtonSize);
        rewardButton.addActionListener(new ActionListener() {
            public void actionPerformed(ActionEvent evt) {
            	reward();
            }
        });

        rewardButton.setText("   REWARD   ");

        commandPanel.add(Box.createRigidArea(new Dimension(6,6)));
        commandPanel.add(rewardButton);
        commandPanel.add(Box.createRigidArea(new Dimension(6,3)));

        /////////////////////
        JLabel monitorLabel = new JLabel("<html><strong> " + GuiUtil.getKeyText(monitorToken.getKeyCode()) + "</strong>: monitor mode </html>");
		monitorLabel.setToolTipText("<html><strong>monitor mode commands</strong> <br><strong> " + GuiUtil.getKeyText(lockUnlockKey.getKeyCode()) + "</strong>: lock/unlock </html>");
        commandPanel.add(monitorLabel);

        for (IConsolePlugin p : consolePlugins) {
        	JLabel pLabel = new JLabel("<html><strong> " + GuiUtil.getKeyText(p.getToken().getKeyCode()) + "</strong>: " + p.getPluginName() + " <html>");
        	pLabel.setToolTipText(p.getPluginHelp());
        	commandPanel.add(pLabel);
		}

        JLabel rpLabel = new JLabel("<html><strong> " + GuiUtil.getKeyText(pauseResumeKey.getKeyCode()) + "</strong>: run/pause </html>");
        commandPanel.add(rpLabel);

        JLabel exitLabel = new JLabel("<html><strong> ESC</strong>: exit </html>");
        commandPanel.add(exitLabel);

        commandPanel.add(Box.createGlue());
        modeLabel = new JLabel("");
        commandPanel.add(modeLabel);
        commandPanel.add(Box.createRigidArea(new Dimension(0,3)));

        mousePositionPanel.add(new JLabel("Screen"),
        		new GridBagConstraints(0,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        mouseXCanvas = new JLabel("0");
        mouseYCanvas = new JLabel("0");
        mousePositionPanel.add(mouseXCanvas,
        		new GridBagConstraints(1,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        mousePositionPanel.add(mouseYCanvas,
        		new GridBagConstraints(2,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        mousePositionPanel.add(new JLabel("World"),
        		new GridBagConstraints(0,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        mouseXWorld = new JLabel("0");
        mouseYWorld = new JLabel("0");
        mousePositionPanel.add(mouseXWorld,
        		new GridBagConstraints(1,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        mousePositionPanel.add(mouseYWorld,
        		new GridBagConstraints(2,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        mousePositionPanel.add(new JLabel("Degree"),
        		new GridBagConstraints(0,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        mouseXDegree = new JLabel("0");
        mouseYDegree = new JLabel("0");
        mousePositionPanel.add(mouseXDegree,
        		new GridBagConstraints(1,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        mousePositionPanel.add(mouseYDegree,
        		new GridBagConstraints(2,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));

        mouseXCanvas.setPreferredSize(new Dimension(80,20));
        mouseXCanvas.setHorizontalAlignment(SwingConstants.RIGHT);
        mouseXCanvas.setToolTipText("Window Coordinate X");
        mouseYCanvas.setPreferredSize(new Dimension(80,20));
        mouseYCanvas.setHorizontalAlignment(SwingConstants.RIGHT);
        mouseYCanvas.setToolTipText("Window Coordinate Y");
        mouseXWorld.setToolTipText("World Coordinate X");
        mouseYWorld.setToolTipText("World Coordinate Y");
        mouseXDegree.setToolTipText("Degree X");
        mouseYDegree.setToolTipText("Degree Y");
// Fix
        trialStatPanel.add(new JLabel("Fixation Success"),
        		new GridBagConstraints(0,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,0));
        fixationSuccess = new JLabel("0");
        trialStatPanel.add(fixationSuccess,
        		new GridBagConstraints(1,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,0));

        trialStatPanel.add(new JLabel("Fixation Eye In Fail"),
        		new GridBagConstraints(0,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,0));
        fixationEyeInFail = new JLabel("0");
        trialStatPanel.add(fixationEyeInFail,
        		new GridBagConstraints(1,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,0));

        trialStatPanel.add(new JLabel("Fixation Eye Hold Fail"),
        		new GridBagConstraints(0,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,0));
        fixationEyeInHoldFail = new JLabel("0");
        trialStatPanel.add(fixationEyeInHoldFail,
        		new GridBagConstraints(1,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,0));
// Sample
        trialStatPanel.add(new JLabel("Sample Success"),
        		new GridBagConstraints(2,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,0));
        sampleSuccess = new JLabel("0");
        trialStatPanel.add(sampleSuccess,
        		new GridBagConstraints(3,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,0));

        trialStatPanel.add(new JLabel("Sample Eye Hold Fail"),
        		new GridBagConstraints(2,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,0));
        sampleEyeInHoldFail = new JLabel("0");
        trialStatPanel.add(sampleEyeInHoldFail,
        		new GridBagConstraints(3,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,0));
// Choice
        trialStatPanel.add(new JLabel("Choice Correct"),
        		new GridBagConstraints(4,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,0));
        choiceCorrect = new JLabel("0");
        trialStatPanel.add(choiceCorrect,
        		new GridBagConstraints(5,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,0));

        trialStatPanel.add(new JLabel("Choice Incorrect"),
        		new GridBagConstraints(4,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,0));
        choiceIncorrect = new JLabel("0");
        trialStatPanel.add(choiceIncorrect,
        		new GridBagConstraints(5,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,0));

        trialStatPanel.add(new JLabel("Rewarded Incorrect"),
        		new GridBagConstraints(4,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,0));
        choiceRewardedIncorrect = new JLabel("0");
        trialStatPanel.add(choiceRewardedIncorrect,
        		new GridBagConstraints(5,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,0));

        trialStatPanel.add(new JLabel("Choice Eye Fail"),
        		new GridBagConstraints(4,3,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,0));
        choiceEyeFail = new JLabel("0");
        trialStatPanel.add(choiceEyeFail,
        		new GridBagConstraints(5,3,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,0));

        trialStatPanel.add(new JLabel("Completed Trials"),
        		new GridBagConstraints(4,4,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),40,10));
        completeTrialCount = new JLabel("0");
        trialStatPanel.add(completeTrialCount,
        		new GridBagConstraints(5,4,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),60,10));

        eyeDeviceSelect = new JComboBox();
        eyeDevicePanel.add(eyeDeviceSelect,
        		new GridBagConstraints(0,0,3,1,0.0,0.0,GridBagConstraints.LINE_START,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeDevicePanel.add(new JLabel("Degree"),
        		new GridBagConstraints(0,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeReadingDegreeX = new JLabel("0");
        eyeDevicePanel.add(eyeReadingDegreeX,
        		new GridBagConstraints(1,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeReadingDegreeY = new JLabel("0");
        eyeDevicePanel.add(eyeReadingDegreeY,
        		new GridBagConstraints(2,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeDevicePanel.add(new JLabel("Volt"),
        		new GridBagConstraints(0,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeReadingVoltX = new JLabel("0");
        eyeDevicePanel.add(eyeReadingVoltX,
        		new GridBagConstraints(1,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeReadingVoltY = new JLabel("0");
        eyeDevicePanel.add(eyeReadingVoltY,
        		new GridBagConstraints(2,2,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeDevicePanel.add(new JLabel("Zero"),
        		new GridBagConstraints(0,3,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeZeroX = new JLabel("0");
        eyeDevicePanel.add(eyeZeroX,
        		new GridBagConstraints(1,3,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeZeroY = new JLabel("0");
        eyeDevicePanel.add(eyeZeroY,
        		new GridBagConstraints(2,3,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));

        eyeDeviceSelect.setPreferredSize(new Dimension(180,25));
        eyeReadingDegreeX.setHorizontalAlignment(SwingConstants.RIGHT);
        eyeReadingDegreeX.setPreferredSize(new Dimension(80,20));
        eyeReadingDegreeY.setHorizontalAlignment(SwingConstants.RIGHT);
        eyeReadingDegreeY.setPreferredSize(new Dimension(80,20));

        eyeReadingDegreeX.setToolTipText("Degree X");
        eyeReadingDegreeY.setToolTipText("Degre Y");
        eyeReadingVoltX.setToolTipText("Volt X");
        eyeReadingVoltY.setToolTipText("Volt Y");
        eyeZeroX.setToolTipText("Zero X");
        eyeZeroY.setToolTipText("Zero Y");

        eyeWinPanel.add(new JLabel("Center"),
        		new GridBagConstraints(0,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeWindowCenterX = new JLabel("0");
        eyeWinPanel.add(eyeWindowCenterX,
        		new GridBagConstraints(1,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeWindowCenterY = new JLabel("0");
        eyeWinPanel.add(eyeWindowCenterY,
        		new GridBagConstraints(2,0,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeWinPanel.add(new JLabel("Size"),
        		new GridBagConstraints(0,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));
        eyeWindowSize = new JLabel("0");
        eyeWinPanel.add(eyeWindowSize,
        		new GridBagConstraints(1,1,1,1,0.0,0.0,GridBagConstraints.LINE_END,GridBagConstraints.NONE,new Insets(0,0,0,0),0,0));

        eyeWindowCenterX.setHorizontalAlignment(SwingConstants.RIGHT);
        eyeWindowCenterX.setPreferredSize(new Dimension(80,20));
        eyeWindowCenterY.setHorizontalAlignment(SwingConstants.RIGHT);
        eyeWindowCenterY.setPreferredSize(new Dimension(80,20));

        eyeWindowCenterX.setToolTipText("Degree X");
        eyeWindowCenterY.setToolTipText("Degree Y");
        eyeWindowSize.setToolTipText("Degree");

        eyeDeviceSelect.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
            	changeCurrentDeviceId((String) eyeDeviceSelect.getSelectedItem());
            }
        });

		for (String id : model.getEyeDeviceIds()) {
			eyeDeviceSelect.addItem(id);
		}
		eyeDeviceSelect.setSelectedIndex(1);
		changeCurrentDeviceId((String) eyeDeviceSelect.getSelectedItem());

		pack();
    }

	void pauseResume() {
		paused = !paused;
		if (paused) {
			pauseResumeButton.setText("   Run   ");
			setCursor(Cursor.getPredefinedCursor(Cursor.WAIT_CURSOR));
			final JDialog progress = GuiUtil.createProgressDialog(this, "Pausing experiment...");
			ThreadUtil.backgroundRun(new Runnable() {
				public void run() {
					model.pause();
				}
			}, new Runnable() {
				public void run() {
					setCursor(Cursor.getPredefinedCursor(Cursor.DEFAULT_CURSOR));
					progress.dispose();
				}
			});
		} else {
			pauseResumeButton.setText("  Pause  ");
			setCursor(Cursor.getPredefinedCursor(Cursor.WAIT_CURSOR));
			final JDialog progress = GuiUtil.createProgressDialog(this, "Resuming experiment...");
			ThreadUtil.backgroundRun(new Runnable() {
				public void run() {
					model.resume();
				}
			}, new Runnable() {
				public void run() {
					setCursor(Cursor.getPredefinedCursor(Cursor.DEFAULT_CURSOR));
					progress.dispose();
				}
			});
		}
	}

	//AC JUICE BUTTON 10/25/21
	void reward(){
		model.reward();
	}
	void start() {
		model.start();
		for (IConsolePlugin p : consolePlugins) {
    		p.startPlugin();
    	}
	}

	public void stop() {
		final JDialog progress = GuiUtil.createProgressDialog(this, "Shuting down experiment...");
		ThreadUtil.backgroundRun(new Runnable() {
			public void run() {
				for (IConsolePlugin p : consolePlugins) {
            		p.stopPlugin();
            	}
				model.stop();
			}
		}, new Runnable() {
			public void run() {
				progress.dispose();
				setVisible(false);
				System.exit(0);
			}
		});
	}

	public void run() {
		start();
		EventQueue.invokeLater(new Runnable() {
			public void run() {
				initComponents();
				setVisible(true);
			}
		});
	}

	public void mousePosition(int x, int y) {
		if (!lockSimulatedEyePos) {
			mouseXCanvas.setText(String.valueOf(x));
			mouseYCanvas.setText(String.valueOf(y));

			AbstractRenderer renderer = consoleRenderer.getRenderer();
			Coordinates2D world = renderer.pixel2coord(new Coordinates2D(x, y));
			Coordinates2D degree = new Coordinates2D(renderer.mm2deg(world.getX()),
					renderer.mm2deg(world.getY()));
			model.setEyePosition(degree);

			mouseXWorld.setText(StringUtil.format(world.getX(), 1));
			mouseYWorld.setText(StringUtil.format(world.getY(), 1));

			mouseXDegree.setText(StringUtil.format(degree.getX(), 1));
			mouseYDegree.setText(StringUtil.format(degree.getY(), 1));
		}
	}

	public void changeCurrentDeviceId(String id) {
		currentDeviceId.set(id);
	}

	void updateEyeWindow() {
		EyeWindow window = model.getEyeWindow();
		Coordinates2D eyeWindowCenter = window.getCenter();

		this.eyeWindowCenterX.setText(StringUtil.format(
				eyeWindowCenter.getX(), 1));
		this.eyeWindowCenterY.setText(StringUtil.format(
				eyeWindowCenter.getY(), 1));
		this.eyeWindowSize.setText(StringUtil.format(window.getSize(), 1));
	}

	void updateEyeDeviceReading() {
		for (Map.Entry<String, EyeDeviceReading> ent : model.getEyeDeviceReading()) {
			String id = ent.getKey();

			EyeDeviceReading reading = ent.getValue();
			Coordinates2D eyeDegree = reading.getDegree();
			Coordinates2D eyeVolt = reading.getVolt();

			if (currentDeviceId.get().equals(id)) {
				this.eyeReadingDegreeX.setText(StringUtil.format(eyeDegree
						.getX(), 1));
				this.eyeReadingDegreeY.setText(StringUtil.format(eyeDegree
						.getY(), 1));
				this.eyeReadingVoltX.setText(StringUtil.format(eyeVolt.getX(),
						1));
				this.eyeReadingVoltY.setText(StringUtil.format(eyeVolt.getY(),
						1));
			}
		}
	}

	protected void updateStatistics() {
		NAFCTrialStatistics stat = model.getNAFCTrialStatistics();

		updateLabelCount(fixationSuccess, stat.getFixationSuccess());
		updateLabelCount(fixationEyeInFail, stat.getFixationEyeInFail());
		updateLabelCount(fixationEyeInHoldFail, stat.getFixationEyeInHoldFail());
		updateLabelCount(sampleSuccess, stat.getSampleSuccess());
		updateLabelCount(sampleEyeInHoldFail, stat.getSampleEyeInHoldFail());
		updateLabelCount(choiceCorrect, stat.getChoiceCorrect());
		updateLabelCount(choiceIncorrect, stat.getChoiceIncorrect());
		updateLabelCount(choiceRewardedIncorrect, stat.getChoiceRewardedIncorrect());
		updateLabelCount(choiceEyeFail, stat.getChoiceEyeFail());
		updateLabelCount(completeTrialCount,stat.getCompleteTrials());
	}

	public void updateLabelCount(JLabel label, int trialCount) {
		String lastCount = label.getText();
		String thisCount = StringUtil.format(trialCount, 0);
		label.setText(thisCount);
		if (thisCount.equals(lastCount)) {
			label.setForeground(Color.BLACK);
		} else {
			label.setForeground(Color.RED);
		}
	}

	void updateEyeZero() {
		Coordinates2D eyeZero = model.getEyeZero(currentDeviceId.get());
		this.eyeZeroX.setText(StringUtil.format(eyeZero.getX(), 1));
		this.eyeZeroY.setText(StringUtil.format(eyeZero.getY(), 1));
	}

	protected Canvas getCanvas() {
		try {
			return new org.lwjgl.opengl.AWTGLCanvas() {
				private static final long serialVersionUID = 392316101235320412L;

				protected void initGL() {
					int x = (int)(monkeyScreenDimension.getX() / canvasScaleFactor);
					int y = (int)(monkeyScreenDimension.getY() / canvasScaleFactor);
					consoleRenderer.getRenderer().init(x, y);
				}

				protected void paintGL() {
					Context context = new Context();
					consoleRenderer.getRenderer().draw(new Drawable() {
						public void draw(Context context) {
							//Drawing the choices, etc.
							consoleRenderer.drawCanvas(context, currentDeviceId.get());
							if (!isMonitorMode()) {
								currentPlugin.drawCanvas(context, currentDeviceId.get());
							}
							updateEyeDeviceReading();
							updateStatistics();
							updateEyeZero();
							updateEyeWindow();

							modeLabel.setText("<html><strong>Mode: " +
									GuiUtil.getKeyText(isMonitorMode() ? monitorToken.getKeyCode() : currentPlugin.getToken().getKeyCode()) + "</strong></html>");
						}
					}, context);
					try {
						swapBuffers();
					} catch (LWJGLException e) {
					}
				}
			};
		} catch (LWJGLException e) {
			throw new org.xper.exception.XGLException(e);
		}
	}

    protected JLabel completeTrialCount;
    protected Canvas consoleCanvas;
    protected JComboBox eyeDeviceSelect;
    protected JLabel eyeReadingDegreeX;
    protected JLabel eyeReadingDegreeY;
    protected JLabel eyeReadingVoltX;
    protected JLabel eyeReadingVoltY;
    protected JLabel eyeWindowCenterX;
    protected JLabel eyeWindowCenterY;
    protected JLabel eyeWindowSize;
    protected JLabel eyeZeroX;
    protected JLabel eyeZeroY;
    protected JLabel mouseXCanvas;
    protected JLabel mouseXDegree;
    protected JLabel mouseXWorld;
    protected JLabel mouseYCanvas;
    protected JLabel mouseYDegree;
    protected JLabel mouseYWorld;
    protected JLabel modeLabel;
    protected JButton pauseResumeButton;
    protected JButton rewardButton;
    //////
    protected JLabel fixationSuccess;
    protected JLabel fixationEyeInFail;
    protected JLabel fixationEyeInHoldFail;
    protected JLabel sampleSuccess;
    protected JLabel sampleEyeInHoldFail;
    protected JLabel choiceCorrect;
    protected JLabel choiceIncorrect;
    protected JLabel choiceRewardedIncorrect;
    protected JLabel choiceEyeFail;

	public void messageReceived() {
		SwingUtilities.invokeLater(new Runnable() {
			public void run() {
				consoleCanvas.repaint();
			}
		});
	}

	public boolean isPaused() {
		return paused;
	}

	public void setPaused(boolean paused) {
		this.paused = paused;
	}

	public Coordinates2D getMonkeyScreenDimension() {
		return monkeyScreenDimension;
	}

	public void setMonkeyScreenDimension(Coordinates2D monkeyScreenDimension) {
		this.monkeyScreenDimension = monkeyScreenDimension;
		this.monkeyScreenDimension.setX(this.monkeyScreenDimension.getX());
	}

	public NAFCExperimentConsoleRenderer getConsoleRenderer() {
		return consoleRenderer;
	}

	public void setConsoleRenderer(NAFCExperimentConsoleRenderer consoleRenderer) {
		this.consoleRenderer = consoleRenderer;
	}

	public NAFCExperimentConsoleModel getModel() {
		return model;
	}

	public void setModel(NAFCExperimentConsoleModel model) {
		this.model = model;
	}

	public double getCanvasScaleFactor() {
		return canvasScaleFactor;
	}

	public void setCanvasScaleFactor(double canvasScaleFactor) {
		this.canvasScaleFactor = canvasScaleFactor;
	}

	public List<IConsolePlugin> getConsolePlugins() {
		return consolePlugins;
	}

	public void setConsolePlugins(List<IConsolePlugin> consolePlugins) {
		this.consolePlugins = consolePlugins;
	}

	public JLabel getCompleteTrialCount() {
		return completeTrialCount;
	}


}