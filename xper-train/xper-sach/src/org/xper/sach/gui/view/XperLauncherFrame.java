package org.xper.sach.gui.view;

import java.awt.BorderLayout;
import java.awt.CardLayout;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyEvent;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.prefs.Preferences;

import javax.swing.BorderFactory;
import javax.swing.ImageIcon;
import javax.swing.JButton;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JMenu;
import javax.swing.JMenuBar;
import javax.swing.JMenuItem;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JPopupMenu;
import javax.swing.JScrollPane;
import javax.swing.JSplitPane;
import javax.swing.JTabbedPane;
import javax.swing.JTable;
import javax.swing.JTextField;
import javax.swing.JTree;
import javax.swing.ListSelectionModel;
import javax.swing.border.TitledBorder;
import javax.swing.event.TreeModelEvent;
import javax.swing.event.TreeModelListener;
import javax.swing.event.TreeSelectionEvent;
import javax.swing.event.TreeSelectionListener;
import javax.swing.tree.DefaultMutableTreeNode;
import javax.swing.tree.DefaultTreeCellRenderer;
import javax.swing.tree.DefaultTreeModel;
import javax.swing.tree.TreePath;
import javax.swing.tree.TreeSelectionModel;

import org.jdesktop.swingx.JXTreeTable;
import org.jdesktop.swingx.treetable.TreeTableModel;
import org.xper.sach.gui.model.VariableSet;
import org.xper.sach.gui.model.XperLauncherModel;

public class XperLauncherFrame extends JFrame {
	
	private XperLauncherModel model;  //  @jve:decl-index=0:
	
	Preferences prefs;
	
	int newVariableSetIndex = 0;

	private static final long serialVersionUID = 1L;

	private JPanel topContentPane = null;

	private JMenuBar mainMenuBar = null;

	private JMenu experimentMenu = null;

	private JMenuItem exitMenuItem = null;

	private JSplitPane topSplitPane = null;

	private JTabbedPane leftTabbedPane = null;

	private JPanel systemVarPanel = null;

	private JPanel experimentPanel = null;

	private JPanel acqDataPanel = null;

	private JPanel rightPanel = null;

	private JPanel systemVariableViewPanel = null;

	private JTree variableSetTree = null;

	private JMenu systemVariableMenu = null;
	
	private JXTreeTable variableTreeTable = null;
	
	private ArrayList<JMenuItem> addVariableSetMenuItemList = new ArrayList<JMenuItem>();  //  @jve:decl-index=0:
	private ArrayList<JMenuItem> removeVariableSetMenuItemList = new ArrayList<JMenuItem>();
	private ArrayList<JMenuItem> renameVariableSetMenuItemList = new ArrayList<JMenuItem>();
	private ArrayList<JMenuItem> configVariableSetMenuItemList = new ArrayList<JMenuItem>();  //  @jve:decl-index=0:
	private ArrayList<JMenuItem> reloadSystemVariablesMenuItemList = new ArrayList<JMenuItem>();  //  @jve:decl-index=0:

	/**
	 * This method initializes mainMenuBar	
	 * 	
	 * @return javax.swing.JMenuBar	
	 */
	private JMenuBar getMainMenuBar() {
		if (mainMenuBar == null) {
			mainMenuBar = new JMenuBar();
			mainMenuBar.add(getXperMenu());
			mainMenuBar.add(getExperimentMenu());
			mainMenuBar.add(getSystemVariableMenu());
			mainMenuBar.add(getAcqDataMenu());
		}
		return mainMenuBar;
	}

	/**
	 * This method initializes experimentMenu	
	 * 	
	 * @return javax.swing.JMenu	
	 */
	private JMenu getExperimentMenu() {
		if (experimentMenu == null) {
			experimentMenu = new JMenu();
			experimentMenu.setText("Experiment");
			experimentMenu.setMnemonic(KeyEvent.VK_E);
			experimentMenu.setFont(new Font("Dialog", Font.PLAIN, 12));
		}
		return experimentMenu;
	}

	/**
	 * This method initializes exitMenuItem	
	 * 	
	 * @return javax.swing.JMenuItem	
	 */
	private JMenuItem getExitMenuItem() {
		if (exitMenuItem == null) {
			exitMenuItem = new JMenuItem();
			exitMenuItem.setText("Exit");
			exitMenuItem.setMnemonic(KeyEvent.VK_X);
			exitMenuItem.addActionListener(new java.awt.event.ActionListener() {
				public void actionPerformed(java.awt.event.ActionEvent e) {
					postClosingEvent();
				}
			});
		}
		return exitMenuItem;
	}
	
	void postClosingEvent () {
		this.dispatchEvent(new WindowEvent(this, WindowEvent.WINDOW_CLOSING));
	}

	/**
	 * This method initializes topSplitPane	
	 * 	
	 * @return javax.swing.JSplitPane	
	 */
	private JSplitPane getTopSplitPane() {
		if (topSplitPane == null) {
			topSplitPane = new JSplitPane();
			topSplitPane.setLeftComponent(getLeftTabbedPane());
			topSplitPane.setRightComponent(getRightPanel());
		}
		return topSplitPane;
	}
	
