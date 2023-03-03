package org.xper.allen.ga;

import com.thoughtworks.xstream.XStream;

import java.util.Collection;
import java.util.LinkedList;
import java.util.Objects;
import java.util.function.Consumer;

public class Branch<T> {

    private Collection<Branch<T>> children;
    private T identifier;

    public Branch(T identifier){
        this.identifier = identifier;
        this.children = new LinkedList<>();
    }

    public void addChild(Branch<T> child){
        children.add(child);
    }

    /**
     * Adds a child to the branch with the specified identifier. The specified identifier
     * can be the identifier for any of the branches in the tree.
     *
     * @param childBranch the branch to add as a child
     */
    public void addChildTo(T parentId, Branch<T> childBranch) {
        if (this.identifier == parentId){
            this.addChild(childBranch);
        } else {
            for (Branch<T> child : children){
                child.addChildTo(parentId, childBranch);
            }
        }
    }

    /**
     * Adds a child to the branch with the specified identifier. The specified identifier
     * can be the identifier for any of the branches in the tree.
     *
     * @param childId given identifier for the child branch, will create a new branch with this identifier to add
     */
    public void addChildTo(T parentId, T childId) {
        if (this.identifier == parentId){
            this.addChild(new Branch<T>(childId));
        } else {
            for (Branch<T> child : children){
                child.addChildTo(parentId, childId);
            }
        }
    }

    public void forEach(Consumer<? super Branch<T>> action) {
        action.accept(this);
        for (Branch<T> child : children){
            child.forEach(action);
        }
    }

    static XStream s;

    static{
        s = new XStream();
        s.alias("GABranch", Branch.class);
        s.aliasField("identifier", Branch.class, "identifier");
    }

    /**
     * For XStream, shouldn't be called directly.
     */
    private Branch() {
    }

    public String toXml(){
        return Branch.toXml(this);
    }

    public static String toXml(Branch branch){
        return s.toXML(branch);
    }

    public static Branch fromXml(String xml){
        return (Branch) s.fromXML(xml);
    }

    public Collection<Branch<T>> getChildren() {
        return children;
    }

    public void setChildren(Collection<Branch<T>> children) {
        this.children = children;
    }

    public T getIdentifier() {
        return identifier;
    }

    public void setIdentifier(T identifier) {
        this.identifier = identifier;
    }

    @Override
    public String toString() {
       String s = identifier + "\n";
         for (Branch<T> child : children){

              s += "-"+child.toString();
         }
           return s;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Branch<T> branch = (Branch<T>) o;
        return getChildren().equals(branch.getChildren()) && getIdentifier().equals(branch.getIdentifier());
    }

    @Override
    public int hashCode() {
        return Objects.hash(getChildren(), getIdentifier());
    }
}