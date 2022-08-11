package org.xper.sach.gui.view;

import java.awt.Dimension;
import java.awt.Font;
import java.awt.Frame;
import java.util.Set;
import java.util.TreeSet;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JLabel;
import javax.swing.JList;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.ListModel;
import javax.swing.SwingConstants;

public class ConfigVariableSetDialog extends JDialog {

	private static final long serialVersionUID = 1L;

	private JPanel dialogContentPane = null;

	private JLabel allVariableLabel = null;

	private JList allVariableList = null;
	
	private TreeSet<String> allVariables = null;
	
	private TreeSet<String> visibleVariables = null;

	private JPanel allVariablePanel = null;

	private JPanel visibleVariablePanel = null;

	private JPanel selectPanel = null;

	private JPanel okPanel = null;

	private JLabel visibleVariableLabel = null;
	
	private String variableSetName = null;

	private JButton selectButton = null;

	private JButton unselectButton = null;

	private JList visibleVariableList = null;

	private JButton okButton = null;

	private JButton cancelButton = null;
	
	private TreeSet<String> returnVisibleVariables = null;

	private JScrollPane allVariableScrollPane = null;

	private JScrollPane visibleVariableScrollPane = null;

	/**
	 * @param owner
	 */
	public ConfigVariableSetDialog(Frame owner, String setName, Set<String> allVariables, Set<String> visibleVariables) {
		super(owner, true);
		this.variableSetName = setName;
		this.allVariables = new TreeSet<String>(allVariables);
		this.visibleVariables = new TreeSet<String>(visibleVariables);
		// Remove visibleVariables from all variables
		for (String v : this.visibleVariables) {
			if (this.allVariables.contains(v)) {
				this.allVariables.remove(v);
			}
		}
		initialize();
	}

	/**
	 * This method initializes this
	 * 
	 * @return void
	 */
	private void initialize() {
		//this.setSize(600, 500);
		this.setContentPane(getDialogContentPane());
		pack();
		setLocationRelativeTo(getOwner());
	}