	static String SYSTEM_VARIABLE_TAB = "System Variable";  //  @jve:decl-index=0:
	static String EXPERIMENT_TAB = "Experiment";  //  @jve:decl-index=0:
	static String ACQUIRED_DATA_TAB = "Acquired Data";  //  @jve:decl-index=0:

	/**
	 * This method initializes leftTabbedPane	
	 * 	
	 * @return javax.swing.JTabbedPane	
	 */
	private JTabbedPane getLeftTabbedPane() {
		if (leftTabbedPane == null) {
			leftTabbedPane = new JTabbedPane();
			leftTabbedPane.setPreferredSize(new Dimension(300, 1000));
			leftTabbedPane.setFont(new Font("Dialog", Font.PLAIN, 12));
			leftTabbedPane.addTab(EXPERIMENT_TAB, null, getExperimentPanel(), null);
			leftTabbedPane.addTab(SYSTEM_VARIABLE_TAB, null, getSystemVarPanel(), null);
			leftTabbedPane.addTab(ACQUIRED_DATA_TAB, null, getAcqDataPanel(), null);
			leftTabbedPane.addChangeListener(new javax.swing.event.ChangeListener() {
				public void stateChanged(javax.swing.event.ChangeEvent e) {
					CardLayout c = (CardLayout)getRightPanel().getLayout();
					if (leftTabbedPane.getSelectedIndex() == leftTabbedPane.indexOfTab(SYSTEM_VARIABLE_TAB)) {
						getSystemVariableMenu().setEnabled(true);
						c.show(getRightPanel(), getSystemVariableViewPanel().getName());
					} else {
						getSystemVariableMenu().setEnabled(false);
					}
					if (leftTabbedPane.getSelectedIndex() == leftTabbedPane.indexOfTab(EXPERIMENT_TAB)) {
						getExperimentMenu().setEnabled(true);
						c.show(getRightPanel(), getExperimentViewPanel().getName());
					} else {
						getExperimentMenu().setEnabled(false);
					}
					if (leftTabbedPane.getSelectedIndex() == leftTabbedPane.indexOfTab(ACQUIRED_DATA_TAB)) {
						getAcqDataMenu().setEnabled(true);
						c.show(getRightPanel(), getAcqDataViewPanel().getName());
					} else {
						getAcqDataMenu().setEnabled(false);
					}
				}
			});
		}
		return leftTabbedPane;
	}

