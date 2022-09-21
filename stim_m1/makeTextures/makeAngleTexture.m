function makeAngleTexture



global screenPTROff screenNum GL



Pstruct = getParamStruct;

%this is the outer size of the stimulus
rfrad=1;


%initialize
stimcoord=[];





stimangle1=(180+Pstruct.stimacute/2)*pi/180;
stimangle2=(180-Pstruct.stimacute/2)*pi/180;
%stimangle1=(stimori+180+stimacute/2)*pi/180;
%stimangle2=(stimori+180-stimacute/2)*pi/180;

%center of curved line
%[xcirc,ycirc]=pol2cart(stimori*pi/180,stimcurve);
xcirc=Pstruct.stimcurve;
ycirc=0;


%arc
curvecoord=makeArc(stimangle1,stimangle2,Pstruct.stimcurve,0);
na=size(curvecoord,2);
slope1=-curvecoord(1,1)/curvecoord(2,1);
slope2=-curvecoord(1,na)/curvecoord(2,na);


%offset arc so that it touches the origin
stimcoord(1,:)=curvecoord(1,:)+xcirc;
stimcoord(2,:)=curvecoord(2,:)+ycirc;

%fix any parts sticking out past +- 1
idx=find(stimcoord(1,:).^2+stimcoord(2,:).^2<1);

if length(idx)<na
    stimcoord=stimcoord(:,idx);
    na=size(stimcoord,2);

    %need to correct the slope to the new ends; this is easier done using the circle centered around 0    
    curvetemp=curvecoord(:,idx);
    slope1=-curvetemp(1,1)/curvetemp(2,1);
    slope2=-curvetemp(1,na)/curvetemp(2,na);
end

%add straight lines out to the rf boundary
%get intersect with circle of rf size
%in this computation, make sure that the intercept of the lines is correct
%(needs to go through the endpoint of the curve)
[xinter1,yinter1]=linecirc(slope1,-slope1*stimcoord(1,1)+stimcoord(2,1),0,0,rfrad);
[xinter2,yinter2]=linecirc(slope2,-slope2*stimcoord(1,na)+stimcoord(2,na),0,0,rfrad);

%only keep the ones that are close to the control points
[m,mx]=min((xinter1-stimcoord(1,1)).^2+(yinter1-stimcoord(2,1)).^2);
xinter1=xinter1(mx);
yinter1=yinter1(mx);

[m,mx]=min((xinter2-stimcoord(1,na)).^2+(yinter2-stimcoord(2,na)).^2);
xinter2=xinter2(mx);
yinter2=yinter2(mx);

%add these to the stimulus points
stimcoord=[[xinter1;yinter1] stimcoord [xinter2;yinter2]];

%rotate
rotmat=[cos(Pstruct.stimori*pi/180) -sin(Pstruct.stimori*pi/180); sin(Pstruct.stimori*pi/180) cos(Pstruct.stimori*pi/180)];
linecoord=rotmat*stimcoord;


%also make the connecting arc
ang1=atan2(yinter1,xinter1);
ang2=atan2(yinter2,xinter2);
closecurve=makeArc(ang1,ang2,rfrad,0);
arccoord=rotmat*closecurve;

%figure out whether this is in the correct direction or not
diffarc(1)=(linecoord(1,end)-arccoord(1,1)).^2 + (linecoord(2,end)-arccoord(2,1)).^2;
diffarc(2)=(linecoord(1,end)-arccoord(1,end)).^2 + (linecoord(2,end)-arccoord(2,end)).^2;
if diffarc(2)<diffarc(1)
    arccoord=fliplr(arccoord);
end

%also make circle for the concave stimuli
if Pstruct.stimtype==2
    circ=rsmak('circle',rfrad);
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



if Pstruct.stimtype==1  %convex 
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




