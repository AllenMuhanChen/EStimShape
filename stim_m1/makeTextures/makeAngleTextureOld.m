function makeAngleTexture



global screenPTROff screenNum GL



Pstruct = getParamStruct;



%internal parameters
splinesteps=100;
radius=1/2;

% initial stimulus setup: generate coordinates for all shape outlines
%get angles 
stimangle1=(Pstruct.stimori+Pstruct.stimacute/2)*pi/180;
stimangle2=(Pstruct.stimori-Pstruct.stimacute/2)*pi/180;

%make line or spline, depending on input
linecoord=[];
xinter1=[];
yinter1=[];
xinter2=[];
yinter2=[];
if Pstruct.stimsmooth==0
    %points for line
    linecoord(1,1)=2*radius*cos(stimangle1);
    linecoord(2,1)=2*radius*sin(stimangle1);
    linecoord(1,2)=0;
    linecoord(2,2)=0;
    linecoord(1,3)=2*radius*cos(stimangle2);
    linecoord(2,3)=2*radius*sin(stimangle2);
    
    xinter1=linecoord(1,1);
    yinter1=linecoord(2,1);
    xinter2=linecoord(1,3);
    yinter2=linecoord(2,3);
else
    %make cubic b-spline (ala pasupathy and connor)

    %control points
    yctrl(1)=2*sqrt(2)*radius*sin(stimangle1);
    xctrl(1)=2*sqrt(2)*radius*cos(stimangle1);
    yctrl(2)=sqrt(2)*radius*sin(stimangle1);
    xctrl(2)=sqrt(2)*radius*cos(stimangle1);
    yctrl(3)=0;
    xctrl(3)=0;
    yctrl(4)=sqrt(2)*radius*sin(stimangle2);
    xctrl(4)=sqrt(2)*radius*cos(stimangle2);
    yctrl(5)=2*sqrt(2)*radius*sin(stimangle2);
    xctrl(5)=2*sqrt(2)*radius*cos(stimangle2);

    %spline
    knots=[1:9];
    sp=spmak(knots,[xctrl;yctrl]);
    sp=fnbrk(sp,[3 7]);

    %determine minimum to shift apex to 0,0
    xcomp=fncmb(sp,[1 0]);
    ycomp=fncmb(sp,[0 1]);
    xcomp2=fncmb(xcomp,'*',xcomp);
    ycomp2=fncmb(ycomp,'*',ycomp);
    rad=fncmb(xcomp2,'+',ycomp2);
    [mv,minloc]=fnmin(rad);
    mcoord=fnval(sp,minloc);

    %subtract minimum
    sp=fncmb(sp,mcoord*-1);
    
    %also use rad to determine the useful parts of the spline (the ones
    %where the line doesn't turn back on itself)
    [mv,maxloc1]=fnmin(fncmb(rad,-1),[3 4]);
    [mv,maxloc2]=fnmin(fncmb(rad,-1),[6 7]);
    
    %get x and y values for spline
    x=linspace(maxloc1,maxloc2,splinesteps); %index into spline (this is in knot space)
    tempcoord=fnval(sp,x);
    
    %we need to expand this out to radius 1
    %for this, construct lines through the control points(taking shift into account), 
    %and determine intersection with circle of radius 1
    %need to compute the slope and intersect for the two lines 
    m1=(yctrl(1)-yctrl(2))/(xctrl(1)-xctrl(2));
    m2=(yctrl(5)-yctrl(4))/(xctrl(5)-xctrl(4));
    i1=yctrl(1)-mcoord(2) - m1*(xctrl(1)-mcoord(1));
    i2=yctrl(5)-mcoord(2) - m2*(xctrl(5)-mcoord(1));
    
    %now compute intersects
    [xinter1,yinter1]=linecirc(m1,i1,0,0,1);
    [xinter2,yinter2]=linecirc(m2,i2,0,0,1);
    
    %only keep the ones that are close to the control points
    [m,mx]=min((xinter1-xctrl(1)-mcoord(1)).^2+(yinter1-yctrl(1)-mcoord(2)).^2);
    xinter1=xinter1(mx);
    yinter1=yinter1(mx);

    [m,mx]=min((xinter2-xctrl(5)-mcoord(1)).^2+(yinter2-yctrl(5)-mcoord(2)).^2);
    xinter2=xinter2(mx);
    yinter2=yinter2(mx);
    
    %make sure that the spline does not go past 1
    idx=find(sqrt(tempcoord(1,:).^2+tempcoord(2,:).^2)<1);
    
    %build linecoord
    linecoord=[xinter1;yinter1];
    linecoord=[linecoord tempcoord(:,idx)];
    linecoord(1,length(idx)+2)=xinter2;
    linecoord(2,length(idx)+2)=yinter2;
    
end


%if the stimulus is convex or concave, also make the arc connecting the
%lines
arccoord=[];
if Pstruct.stimtype==1 || Pstruct.stimtype==2
    %get start and stop angle for arc
    ang1=atan2(yinter1,xinter1);
    ang2=atan2(yinter2,xinter2);
    
    %get arc
    arccoord=makeArc(ang1,ang2,0);

    %figure out whether this is in the correct direction or not
    diffarc(1)=(linecoord(1,end)-arccoord(1,1)).^2 + (linecoord(2,end)-arccoord(2,1)).^2;
    diffarc(2)=(linecoord(1,end)-arccoord(1,end)).^2 + (linecoord(2,end)-arccoord(2,end)).^2;
    if diffarc(2)<diffarc(1)
        arccoord=fliplr(arccoord);
    end
end

%also make circle for the concave stimuli
if Pstruct.stimtype==2
    circ=rsmak('circle',2*radius);
    circcoord=fnval(circ,linspace(0,4,100));
end

% now build the actual stimulus
%we're using an offscreen window here instead of drawtexture onto the
%backplane because of the opengl commands
%coordinate system for the offscreen window: -1 to 1 for both x and y
%we'll copy the stimulus over later; at that point we'll set size and
%position

%contrast value is used to generate blanks
if Pstruct.contrast==0
    r=Pstruct.background/255;
    g=Pstruct.background/255;
    b=Pstruct.background/255;
else
    r=Pstruct.redgain;
    g=Pstruct.greengain;
    b=Pstruct.bluegain;
end

%start openGL drawing in offscreen window
Screen('BeginOpenGL', screenPTROff);

glEnable(GL.DEPTH_TEST);
glClearColor(Pstruct.background/255,Pstruct.background/255,Pstruct.background/255,1);
glClear;
%glLineWidth(stimlinewidth);

glEnable(GL.LINE_SMOOTH);
glHint(GL.LINE_SMOOTH_HINT, GL.NICEST);
glEnable(GL.BLEND);
glBlendFunc(GL.SRC_ALPHA,GL.ONE_MINUS_SRC_ALPHA);



if Pstruct.stimtype==0 %line
    glColor3f(r,g,b);
    vertcoord=makeLine(linecoord,Pstruct.linewidth/100);
    glBegin(GL.TRIANGLE_STRIP);
    for i=1:size(vertcoord,2)
        glVertex2f(vertcoord(1,i),vertcoord(2,i));
    end
    glEnd;
    
elseif Pstruct.stimtype==1  %convex 
    glColor3f(r,g,b);
    glBegin(GL.POLYGON);
    for i=1:size(linecoord,2)
        glVertex2f(linecoord(1,i),linecoord(2,i));
    end
    for i=1:size(arccoord,2)
        glVertex2f(arccoord(1,i),arccoord(2,i));
    end
    glEnd; 
else %concave
    %draw shape
    glColor3f(Pstruct.background/255, Pstruct.background/255, Pstruct.background/255);
    glBegin(GL.POLYGON);
    for i=1:size(linecoord,2)
        glVertex2f(linecoord(1,i),linecoord(2,i));
    end
    for i=1:size(arccoord,2)
        glVertex2f(arccoord(1,i),arccoord(2,i));
    end
    glEnd; 
    
    %draw circle
    glColor3f(r,g,b);
    glBegin(GL.POLYGON);
    for i=1:size(circcoord,2)
        glVertex2f(circcoord(1,i),circcoord(2,i));
    end
    glEnd;
end
    
%end openGL
Screen('EndOpenGL', screenPTROff);

%now add the mask - this is a regular matlab matrix
screenRes = Screen('Resolution',screenNum);
offwidth=screenRes.width;
offheight=screenRes.height;
    
mask=ones(offheight,offwidth,4);
for i=1:3
    mask(:,:,i)=round(mask(:,:,i)*Pstruct.background);
end

x=linspace(-1,1,offwidth);
y=linspace(-1,1,offheight);
xmat=repmat(x,offheight,1);
ymat=repmat(y',1,offwidth);
[phi,rad]=cart2pol(xmat,ymat);
    
masktmp=zeros(offheight,offwidth);
masktmp=-1+2*rad;
masktmp(rad<.5)=0;
masktmp(rad>1)=1;
masktmp=masktmp.*255;
    
mask(:,:,4)=masktmp;
    
Screen('PutImage',screenPTROff,mask);