	/**
	 * This method initializes systemVarPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getSystemVarPanel() {
		if (systemVarPanel == null) {
			GridBagConstraints gridBagConstraints = new GridBagConstraints();
			gridBagConstraints.fill = GridBagConstraints.BOTH;
			gridBagConstraints.weighty = 1.0;
			gridBagConstraints.weightx = 1.0;
			systemVarPanel = new JPanel();
			systemVarPanel.setLayout(new GridBagLayout());
			systemVarPanel.add(getVariableSetTree(), gridBagConstraints);
		}
		return systemVarPanel;
	}

	/**
	 * This method initializes experimentPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getExperimentPanel() {
		if (experimentPanel == null) {
			experimentPanel = new JPanel();
			experimentPanel.setLayout(new GridBagLayout());
			experimentPanel.setName("");
		}
		return experimentPanel;
	}

	/**
	 * This method initializes acqDataPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getAcqDataPanel() {
		if (acqDataPanel == null) {
			acqDataPanel = new JPanel();
			acqDataPanel.setLayout(new BorderLayout());
			acqDataPanel.add(getAcqSessionCriteriaPanel(), BorderLayout.PAGE_START);
			acqDataPanel.add(getAcqSessionScrollPane(), BorderLayout.CENTER);
		}
		return acqDataPanel;
	}

	/**
	 * This method initializes rightPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getRightPanel() {
		if (rightPanel == null) {
			rightPanel = new JPanel();
			rightPanel.setLayout(new CardLayout());
			rightPanel.add(getExperimentViewPanel(), getExperimentViewPanel().getName());
			rightPanel.add(getSystemVariableViewPanel(), getSystemVariableViewPanel().getName());
			rightPanel.add(getAcqDataViewPanel(), getAcqDataViewPanel().getName());
		}
		return rightPanel;
	}

	/**
	 * This method initializes systemVariableViewPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getSystemVariableViewPanel() {
		if (systemVariableViewPanel == null) {
			GridBagConstraints gridBagConstraints1 = new GridBagConstraints();
			gridBagConstraints1.fill = GridBagConstraints.BOTH;
			gridBagConstraints1.weighty = 1.0;
			gridBagConstraints1.weightx = 1.0;
			systemVariableViewPanel = new JPanel();
			systemVariableViewPanel.setLayout(new GridBagLayout());
			systemVariableViewPanel.setName("systemVariableViewPanel");
			systemVariableViewPanel.add(getVariableSetTreeTableScrollPane(), gridBagConstraints1);
		}
		return systemVariableViewPanel;
	}

	/**
	 * This method initializes variableSetTree	
	 * 	
	 * @return javax.swing.JTree	
	 */
	private JTree getVariableSetTree() {
		if (variableSetTree == null) {
			DefaultMutableTreeNode rootNode = new DefaultMutableTreeNode("System Variable Sets");
			DefaultTreeModel treeModel = new DefaultTreeModel(rootNode);
			List<VariableSet> variableSets = model.getVariableSets();
			for (VariableSet set: variableSets) {
				DefaultMutableTreeNode childNode =
		            new DefaultMutableTreeNode(set.getName(), false);
				treeModel.insertNodeInto(childNode, rootNode, rootNode.getChildCount());
			}
			treeModel.addTreeModelListener(new TreeModelListener(){
				public void treeNodesChanged(TreeModelEvent e) {
					int ind = e.getChildIndices()[0];
					DefaultMutableTreeNode  node = (DefaultMutableTreeNode)(e.getTreePath().getLastPathComponent());
					node = (DefaultMutableTreeNode)(node.getChildAt(ind));
					String name = (String)node.getUserObject();
					model.renameVariableSet(ind, name);
				}

				public void treeNodesInserted(TreeModelEvent e) {
					int ind = e.getChildIndices()[0];
					DefaultMutableTreeNode  node = (DefaultMutableTreeNode)(e.getTreePath().getLastPathComponent());
					node = (DefaultMutableTreeNode)(node.getChildAt(ind));
					String name = (String)node.getUserObject();
					model.insertVariableSet(ind, name);
				}

				public void treeNodesRemoved(TreeModelEvent e) {
					int ind = e.getChildIndices()[0];
					model.removeVariableSet(ind);
				}

				public void treeStructureChanged(TreeModelEvent e) {
				}
			});
			variableSetTree = new JTree(treeModel);
			variableSetTree.getSelectionModel().setSelectionMode(TreeSelectionModel.SINGLE_TREE_SELECTION);
			variableSetTree.setShowsRootHandles(true);
			//variableSetTree.setRootVisible(false);
			VariableSetTreeCellEditor cellEditor = new VariableSetTreeCellEditor(variableSetTree, new DefaultTreeCellRenderer());
			variableSetTree.setCellEditor(cellEditor);
			variableSetTree.setCellRenderer(new VariableSetCellRenderer());
			variableSetTree.addTreeSelectionListener(new TreeSelectionListener() {
						public void valueChanged(TreeSelectionEvent e) {
							updateVariableSet();
						}
					});
			variableSetTree.addMouseListener(new java.awt.event.MouseAdapter() {
				public void mouseReleased(java.awt.event.MouseEvent e) {
					if (e.isPopupTrigger()) {
						getVariableSetPopupMenu().show(e.getComponent(), e.getX(), e.getY());
			        }
				}
			});
		}
		return variableSetTree;
	}
	
	void updateVariableSet () {
		TreePath path = getVariableSetTree().getSelectionPath();
		if (path != null) {
			DefaultMutableTreeNode  node = (DefaultMutableTreeNode)(path.getLastPathComponent());
			VariableSet set = model.getVariableSet((String)node.getUserObject());
			VariableTableModel treeTableModel = (VariableTableModel)getVariableTreeTable().getTreeTableModel();
			treeTableModel.update(set);
		} else {
			VariableTableModel treeTableModel = (VariableTableModel)getVariableTreeTable().getTreeTableModel();
			treeTableModel.update(null);
		}
	}
	
	public void addVariableSet(String childName) {
		childName = JOptionPane.showInputDialog(this, "Please specify name of the variable set", childName);
		DefaultTreeModel model = (DefaultTreeModel)getVariableSetTree().getModel();
		DefaultMutableTreeNode parentNode = (DefaultMutableTreeNode)model.getRoot();
	    
		DefaultMutableTreeNode childNode =
            new DefaultMutableTreeNode(childName, false);
		model.insertNodeInto(childNode, parentNode, parentNode.getChildCount());
		TreePath path = new TreePath(childNode.getPath());
		getVariableSetTree().scrollPathToVisible(path);
		getVariableSetTree().setSelectionPath(path);
	}

	/**
	 * This method initializes systemVariableMenu	
	 * 	
	 * @return javax.swing.JMenu	
	 */
	private JMenu getSystemVariableMenu() {
		if (systemVariableMenu == null) {
			systemVariableMenu = new JMenu();
			systemVariableMenu.setText("System Variable");
			systemVariableMenu.setFont(new Font("Dialog", Font.PLAIN, 12));
			systemVariableMenu.setMnemonic(KeyEvent.VK_V);
			systemVariableMenu.add(getAddVariableSetMenuItem());
			systemVariableMenu.add(getRemoveVariableSetMenuItem());
			systemVariableMenu.add(getRenameVariableSetMenuItem());
			systemVariableMenu.addSeparator();
			systemVariableMenu.add(getConfigVariableSetMenuItem());
			systemVariableMenu.addSeparator();
			systemVariableMenu.add(getReloadSystemVarMenuItem());
			
			if (getLeftTabbedPane().getSelectedIndex() == getLeftTabbedPane().indexOfTab(SYSTEM_VARIABLE_TAB)) {
				systemVariableMenu.setEnabled(true);
			} else {
				systemVariableMenu.setEnabled(false);
			}
			
			systemVariableMenu.addChangeListener(new javax.swing.event.ChangeListener() {
				public void stateChanged(javax.swing.event.ChangeEvent e) {
					updateSystemVariableMenu();
				}
			});
		}
		return systemVariableMenu;
	}
	
