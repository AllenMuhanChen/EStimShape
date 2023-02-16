package org.xper.allen.ga;

import org.junit.Before;
import org.junit.Test;

import java.util.LinkedList;
import java.util.List;
import java.util.function.Consumer;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

public class GABranchTest {

    private GABranch founder;

    @Before
    public void setUp() throws Exception {
        founder = new GABranch(1L);
    }

    @Test
    public void addsChildToCurrentBranch(){
        GABranch child = new GABranch(2L);
        founder.addChild(child);

        System.out.println(founder);
        assertTrue(founder.getChildren().contains(child));
    }

    @Test
    public void addsChildToSpecifiedBranch(){
        GABranch child1 = new GABranch(2L);
        GABranch child2 = new GABranch(3L);
        founder.addChild(child1);
        founder.addChild(child2);

        GABranch testBranch = new GABranch(4L);
        founder.addChildTo(2L, testBranch);

        System.out.println(founder);
        assertTrue(child1.getChildren().contains(testBranch));
        assertTrue(child2.getChildren().isEmpty());
    }

    @Test
    public void can_parse_tree(){
        GABranch child1 = new GABranch(2L);
        GABranch child2 = new GABranch(3L);
        founder.addChild(child1);
        founder.addChild(child2);

        GABranch testBranch = new GABranch(4L);
        founder.addChildTo(2L, testBranch);
        List<Long> childrenIds = new LinkedList<>();
        founder.forEach(new Consumer<GABranch>() {
            @Override
            public void accept(GABranch branch) {
                System.out.println(branch.getBranchId());
                childrenIds.add(branch.getBranchId());
            }
        });

        assertTrue(childrenIds.contains(1L));
        assertTrue(childrenIds.contains(2L));
        assertTrue(childrenIds.contains(3L));
        assertTrue(childrenIds.contains(4L));
    }

    @Test
    public void to_xml_and_back(){
        GABranch child1 = new GABranch(2L);
        GABranch child2 = new GABranch(3L);
        founder.addChild(child1);
        founder.addChild(child2);
        GABranch child3 = new GABranch(4L);
        founder.addChildTo(2L, child3);

        String xml = founder.toXml();
        System.out.println(xml);
        GABranch fromXML = GABranch.fromXml(xml);
        System.out.println(fromXML);

        assertEquals(founder, fromXML);
    }


}
