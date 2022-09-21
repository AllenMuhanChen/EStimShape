%this function computes the vertices for a thick line
%assumptions: for end of line, compute normal to line segment between end
%and one point away; for all other points in the line, average the normals
%to the line segments that join in the point
%if line is given by (x2-x1,y2-y1), then (one) normal vector is given by
%(-(y2-y1),x2-x1)

%linecoord: points describing the line
%lw: linewidth

function vertcoord=makeLine(linecoord,lw)

flaginvert=0;
if size(linecoord,1)<size(linecoord,2)
    flaginvert=1;
    linecoord=linecoord';
end

nrpoints=length(linecoord);



%first compute normal in every point
normvec=zeros(nrpoints,2);
for i=1:nrpoints-1
    %get normal to the line between the point and the next point
    xnorm=-(linecoord(i+1,2)-linecoord(i,2));
    ynorm=linecoord(i+1,1)-linecoord(i,1);
  
    %normalize
    normlength=sqrt(xnorm^2+ynorm^2);
    normvec(i,1)=xnorm/normlength;
    normvec(i,2)=ynorm/normlength;
end
normvec(nrpoints,:)=normvec(nrpoints-1,:); %just to make the next stuff easier   

%now compute vertices for the thick lines

%ends of lines are special case
vertcoord=zeros(2*nrpoints,2);
for i=[1 nrpoints]
    %vertices are lw/2 away from the endpoints along the direction of the
    %normal
    vertcoord(2*i-1,1)=linecoord(i,1)+lw/2*normvec(i,1);
    vertcoord(2*i-1,2)=linecoord(i,2)+lw/2*normvec(i,2);
    
    vertcoord(2*i,1)=linecoord(i,1)-lw/2*normvec(i,1);
    vertcoord(2*i,2)=linecoord(i,2)-lw/2*normvec(i,2);
end

%for all other lines, need to deal with intersection between lines
for i=2:nrpoints-1
    %average normals to get the normal to the intersection
    %normvec(i-1) is the normal to the line segment that ends in point i,
    %normvec(i) the normal to the line segment that starts in i
    normpoint=1/2*(normvec(i-1,:)+normvec(i,:));
    normpoint=normpoint/sqrt(sum(normpoint.^2));

    
    %get angle between the normal to the intersection and that of one of
    %the lines
    d=sum(normpoint.*normvec(i-1,:));
    
    %now compute vertices
    vertcoord(2*i-1,1)=linecoord(i,1)+lw/(2*d)*normpoint(1);
    vertcoord(2*i-1,2)=linecoord(i,2)+lw/(2*d)*normpoint(2);
    
    vertcoord(2*i,1)=linecoord(i,1)-lw/(2*d)*normpoint(1);
    vertcoord(2*i,2)=linecoord(i,2)-lw/(2*d)*normpoint(2);
end

if flaginvert
    vertcoord=vertcoord';
end