	void updateSystemVariableMenu() {
		TreePath path = getVariableSetTree().getSelectionPath();
		if (path != null) {
			DefaultMutableTreeNode node = (DefaultMutableTreeNode)path.getLastPathComponent();
			if (node != null & node.isLeaf()) {
				for(JMenuItem menu : removeVariableSetMenuItemList) {
					menu.setEnabled(true);
				}
				for (JMenuItem menu : renameVariableSetMenuItemList) {
					menu.setEnabled(true);
				}
				for (JMenuItem menu : configVariableSetMenuItemList) {
					menu.setEnabled(true);
				}
			} else {
				for(JMenuItem menu : removeVariableSetMenuItemList) {
					menu.setEnabled(false);
				}
				for (JMenuItem menu : renameVariableSetMenuItemList) {
					menu.setEnabled(false);
				}
				for (JMenuItem menu : configVariableSetMenuItemList) {
					menu.setEnabled(false);
				}
			}
		} else {
			for(JMenuItem menu : removeVariableSetMenuItemList) {
				menu.setEnabled(false);
			}
			for (JMenuItem menu : renameVariableSetMenuItemList) {
				menu.setEnabled(false);
			}
			for (JMenuItem menu : configVariableSetMenuItemList) {
				menu.setEnabled(false);
			}
		}
	}
	
	static String ADD_VARIABLE_SET_MENU = "Add Set";

	/**
	 * This method initializes addVariableSetMenuItem	
	 * Create one for each menu.
	 * 	
	 * @return javax.swing.JMenuItem	
	 */
	private JMenuItem getAddVariableSetMenuItem() {
		JMenuItem addVariableSetMenuItem = new JMenuItem();
		addVariableSetMenuItem.setText(ADD_VARIABLE_SET_MENU);
		addVariableSetMenuItem.setMnemonic(KeyEvent.VK_A);
		addVariableSetMenuItem.setFont(new Font("Dialog", Font.PLAIN, 12));
		addVariableSetMenuItem.addActionListener(new ActionListener() {
			public void actionPerformed(ActionEvent e) {
				getLeftTabbedPane().setSelectedIndex(getLeftTabbedPane().indexOfTab(SYSTEM_VARIABLE_TAB));
				addVariableSet("New Variable Set " + newVariableSetIndex);
				newVariableSetIndex ++;
			}
		});
		addVariableSetMenuItemList.add(addVariableSetMenuItem);
		return addVariableSetMenuItem;
	}
	
	static String REMOVE_VARIABLE_SET_MENU = "Delete Set";  //  @jve:decl-index=0:

	/**
	 * This method initializes removeVariableSetMenuItem	
	 * 	
	 * @return javax.swing.JMenuItem	
	 */
	private JMenuItem getRemoveVariableSetMenuItem() {
		JMenuItem removeVariableSetMenuItem = new JMenuItem();
		removeVariableSetMenuItem.setText(REMOVE_VARIABLE_SET_MENU);
		removeVariableSetMenuItem.setIcon(new ImageIcon(this.getClass().getResource("images/delete.png")));
		removeVariableSetMenuItem.setMnemonic(KeyEvent.VK_D);
		removeVariableSetMenuItem.setFont(new Font("Dialog", Font.PLAIN, 12));
		removeVariableSetMenuItem
				.addActionListener(new java.awt.event.ActionListener() {
					public void actionPerformed(ActionEvent e) {
						removeSystemVariableSet();
					}
				});
	    removeVariableSetMenuItemList.add(removeVariableSetMenuItem);
		return removeVariableSetMenuItem;
	}
	
	void removeSystemVariableSet() {
	    TreePath path = getVariableSetTree().getSelectionPath();

	    if (path == null) {
			JOptionPane.showMessageDialog(this, "No system variable set selected.");
	    } else {
	    	DefaultMutableTreeNode node = (DefaultMutableTreeNode)(path.getLastPathComponent());
	    	if (node.isLeaf()) {
		    	int answer = JOptionPane.showConfirmDialog(this, 
		    			"Delete system variable set \"" + node.getUserObject() + "\"?", 
		    			"Please confirm", JOptionPane.YES_NO_OPTION);
		    	if (answer == JOptionPane.YES_OPTION) {
		    		DefaultTreeModel model = (DefaultTreeModel)getVariableSetTree().getModel();
		    		model.removeNodeFromParent(node);
		    	}
	    	} else {
	    		JOptionPane.showMessageDialog(this, "Cannot delete root node.");
	    	}
	    }
	}
	