	/**
	 * This method initializes dialogContentPane
	 * 
	 * @return javax.swing.JPanel
	 */
	private JPanel getDialogContentPane() {
		if (dialogContentPane == null) {
			allVariableLabel = new JLabel();
			allVariableLabel.setText("All System Variables");
			allVariableLabel.setFont(new Font("Dialog", Font.PLAIN, 12));
			allVariableLabel.setHorizontalAlignment(SwingConstants.LEFT);
			allVariableLabel.setAlignmentX(LEFT_ALIGNMENT);
			dialogContentPane = new JPanel();
			dialogContentPane.setLayout(new BoxLayout(dialogContentPane, BoxLayout.LINE_AXIS));
			dialogContentPane.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));
			dialogContentPane.add(getAllVariablePanel(), null);
			dialogContentPane.add(getSelectPanel(), null);
			dialogContentPane.add(getVisibleVariablePanel(), null);
			dialogContentPane.add(getOkPanel(), null);
		}
		return dialogContentPane;
	}

	/**
	 * This method initializes allVariableList	
	 * 	
	 * @return javax.swing.JList	
	 */
	private JList getAllVariableList() {
		if (allVariableList == null) {
			allVariableList = new JList(allVariables.toArray());
			allVariableList.setFont(new Font("Dialog", Font.PLAIN, 12));
			allVariableList
					.addListSelectionListener(new javax.swing.event.ListSelectionListener() {
						public void valueChanged(javax.swing.event.ListSelectionEvent e) {
							if (allVariableList.getSelectedIndices().length > 0) {
								getSelectButton().setEnabled(true);
							} else {
								getSelectButton().setEnabled(false);
							}
						}
					});
		}
		return allVariableList;
	}

	/**
	 * This method initializes allVariablePanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getAllVariablePanel() {
		if (allVariablePanel == null) {
			allVariablePanel = new JPanel();
			allVariablePanel.setLayout(new BoxLayout(allVariablePanel, BoxLayout.PAGE_AXIS));
			allVariablePanel.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));
			allVariablePanel.add(allVariableLabel, null);
			allVariablePanel.add(getAllVariableScrollPane(), null);
		}
		return allVariablePanel;
	}

	/**
	 * This method initializes visibleVariablePanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getVisibleVariablePanel() {
		if (visibleVariablePanel == null) {
			visibleVariableLabel = new JLabel();
			visibleVariableLabel.setText(variableSetName);
			visibleVariableLabel.setFont(new Font("Dialog", Font.PLAIN, 12));
			visibleVariableLabel.setHorizontalAlignment(SwingConstants.LEFT);
			visibleVariableLabel.setAlignmentX(LEFT_ALIGNMENT);
			visibleVariablePanel = new JPanel();
			visibleVariablePanel.setLayout(new BoxLayout(visibleVariablePanel, BoxLayout.PAGE_AXIS));
			visibleVariablePanel.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));
			visibleVariablePanel.add(visibleVariableLabel, null);
			visibleVariablePanel.add(getVisibleVariableScrollPane(), null);
		}
		return visibleVariablePanel;
	}

	/**
	 * This method initializes selectPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getSelectPanel() {
		if (selectPanel == null) {
			selectPanel = new JPanel();
			selectPanel.setLayout(new BoxLayout(selectPanel, BoxLayout.PAGE_AXIS));
			selectPanel.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));
			selectPanel.add(getSelectButton(), null);
			selectPanel.add(Box.createRigidArea(new Dimension(0, 5)));
			selectPanel.add(getUnselectButton(), null);
		}
		return selectPanel;
	}

	/**
	 * This method initializes okPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getOkPanel() {
		if (okPanel == null) {
			okPanel = new JPanel();
			okPanel.setLayout(new BoxLayout(okPanel, BoxLayout.Y_AXIS));
			okPanel.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));
			okPanel.add(Box.createRigidArea(new Dimension(0, 11)));
			okPanel.add(getOkButton(), null);
			okPanel.add(Box.createRigidArea(new Dimension(0, 5)));
			okPanel.add(getCancelButton(), null);
			okPanel.add(Box.createVerticalGlue());
		}
		return okPanel;
	}

	/**
	 * This method initializes selectButton	
	 * 	
	 * @return javax.swing.JButton	
	 */
	private JButton getSelectButton() {
		if (selectButton == null) {
			selectButton = new JButton();
			selectButton.setText(">>");
			selectButton.setEnabled(false);
			selectButton.addActionListener(new java.awt.event.ActionListener() {
				public void actionPerformed(java.awt.event.ActionEvent e) {
					Object[] selected = getAllVariableList().getSelectedValues();
					for (Object s : selected) {
						visibleVariables.add((String)s);
						allVariables.remove(s);
						getAllVariableList().setListData(allVariables.toArray());
						getVisibleVariableList().setListData(visibleVariables.toArray());
					}
				}
			});
		}
		return selectButton;
	}

	/**
	 * This method initializes unselectButton	
	 * 	
	 * @return javax.swing.JButton	
	 */
	private JButton getUnselectButton() {
		if (unselectButton == null) {
			unselectButton = new JButton();
			unselectButton.setText("<<");
			unselectButton.setEnabled(false);
			unselectButton.addActionListener(new java.awt.event.ActionListener() {
				public void actionPerformed(java.awt.event.ActionEvent e) {
					Object[] selected = getVisibleVariableList().getSelectedValues();
					for (Object s: selected) {
						visibleVariables.remove(s);
						allVariables.add((String)s);
						getAllVariableList().setListData(allVariables.toArray());
						getVisibleVariableList().setListData(visibleVariables.toArray());
					}
				}
			});
		}
		return unselectButton;
	}

	/**
	 * This method initializes visibleVariableList	
	 * 	
	 * @return javax.swing.JList	
	 */
	private JList getVisibleVariableList() {
		if (visibleVariableList == null) {
			visibleVariableList = new JList(visibleVariables.toArray());
			visibleVariableList.setFont(new Font("Dialog", Font.PLAIN, 12));
			visibleVariableList
					.addListSelectionListener(new javax.swing.event.ListSelectionListener() {
						public void valueChanged(javax.swing.event.ListSelectionEvent e) {
							if (visibleVariableList.getSelectedIndices().length > 0) {
								getUnselectButton().setEnabled(true);
							} else {
								getUnselectButton().setEnabled(false);
							}
						}
					});
		}
		return visibleVariableList;
	}

	/**
	 * This method initializes okButton	
	 * 	
	 * @return javax.swing.JButton	
	 */
	private JButton getOkButton() {
		if (okButton == null) {
			okButton = new JButton();
			okButton.setText("   OK    ");
			okButton.setPreferredSize(new Dimension(73, 26));
			okButton.setFont(new Font("Dialog", Font.PLAIN, 12));
			okButton.addActionListener(new java.awt.event.ActionListener() {
				public void actionPerformed(java.awt.event.ActionEvent e) {
					ListModel model = visibleVariableList.getModel();
					int n = model.getSize();
					returnVisibleVariables = new TreeSet<String>();
					for (int i = 0; i < n; i ++) {
						returnVisibleVariables.add((String)model.getElementAt(i));
					}
					setVisible(false);
				}
			});
		}
		return okButton;
	}

	/**
	 * This method initializes cancelButton	
	 * 	
	 * @return javax.swing.JButton	
	 */
	private JButton getCancelButton() {
		if (cancelButton == null) {
			cancelButton = new JButton();
			cancelButton.setText("Cancel");
			cancelButton.setFont(new Font("Dialog", Font.PLAIN, 12));
			cancelButton.addActionListener(new java.awt.event.ActionListener() {
				public void actionPerformed(java.awt.event.ActionEvent e) {
					setVisible(false);
				}
			});
		}
		return cancelButton;
	}
	
	public TreeSet<String> showDialog() {
		setVisible(true);
		return returnVisibleVariables;
	}

	/**
	 * This method initializes allVariableScrollPane	
	 * 	
	 * @return javax.swing.JScrollPane	
	 */
	private JScrollPane getAllVariableScrollPane() {
		if (allVariableScrollPane == null) {
			allVariableScrollPane = new JScrollPane();
			allVariableScrollPane.setPreferredSize(new Dimension(300, 200));
			allVariableScrollPane.setViewportView(getAllVariableList());
		}
		return allVariableScrollPane;
	}

	/**
	 * This method initializes visibleVariableScrollPane	
	 * 	
	 * @return javax.swing.JScrollPane	
	 */
	private JScrollPane getVisibleVariableScrollPane() {
		if (visibleVariableScrollPane == null) {
			visibleVariableScrollPane = new JScrollPane();
			visibleVariableScrollPane.setPreferredSize(new Dimension(300, 200));
			visibleVariableScrollPane.setViewportView(getVisibleVariableList());
		}
		return visibleVariableScrollPane;
	}

}
