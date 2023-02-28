package org.xper.allen.ga;

import com.thoughtworks.xstream.XStream;

import java.util.Collection;
import java.util.LinkedList;
import java.util.Objects;
import java.util.function.Consumer;

public class GABranch {

    private Collection<GABranch> children;
    private Long stimId;


    /**
     * For xstream, don't use this.
     */
    public GABranch() {
    }


    public GABranch(Long stimId, Collection<GABranch> children){
        this.stimId = stimId;
        this.children = children;
    }


    public GABranch(Long stimId){
        this.stimId = stimId;
        this.children = new LinkedList<>();
    }

    static XStream s;

    static{
        s = new XStream();
        s.alias("GABranch", GABranch.class);
    }

    public String toXml(){
        return GABranch.toXml(this);
    }

    public static String toXml(GABranch gaBranch){
        return s.toXML(gaBranch);
    }

    public static GABranch fromXml(String xml){
        return (GABranch) s.fromXML(xml);
    }

    public void addChild(GABranch child){
        children.add(child);
    }

    public void addChildTo(long parentId, GABranch childBranch) {
        if (this.stimId == parentId){
            this.addChild(childBranch);
        } else {
            for (GABranch child : children){
                child.addChildTo(parentId, childBranch);
            }
        }
    }

    public void addChildTo(long parentId, long childId) {
        if (this.stimId == parentId){
            this.addChild(new GABranch(childId));
        } else {
            for (GABranch child : children){
                child.addChildTo(parentId, childId);
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

    public Long getStimId() {
        return stimId;
    }

    public void setStimId(Long stimId) {
        this.stimId = stimId;
    }

    @Override
    public String toString() {
       String s = stimId + "\n";
         for (GABranch child : children){

              s += "-"+child.toString();
         }
           return s;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        GABranch gaBranch = (GABranch) o;
        return getChildren().equals(gaBranch.getChildren()) && getStimId().equals(gaBranch.getStimId());
    }

    @Override
    public int hashCode() {
        return Objects.hash(getChildren(), getStimId());
    }
}