	static String RENAME_VARIABLE_SET_MENU = "Rename Set";  //  @jve:decl-index=0:

	/**
	 * This method initializes renameVariableSetMenuItem	
	 * 	
	 * @return javax.swing.JMenuItem	
	 */
	private JMenuItem getRenameVariableSetMenuItem() {
		JMenuItem renameVariableSetMenuItem = new JMenuItem();
		renameVariableSetMenuItem.setMnemonic(KeyEvent.VK_N);
		renameVariableSetMenuItem.setText(RENAME_VARIABLE_SET_MENU);
		renameVariableSetMenuItem.setFont(new Font("Dialog", Font.PLAIN, 12));
		renameVariableSetMenuItem
				.addActionListener(new java.awt.event.ActionListener() {
					public void actionPerformed(java.awt.event.ActionEvent e) {
						renameVariableSet();
					}
				});
		renameVariableSetMenuItemList.add(renameVariableSetMenuItem);
		return renameVariableSetMenuItem;
	}
	
	void renameVariableSet() {
		TreePath path = getVariableSetTree().getSelectionPath();

	    if (path == null) {
			JOptionPane.showMessageDialog(this, "No system variable set selected.");
	    } else {
	    	DefaultMutableTreeNode node = (DefaultMutableTreeNode)(path.getLastPathComponent());
	    	if (node.isLeaf()) {
	    		String childName = JOptionPane.showInputDialog(this, "Please specify name of the variable set", node.getUserObject());
	    		if (childName != null) {
	    			if (childName.trim().length() > 0) {
	    				DefaultTreeModel model = (DefaultTreeModel)getVariableSetTree().getModel();
	    				node.setUserObject(childName);
	    				model.nodeChanged(node);
	    			} else {
	    				JOptionPane.showMessageDialog(this, "Empty string is not allowed.");
	    			}
	    		}
	    	} else {
	    		JOptionPane.showMessageDialog(this, "Cannot rename root node.");
	    	}
	    }
	}

	/**
	 * This is the default constructor
	 */
	public XperLauncherFrame(XperLauncherModel model) {
		super();
		this.model = model;
		prefs = Preferences.userNodeForPackage(this.getClass());
		initialize();
	}
	
	static String FRAME_WIDTH = "frame_width";  //  @jve:decl-index=0:
	static String FRAME_HEIGHT = "frame_height";
	static String FRAME_MAXIMIZED = "frame_maximized";
	static String FRAME_LOCATION_X = "frame_location_x";
	static String FRAME_LOCATION_Y = "frame_location_y";

	private JPopupMenu variableSetPopupMenu = null;

	private JScrollPane variableSetTreeTableScrollPane = null;

	private JPopupMenu variableTreeTablePopupMenu = null;

	private JPanel experimentViewPanel = null;

	private JPanel acqDataViewPanel = null;

	private JMenu acqDataMenu = null;

	private JMenu xperMenu = null;

	void savePreferences() {
		int state = getExtendedState();
		if (state == NORMAL) {
			prefs.putInt(FRAME_WIDTH, getSize().width);
			prefs.putInt(FRAME_HEIGHT, getSize().height);
			
			prefs.putInt(FRAME_LOCATION_X, getLocation().x);
			prefs.putInt(FRAME_LOCATION_Y, getLocation().y);
		}
		
		if ((state & MAXIMIZED_BOTH) != 0){
			prefs.putBoolean(FRAME_MAXIMIZED, true);
		} else {
			prefs.putBoolean(FRAME_MAXIMIZED, false);
		}
	}

