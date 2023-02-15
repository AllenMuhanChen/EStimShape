package org.xper.allen.ga;

import java.util.Collection;
import java.util.LinkedList;
import java.util.function.Consumer;

public class GABranch {

    private Collection<GABranch> children;
    private Long branchId;

    public GABranch(Long branchId, Collection<GABranch> children){
        this.branchId = branchId;
        this.children = children;
    }

    public GABranch(Long branchId){
        this.branchId = branchId;
        this.children = new LinkedList<>();
    }

    public void addChild(GABranch child){
        children.add(child);
    }

    public void addChildTo(long branchId, GABranch branch) {
        if (this.branchId == branchId){
            this.addChild(branch);
        } else {
            for (GABranch child : children){
                child.addChildTo(branchId, branch);
            }
        }
    }

    public void forEach(Consumer<? super GABranch> action) {
        action.accept(this);
        for (GABranch child : children){
            child.forEach(action);
        }
    }

    public Collection<GABranch> getChildren() {
        return children;
    }

    public void setChildren(Collection<GABranch> children) {
        this.children = children;
    }

    public Long getBranchId() {
        return branchId;
    }

    public void setBranchId(Long branchId) {
        this.branchId = branchId;
    }

    @Override
    public String toString() {
       String s = branchId + "\n";
         for (GABranch child : children){

              s += "-"+child.toString();
         }
           return s;
    }
}
