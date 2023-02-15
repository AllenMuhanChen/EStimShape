package org.xper.allen.ga;

import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;

import java.util.function.Consumer;

public class GABranchTest {

    private GABranch founder;

    @Before
    public void setUp() throws Exception {
        founder = new GABranch(1L);
    }

    @Test
    public void addsChildToCurrentBranch() throws Exception {
        GABranch child = new GABranch(2L);
        founder.addChild(child);

        System.out.println(founder);
        Assert.assertTrue(founder.getChildren().contains(child));
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
        Assert.assertTrue(child1.getChildren().contains(testBranch));
        Assert.assertTrue(child2.getChildren().isEmpty());
    }

    @Test
    public void canReadAllIds(){
        GABranch child1 = new GABranch(2L);
        GABranch child2 = new GABranch(3L);
        founder.addChild(child1);
        founder.addChild(child2);

        GABranch testBranch = new GABranch(4L);
        founder.addChildTo(2L, testBranch);

        founder.forEach(new Consumer<GABranch>() {
            @Override
            public void accept(GABranch branch) {
                System.out.println(branch.getBranchId());
            }
        });
    }


}