	/**
	 * This method initializes this
	 * 
	 * @return void
	 */
	private void initialize() {
		int w = prefs.getInt(FRAME_WIDTH, 800);
		int h = prefs.getInt(FRAME_HEIGHT, 600);
		boolean maximized = prefs.getBoolean(FRAME_MAXIMIZED, false);
		this.setSize(w, h);
		if (maximized) {
			setExtendedState(MAXIMIZED_BOTH);
		}
		int x = prefs.getInt(FRAME_LOCATION_X, -1);
		int y = prefs.getInt(FRAME_LOCATION_Y, -1);
		if (x == -1 || y == -1) {
			setLocationRelativeTo(null);
		} else {
			setLocation(x, y);
		}
		this.setJMenuBar(getMainMenuBar());
		this.setContentPane(getTopContentPane());
		this.setTitle("Experiment Laucher");
		this.addWindowListener(new WindowAdapter(){
			public void windowClosing(WindowEvent evt) {
				model.close();
				savePreferences();
				dispose();
				System.exit(0);
			}
		});
		this.setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE);
	}

	/**
	 * This method initializes topContentPane
	 * 
	 * @return javax.swing.JPanel
	 */
	private JPanel getTopContentPane() {
		if (topContentPane == null) {
			topContentPane = new JPanel();
			topContentPane.setLayout(new BorderLayout());
			topContentPane.add(getTopSplitPane(), BorderLayout.CENTER);
		}
		return topContentPane;
	}

	public XperLauncherModel getModel() {
		return model;
	}

	public void setModel(XperLauncherModel model) {
		this.model = model;
	}

	/**
	 * This method initializes variableSetPopupMenu	
	 * 	
	 * @return javax.swing.JPopupMenu	
	 */
	private JPopupMenu getVariableSetPopupMenu() {
		if (variableSetPopupMenu == null) {
			variableSetPopupMenu = new JPopupMenu();
			variableSetPopupMenu.add(getAddVariableSetMenuItem());
			variableSetPopupMenu.add(getRemoveVariableSetMenuItem());
			variableSetPopupMenu.add(getRenameVariableSetMenuItem());
			variableSetPopupMenu.addSeparator();
			variableSetPopupMenu.add(getConfigVariableSetMenuItem());
			variableSetPopupMenu.addSeparator();
			variableSetPopupMenu.add(getReloadSystemVarMenuItem());
			variableSetPopupMenu
					.addPopupMenuListener(new javax.swing.event.PopupMenuListener() {
						public void popupMenuWillBecomeVisible(
								javax.swing.event.PopupMenuEvent e) {
							updateSystemVariableMenu();
						}
						public void popupMenuWillBecomeInvisible(
								javax.swing.event.PopupMenuEvent e) {
						}
						public void popupMenuCanceled(javax.swing.event.PopupMenuEvent e) {
						}
					});
		}
		return variableSetPopupMenu;
	}

	/**
	 * This method initializes variableSetTreeTableScrollPane	
	 * 	
	 * @return javax.swing.JScrollPane	
	 */
	private JScrollPane getVariableSetTreeTableScrollPane() {
		if (variableSetTreeTableScrollPane == null) {
			variableSetTreeTableScrollPane = new JScrollPane(getVariableTreeTable());
		}
		return variableSetTreeTableScrollPane;
	}
	
	private JXTreeTable getVariableTreeTable() {
		if (variableTreeTable == null) {
			TreeTableModel  treeTableModel = new VariableTableModel(model);
			variableTreeTable = new JXTreeTable(treeTableModel);
			ListSelectionModel selectionModel = variableTreeTable.getSelectionModel();
			selectionModel.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
			variableTreeTable.getColumnModel().setSelectionModel(selectionModel);
			variableTreeTable.setLeafIcon(new ImageIcon(this.getClass().getResource("images/variable.gif")));
			//variableTreeTable.setRootVisible(true);
			variableTreeTable.addMouseListener(new java.awt.event.MouseAdapter() {
				public void mouseReleased(java.awt.event.MouseEvent e) {
					if (e.isPopupTrigger()) {
						getVariableTreeTablePopupMenu().show(e.getComponent(), e.getX(), e.getY());
			        }
				}
			});
		} 
		return variableTreeTable;
	}

	/**
	 * This method initializes variableTreeTablePopupMenu	
	 * 	
	 * @return javax.swing.JPopupMenu	
	 */
	private JPopupMenu getVariableTreeTablePopupMenu() {
		if (variableTreeTablePopupMenu == null) {
			variableTreeTablePopupMenu = new JPopupMenu();
			variableTreeTablePopupMenu.add(getConfigVariableSetMenuItem());
			variableTreeTablePopupMenu.addSeparator();
			variableTreeTablePopupMenu.add(getReloadSystemVarMenuItem());
			variableTreeTablePopupMenu
					.addPopupMenuListener(new javax.swing.event.PopupMenuListener() {
						public void popupMenuWillBecomeVisible(
								javax.swing.event.PopupMenuEvent e) {
							updateSystemVariableMenu();
						}
						public void popupMenuWillBecomeInvisible(
								javax.swing.event.PopupMenuEvent e) {
						}
						public void popupMenuCanceled(javax.swing.event.PopupMenuEvent e) {
						}
					});
		}
		return variableTreeTablePopupMenu;
	}

	static String CONFIG_VARIABLE_SET_MENU = "Configure Variable Set";

	/**
	 * This method initializes configVariableSetMenuItem	
	 * 	
	 * @return javax.swing.JMenuItem	
	 */
	private JMenuItem getConfigVariableSetMenuItem() {	
		JMenuItem configVariableSetMenuItem = new JMenuItem();
		configVariableSetMenuItem.setMnemonic(KeyEvent.VK_C);
		configVariableSetMenuItem.setFont(new Font("Dialog", Font.PLAIN, 12));
		configVariableSetMenuItem.setText(CONFIG_VARIABLE_SET_MENU);
		configVariableSetMenuItem
				.addActionListener(new java.awt.event.ActionListener() {
					public void actionPerformed(java.awt.event.ActionEvent e) {
						configVariableSet();
					}
				});
		configVariableSetMenuItemList.add(configVariableSetMenuItem);
		return configVariableSetMenuItem;
	}
	
	void configVariableSet () {
		TreePath path = getVariableSetTree().getSelectionPath();
		if (path == null) {
			JOptionPane.showMessageDialog(this, "No system variable set selected.");
	    } else {
	    	DefaultMutableTreeNode node = (DefaultMutableTreeNode)(path.getLastPathComponent());
	    	if (node.isLeaf()) {
	    		String setName = (String)node.getUserObject();
	    		VariableSet set = model.getVariableSet(setName);
	    		Set<String> allVariables = model.getAllVariables().keySet();
	    		ConfigVariableSetDialog dialog = new ConfigVariableSetDialog(this, setName, 
	    				allVariables, set.getVariables());
	    		TreeSet<String> result = dialog.showDialog();
	    		if (result != null) {
	    			set.setVariables(result);
	    			updateVariableSet();
	    		}
	    	} else {
	    		JOptionPane.showMessageDialog(this, "Cannot config root node.");
	    	}
	    }
	}

	/**
	 * This method initializes experimentViewPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getExperimentViewPanel() {
		if (experimentViewPanel == null) {
			experimentViewPanel = new JPanel();
			experimentViewPanel.setLayout(new GridBagLayout());
			experimentViewPanel.setName("experimentViewPanel");
		}
		return experimentViewPanel;
	}

	/**
	 * This method initializes acqDataViewPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getAcqDataViewPanel() {
		if (acqDataViewPanel == null) {
			acqDataViewPanel = new JPanel();
			acqDataViewPanel.setLayout(new BorderLayout());
			acqDataViewPanel.setName("acqDataViewPanel");
			//acqDataViewPanel.add(getAcqChartPanel(), BorderLayout.CENTER);
		}
		return acqDataViewPanel;
	}

	/**
	 * This method initializes acqDataMenu	
	 * 	
	 * @return javax.swing.JMenu	
	 */
	private JMenu getAcqDataMenu() {
		if (acqDataMenu == null) {
			acqDataMenu = new JMenu();
			acqDataMenu.setText("Acquired Data");
			acqDataMenu.setFont(new Font("Dialog", Font.PLAIN, 12));
			acqDataMenu.setMnemonic(KeyEvent.VK_D);
		}
		return acqDataMenu;
	}

	/**
	 * This method initializes xperMenu	
	 * 	
	 * @return javax.swing.JMenu	
	 */
	private JMenu getXperMenu() {
		if (xperMenu == null) {
			xperMenu = new JMenu();
			xperMenu.setText("Xper");
			xperMenu.setMnemonic(KeyEvent.VK_X);
			xperMenu.setFont(new Font("Dialog", Font.PLAIN, 12));
			xperMenu.add(getExitMenuItem());
		}
		return xperMenu;
	}
	
	static String RELOAD_SYSTEM_VARIABLE_MENU = "Reload All System Variables";  //  @jve:decl-index=0:

	private JScrollPane acqSessionScrollPane = null;

	private JTable acqSessionTable = null;

	private JPanel acqSessionCriteriaPanel = null;

	private JLabel startSessionTimeLabel = null;

	private JLabel stopSessionTimeLabel = null;

	private JTextField startSessionTimeTextField = null;

	private JTextField stopSessionTimeTextField = null;

	private JButton refreshAcqSessionButton = null;

	private JPanel acqChartPanel = null;

	/**
	 * This method initializes reloadSystemVarMenuItem	
	 * 	
	 * @return javax.swing.JMenuItem	
	 */
	private JMenuItem getReloadSystemVarMenuItem() {
		JMenuItem reloadSystemVarMenuItem = new JMenuItem();
		reloadSystemVarMenuItem.setText(RELOAD_SYSTEM_VARIABLE_MENU);
		reloadSystemVarMenuItem.setFont(new Font("Dialog", Font.PLAIN, 12));
		reloadSystemVarMenuItem.setIcon(new ImageIcon(this.getClass().getResource("images/refresh_variable_set.gif")));
		reloadSystemVarMenuItem.setMnemonic(KeyEvent.VK_R);
		reloadSystemVarMenuItem.addActionListener(new java.awt.event.ActionListener() {
			public void actionPerformed(java.awt.event.ActionEvent e) {
				model.reloadSystemVar();
				updateVariableSet();
			}
		});
		reloadSystemVariablesMenuItemList.add(reloadSystemVarMenuItem);
		return reloadSystemVarMenuItem;
	}

	/**
	 * This method initializes acqSessionScrollPane	
	 * 	
	 * @return javax.swing.JScrollPane	
	 */
	private JScrollPane getAcqSessionScrollPane() {
		if (acqSessionScrollPane == null) {
			acqSessionScrollPane = new JScrollPane();
			acqSessionScrollPane.setViewportView(getAcqSessionTable());
		}
		return acqSessionScrollPane;
	}

	/**
	 * This method initializes acqSessionTable	
	 * 	
	 * @return javax.swing.JTable	
	 */
	private JTable getAcqSessionTable() {
		if (acqSessionTable == null) {
			acqSessionTable = new JTable();
			acqSessionTable.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
			acqSessionTable.setModel(new AcqSessionTableModel(model));
			acqSessionTable.setDefaultRenderer(Long.class, new AcqSessionTableCellRenderer());
		}
		return acqSessionTable;
	}

	/**
	 * This method initializes acqSessionCriteriaPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getAcqSessionCriteriaPanel() {
		if (acqSessionCriteriaPanel == null) {
			GridBagConstraints gridBagConstraints5 = new GridBagConstraints();
			gridBagConstraints5.gridx = 1;
			gridBagConstraints5.ipady = 0;
			gridBagConstraints5.fill = GridBagConstraints.NONE;
			gridBagConstraints5.insets = new Insets(5, 0, 0, 0);
			gridBagConstraints5.anchor = GridBagConstraints.WEST;
			gridBagConstraints5.gridy = 2;
			GridBagConstraints gridBagConstraints2 = new GridBagConstraints();
			gridBagConstraints2.gridx = 0;
			gridBagConstraints2.insets = new Insets(5, 0, 0, 0);
			gridBagConstraints2.gridy = 1;
			GridBagConstraints gridBagConstraints4 = new GridBagConstraints();
			gridBagConstraints4.fill = GridBagConstraints.VERTICAL;
			gridBagConstraints4.gridx = 1;
			gridBagConstraints4.gridy = 1;
			gridBagConstraints4.insets = new Insets(5, 0, 0, 0);
			gridBagConstraints4.anchor = GridBagConstraints.WEST;
			gridBagConstraints4.weightx = 1.0;
			GridBagConstraints gridBagConstraints3 = new GridBagConstraints();
			gridBagConstraints3.fill = GridBagConstraints.VERTICAL;
			gridBagConstraints3.anchor = GridBagConstraints.WEST;
			gridBagConstraints3.weightx = 1.0;
			stopSessionTimeLabel = new JLabel();
			stopSessionTimeLabel.setText("Stop Time: ");
			startSessionTimeLabel = new JLabel();
			startSessionTimeLabel.setText("Start Time: ");
			acqSessionCriteriaPanel = new JPanel();
			acqSessionCriteriaPanel.setLayout(new GridBagLayout());
			acqSessionCriteriaPanel.setBorder(BorderFactory.createTitledBorder(null, "Filter Acq Sessions", TitledBorder.DEFAULT_JUSTIFICATION, TitledBorder.DEFAULT_POSITION, new Font("Dialog", Font.PLAIN, 12), new Color(51, 51, 51)));
			acqSessionCriteriaPanel.setPreferredSize(new Dimension(150, 120));
			acqSessionCriteriaPanel.add(startSessionTimeLabel, new GridBagConstraints());
			acqSessionCriteriaPanel.add(getStartSessionTimeTextField(), gridBagConstraints3);
			acqSessionCriteriaPanel.add(stopSessionTimeLabel, gridBagConstraints2);
			acqSessionCriteriaPanel.add(getStopSessionTimeTextField(), gridBagConstraints4);
			acqSessionCriteriaPanel.add(getRefreshAcqSessionButton(), gridBagConstraints5);
		}
		return acqSessionCriteriaPanel;
	}

	/**
	 * This method initializes startSessionTimeTextField	
	 * 	
	 * @return javax.swing.JTextField	
	 */
	private JTextField getStartSessionTimeTextField() {
		if (startSessionTimeTextField == null) {
			startSessionTimeTextField = new JTextField();
			startSessionTimeTextField.setPreferredSize(new Dimension(120, 20));
			startSessionTimeTextField.setMinimumSize(new Dimension(120, 20));
		}
		return startSessionTimeTextField;
	}

	/**
	 * This method initializes stopSessionTimeTextField	
	 * 	
	 * @return javax.swing.JTextField	
	 */
	private JTextField getStopSessionTimeTextField() {
		if (stopSessionTimeTextField == null) {
			stopSessionTimeTextField = new JTextField();
			stopSessionTimeTextField.setPreferredSize(new Dimension(120, 20));
			stopSessionTimeTextField.setMinimumSize(new Dimension(120, 20));
		}
		return stopSessionTimeTextField;
	}

	/**
	 * This method initializes refreshAcqSessionButton	
	 * 	
	 * @return javax.swing.JButton	
	 */
	private JButton getRefreshAcqSessionButton() {
		if (refreshAcqSessionButton == null) {
			refreshAcqSessionButton = new JButton();
			refreshAcqSessionButton.setText("Refresh");
			refreshAcqSessionButton.setPreferredSize(new Dimension(100, 26));
		}
		return refreshAcqSessionButton;
	}

	/**
	 * This method initializes acqChartPanel	
	 * 	
	 * @return javax.swing.JPanel	
	 */
	private JPanel getAcqChartPanel() {
		if (acqChartPanel == null) {
			// TODO:
			/*JFreeChart chart = ChartFactory.createTimeSeriesChart(
					"Legal & General Unit Trust Prices",
					"Date", "Price Per Unit",
					dataset,
					true,
					true,
					false
					);
			acqChartPanel = new ChartPanel(chart);
			acqChartPanel.setMouseZoomable(true, false);*/
		}
		return acqChartPanel;
	}

}  //  @jve:decl-index=0:visual-constraint="10,10"
