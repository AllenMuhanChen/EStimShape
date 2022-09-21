%new curvature stimuli
%control curvature and subtense


stimacute=30;
stimori=270;
stimcurve=3;

rfrad=4;


%make circle approximating outer boundary
rfcirc=rsmak('circle',rfrad);



stimangle1=(180+stimacute/2)*pi/180;
stimangle2=(180-stimacute/2)*pi/180;
%stimangle1=(stimori+180+stimacute/2)*pi/180;
%stimangle2=(stimori+180-stimacute/2)*pi/180;

%center of curved line
%[xcirc,ycirc]=pol2cart(stimori*pi/180,stimcurve);
xcirc=stimcurve;
ycirc=0;


%arc
arccoord=makeArc(stimangle1,stimangle2,stimcurve,0);
na=size(arccoord,2);
slope1=-arccoord(1,1)/arccoord(2,1);
slope2=-arccoord(1,na)/arccoord(2,na);


%offset arc so that it touches the origin
stimcoord(1,:)=arccoord(1,:)+xcirc;
stimcoord(2,:)=arccoord(2,:)+ycirc;



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


%also generate arc between the intersects to close shape
ang1=atan2(yinter1,xinter1);
ang2=atan2(yinter2,xinter2);
closecurve=makeArc(ang1,ang2,rfrad,0);

%rotate the coordinates
rotmat=[cos(stimori*pi/180) -sin(stimori*pi/180); sin(stimori*pi/180) cos(stimori*pi/180)];
rotcoord=rotmat*stimcoord;
rotclose=rotmat*closecurve;

%display

figure
plot(rotcoord(1,:),rotcoord(2,:),'k-')
hold on
fnplt(rfcirc)
plot(rotclose(1,:),rotclose(2,:),'r-')
axis square